
########## Pika temp 2.8 [pico] ##########


import time, framebuf, ssd1306, onewire, ds18x20, machine
from micropython import const
from machine import Pin, I2C
from oled import Write, GFX, SSD1306_I2C
from oled.fonts import ubuntu_15, ubuntu_20


# Globals / Offsets
x_pos = 24                # pika på pos
y_pos = -6                # allt  
x_text = 1                # endast text
y_text = 1                # endast text
celsius_x = 85 + x_text   # 86
celsius_y = 21 + y_text   # 22
do_once = 0
do_once_2 = 0
pika_overwrite = False


# Sensor 4.7k ohms pullup
ds_pin = machine.Pin(26) 
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
temp_sensor = ds_sensor.scan()

# Optocuopler 3.3v till gpio 27
knapp = Pin(27, Pin.IN, Pin.PULL_DOWN)


# Oled display init
i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=const(400000))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled.contrast(32)
gfx = GFX(128, 64, oled.pixel)
oled.fill(0)
write15 = Write(oled, ubuntu_15)
write20 = Write(oled, ubuntu_20)


# Image pikachu read as bitmap
with open('ggi.pbm', 'rb') as f:
    f.readline() #number
    f.readline() #creator
    f.readline() #dimensions
    data = bytearray(f.read())
    pika = framebuf.FrameBuffer(data, 128, 64, framebuf.MONO_HLSB)
    
        
# Första sensor reading fel, så händer här i boot fasen
for i in range(5):
    ds_sensor.convert_temp()
    for rom in temp_sensor:
        temperature_sensor = round(ds_sensor.read_temp(rom),1)+0.3
    time.sleep(0.2)
    

# Temp i txt till display + running time
def temp_txt_oled(offset = 0):
    write20.text(str(temperature_sensor), 43 + x_text - offset, 23 + y_pos + y_text)  # txt temp
    gfx.fill_rect(38 - offset, 51 + y_pos, progress_bar, 2, 1)                        # progressbar
    gfx.fill_rect(39 + progress_bar - offset, 51 + y_pos, 50 - progress_bar, 2, 0)    # inverterad progressbar för att "ta bort" den andra
    oled.show()
    
    
# Celcius symbol * (how to lul) 
def celius_symbol(x, y, offset_x = 0):
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

    
# Main loop
while True:
    try:
        # tempsensor
        ds_sensor.convert_temp()
        for rom in temp_sensor:
            temperature_sensor = round(ds_sensor.read_temp(rom),1)+0.3
            
            # temperature bar
            bar = (((temperature_sensor) - 21) / (36-21))    # (x - min) / (max - min) = % 
            progress_bar = int(bar * 52)                     # mapa till pixlar på skärm 0 - 52
                  
            # pika on, uppdatera endast det som behövs på skärm
            if knapp.value() == True or pika_overwrite == True:
                time.sleep(0.1) # enkel debounce
                if knapp.value() == True or pika_overwrite == True:
                    if do_once == 0:
                        do_once = 1
                        do_once_2 = 0
                        oled.fill(0)
                        oled.blit(pika, 9, 0)
                        celius_symbol(celsius_x, celsius_y, -x_pos)
                        gfx.rect(38 - x_pos, 50 + y_pos, 52, 4, 1)   # progressbar outline
                    temp_txt_oled(x_pos)

            # pika av
            else:
                if do_once_2 == 0:
                    do_once_2 = 1
                    do_once = 0
                    oled.fill(0)
                    celius_symbol(celsius_x, celsius_y)
                    gfx.rect(38, 50 + y_pos, 52, 4, 1)               # progressbar outline
                temp_txt_oled()
   
        # High temp varning
        if ((round(ds_sensor.read_temp(rom),1)) >= const(35.8)): #35.8
            do_once = 0
            do_once_2 = 0
            oled.fill(0)
            write20.text("Varning!", 29, 18)
            write15.text("Hot", 52, 39)
            while (round(ds_sensor.read_temp(rom),1)) >= const(35.8): #35.8
                oled.invert(0), oled.show()
                time.sleep(0.5)
                oled.invert(1), oled.show()
                time.sleep(0.5)
                ds_sensor.convert_temp() # read sensor i while loop
            oled.invert(0)
                
    except:
        machine.reset()
    


