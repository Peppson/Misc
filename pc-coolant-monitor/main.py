
########## Pika temp 3.2 [pico] ##########


import time, framebuf, ssd1306, onewire, ds18x20, machine
from micropython import const
from machine import Pin, I2C
from lib.oled import Write, GFX, SSD1306_I2C
from lib.oled.fonts import ubuntu_15, ubuntu_20


# Globals / Offsets
x_pos = const(24)                   # pos pika on 
y_pos = const(-6)                   # pos everything  
x_text = const(1)                   # pos text only
y_text = const(1)                   # pos text only
celsius_x = const(85 + x_text)      # pos *C
celsius_y = const(21 + y_text)      # pos *C
high_temp = const(35.8)             # max temp before temp varning
temperature_sensor = 0.0            # temp sensor
do_once = False                     # do once
do_once_2 = False                   # do once
pika_overwrite = False              # dev


# Temp sensor, button
def init_temp_sensor_and_button():
    ds_pin = machine.Pin(26) 
    ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
    temp_sensor = ds_sensor.scan()
    button = Pin(27, Pin.IN, Pin.PULL_DOWN)
    
    return temp_sensor, ds_sensor, button


# Remove temp outliers at boot
def remove_outliers():
    for i in range(12):
        ds_sensor.convert_temp()
        for rom in temp_sensor:
            temperature_sensor = ds_sensor.read_temp(rom)
        time.sleep(0.1)
        

# Oled display init
def display_init():
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=const(400000))
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    gfx = GFX(128, 64, oled.pixel)
    write15 = Write(oled, ubuntu_15)
    write20 = Write(oled, ubuntu_20)
    oled.contrast(32)
    oled.fill(0)

    return oled, gfx, write15, write20


# Image pikachu read from flash
def read_image_from_flash():
    with open('pika.pbm', 'rb') as f:
        for i in range(3):
            f.readline() # nothing
        data = bytearray(f.read())

    return framebuf.FrameBuffer(data, 128, 64, framebuf.MONO_HLSB)

    
# Temperature to display
def temp_txt_oled(offset = 0):
    write20.text(str(temperature_sensor), 43 + x_text - offset, 23 + y_pos + y_text)            # txt temp
    gfx.fill_rect(38 - offset, 51 + y_pos, temp_progress_bar, 2, 1)                             # progressbar
    gfx.fill_rect(39 + temp_progress_bar - offset, 51 + y_pos, 50 - temp_progress_bar, 2, 0)    # inverterd progressbar to "remove" the other one
    oled.show()
    
    
# Celcius symbol (how to lul) 
def celsius_symbol(x, y, offset_x = 0):
    oled.pixel(x + offset_x, y, 1)
    oled.pixel(x + 1 + offset_x, y, 1)
    oled.pixel(x + 2 + offset_x, y, 1)
    oled.pixel(x + 3 + offset_x, y + 1, 1)
    oled.pixel(x + 3 + offset_x, y + 2, 1)
    oled.pixel(x + 3 + offset_x, y + 3, 1)
    oled.pixel(x + offset_x, y + 4, 1)
    oled.pixel(x + 1 + offset_x, y + 4, 1)
    oled.pixel(x + 2 + offset_x, y + 4, 1)
    oled.pixel(x - 1 + offset_x, y + 1, 1)
    oled.pixel(x - 1 + offset_x, y + 2, 1)
    oled.pixel(x - 1 + offset_x, y + 3, 1)


# high temperature varning
def high_temp_varning():
    oled.fill(0)
    write20.text("Varning!", 29, 18)
    write15.text("Hot", 52, 39)

    while (round(ds_sensor.read_temp(rom),1)) >= high_temp: 
        oled.invert(0)
        oled.show()
        time.sleep(0.5)
        oled.invert(1)
        oled.show()
        time.sleep(0.5)
        ds_sensor.convert_temp()
    oled.invert(0)
    

# Init
pika = read_image_from_flash()
oled, gfx, write15, write20 = display_init()
temp_sensor, ds_sensor, button = init_temp_sensor_and_button()
remove_outliers()


# Main loop
while True:
    try:    
        ds_sensor.convert_temp()
        for rom in temp_sensor:
            temperature_sensor = round(ds_sensor.read_temp(rom),1) + 0.3 
        
        # temperature bar
        bar = ((temperature_sensor) - 21) / (36-21)    # (x - min) / (max - min) = % 
        temp_progress_bar = int(bar * 52)              # map to pixels  0 - 52
                  
        # pika on
        if button.value() or pika_overwrite:
            time.sleep(0.1) # simple debounce

            if button.value() or pika_overwrite:
                if not do_once:
                    do_once = True
                    do_once_2 = False
                    oled.fill(0)
                    oled.blit(pika, 9, 0)
                    celsius_symbol(celsius_x, celsius_y, -x_pos)
                    gfx.rect(38 - x_pos, 50 + y_pos, 52, 4, 1) # progressbar outline
                temp_txt_oled(x_pos)

        # pika off
        else:
            if not do_once_2:
                do_once_2 = True
                do_once = False
                oled.fill(0)
                celsius_symbol(celsius_x, celsius_y)
                gfx.rect(38, 50 + y_pos, 52, 4, 1) # progressbar outline
            temp_txt_oled()
            
        # High temp varning
        if (round(ds_sensor.read_temp(rom),1)) >= high_temp: #type: ignore
            high_temp_varning()
            do_once = False 
            do_once_2 = False
              
    except:
        machine.reset()
    



