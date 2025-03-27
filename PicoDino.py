from machine import Pin, I2C
from fifo import Fifo
import dino_bitmap
import cacti_bitmap
import framebuf
import ssd1306
import math
import time
import random
import sys

# GPIO pins for game functions
scl_pin = 15	# Screen SCL
sda_pin = 14	# Screen SDA
jump_pin = 12	# Jump button
reset_pin = 7	# Game reset button

# dino bitmap
dino_buffer = framebuf.FrameBuffer(dino_bitmap.img, 8, 8, framebuf.MONO_VLSB)

# cactus bitmap
cactus_buffer = framebuf.FrameBuffer(cacti_bitmap.img, 8, 8, framebuf.MONO_VLSB)

# OLED Setup
i2c = I2C(1, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# Game controls
jump_btn = Pin(jump_pin, Pin.IN, Pin.PULL_UP)
reset_btn = Pin(reset_pin, Pin.IN, Pin.PULL_UP)

# Settings
total_jump_time = 500	# ms
jump_height = 20		# pixels
run_speed = 2			# pixels per frame
ground_height = 50
current_x = 0			# starting position
points = 0
high_score = 0
cactus_chance = 0.1		# cactus spawn chance (out of 1)
brightness = 1			# can be used to change screen brightness.



cactus_cooldown = False
last_cactus = None
color_palette = 0		# 0 = normal, 1 = Inverted screen
#color_change = False	# not used
#color_timer = None		# not used
jump_time = None
cactus_array = []
pause = False


# Dino class
class Dino:
    size_x = 8
    size_y = 8
    
    def __init__(self):
        self.x = 16
        self.y = ground_height - self.size_y
        self.default_y = ground_height - self.size_y
        self.isJumping = False
        self.jump_cooldown = total_jump_time + 50
        
    def jump(self, jump_time):
        if self.isJumping:
            t = jump_time / total_jump_time
            if t <= 1:
                y = self.default_y - jump_height * (4 * t*(1-t))
                self.y = round(y)
                return
            else:
                self.isJumping = False
                self.y = self.default_y
                return
        else:
            self.isJumping = True
            return

# Cactus obstacle class
class Cactus:
    size_x = 8
    size_y = 8
    
    def __init__(self, x, y):
        self.x = x
        self.y = ground_height - self.size_y
    
    def check_hits(self, obj):
        if self.x + self.size_x > obj.x:	# If cactus is not past player 
            return not (obj.x + obj.size_x < self.x or  # A is left of B
                        self.x + self.size_x < obj.x or  # A is right of B
                        obj.y + obj.size_y < self.y or  # A is above B
                        self.y + self.size_y < obj.y)    # A is below B
        else:
            return False

# Draw scene to screen
def Draw_scene(dino):
    oled.fill(0)
    oled.line(0, ground_height + 1, 127, ground_height + 1, 1)
    oled.text(str(points), 10, 10, 1)
    high_score_str = str(high_score)
    oled.text(high_score_str, 128 - (len(high_score_str) * 8), 10, 1)
    oled.blit(dino_buffer, dino.x, dino.y, 0)
    for c in cactus_array:
        oled.blit(cactus_buffer, c.x, c.y, 0)
    oled.invert(color_palette)
    oled.contrast(int(brightness * 255))
    oled.show()
    return

# Spawn cactus to the right side of the screen
def spawn_cactus():
    global current_x, ground_height
    cactus_array.append(Cactus(current_x + 127, ground_height - Cactus.size_y))
    return

# Reset game
def reset_game():
    global dino, cactus_array, current_x, points, cactus_cooldown, last_cactus, color_palette
    oled.fill(0)
    dino = Dino()
    cactus_array = []
    current_x = 0
    points = 0
    cactus_cooldown = False
    last_cactus = None
    color_palette = 0
    return

# Initialize dino object
dino = Dino()

while True:
    # Reset game
    if reset_btn() == 0:
        reset_game()
        pause = False
    
    # If game is paused > skip game loop
    if pause:
        continue

    if jump_btn() == 0 and not dino.isJumping:
        jump_time = time.ticks_ms()
        dino.jump(time.ticks_diff(time.ticks_ms(), jump_time))

    elif dino.isJumping:
        dino.jump(time.ticks_diff(time.ticks_ms(), jump_time))
        
    # Move cactus and check player collision
    for c in cactus_array:
        c.x -= run_speed
        if c.check_hits(dino):
            oled.text("GAVE OVER", 30, 30)
            oled.show()
            pause = True
            break
    if pause:
        continue
    
    # Remove off-screen cactus
    cactus_array = list(filter(lambda c: c.x >= 0, cactus_array))
    
    # Cactus spawn logic
    if random.random() > cactus_chance and not cactus_cooldown:
        spawn_cactus()
        last_cactus = time.ticks_ms()	# make sure next cactus doesn't spawn immediately
        cactus_cooldown = True
    elif cactus_cooldown:
        if time.ticks_diff(time.ticks_ms(), last_cactus) > 300:
            cactus_cooldown = False
    
    current_x += run_speed
    points = round(round(current_x, -1) / 10)
    
    # Update high score
    if points >= high_score:
        high_score = points
    
    # "Day and night cycle", cycles every 100m
    if current_x > 0 and current_x % 1000 == 0:
        color_palette = int(not color_palette)
#         # Cool color fade effect, did not work well with sd1306
#         color_change = True
#         color_timer = time.ticks_ms()
#         
#     if color_change == True:
#         t = time.ticks_diff(time.ticks_ms(), color_timer) / 1000
#         if t <= 1:
#             brightness = 1 - 1 * (4 * t*(1-t))
#             #print(brightness)
#             if int(brightness * 100) == 0:
#                 color_palette = int(not color_palette)
#         else:
#             brightness = 1
#             color_change = False
#             color_timer = None
    
    Draw_scene(dino)
    

