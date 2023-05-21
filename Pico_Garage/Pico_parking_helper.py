
####### Pico Parking Help 3.7 #######


import time, machine, gc, tm1637, _thread 
from machine import Pin, I2C
from tof import VL53L1X
from micropython import const


# Led + button
button = Pin(2, Pin.IN, Pin.PULL_DOWN)
led_red = Pin(3, Pin.OUT, Pin.PULL_DOWN, value = 0)    # type: ignore
led_green = Pin(4, Pin.OUT, Pin.PULL_DOWN, value = 0)  # type: ignore


# Globals / Constants
min_distance = const(400)                 # min distance for car detetion (mm)
max_distance = const(1400)                # max distance for car detetion (mm)
error_distance = const(8000)              # error sensor reading = about 8000+ 
min_park_time = const(6)                  # ignore if parking took < min_park_time s
max_park_time = const(2*60)               # ignore if parking took > max_park_time s
sensor_samples = const(5)                 # samples per checkup
display_brightness = 2                    # brightness 1-7 
parking_check = False                     # car detected?
parking_error = False                     # error? 
start_time = 0                            # used for debouncing + counting 
highscore = "0"                           # highscore str


####### Functions #######


# Read highscore from flash
def read_highscore_from_flash():
    try:
        with open("log.csv", "r") as f:
            highscore = f.readline(8)
        if len(highscore) != 4:
            raise ValueError("Invalid highscore value")

    except (OSError, ValueError) as e:
        print(f"Error: {e}")
        with open("log.csv", "w") as f:
                f.write("0000")
                highscore = "0000"
    return highscore


# Save new highscore to flash
def save_highscore_to_flash(minutes, seconds):
    data = "{:02d}{:02d}".format(minutes, seconds)
    try:
        with open("log.csv", "w") as f:
            f.write(data)
    except:
        pass
    return data


# Init time-of-Flight sensor (tof)
def init_tof_sensor():
    i2c = I2C(0, scl = Pin(1), sda = Pin(0))
    if 0x29 not in i2c.scan():
        print("Failed to find device")
        machine.reset() 
    tof = VL53L1X(i2c)
    return tof  


# Time.sleep() exactly 1s including code block
def sleep_ms(ms):
    global start_time
    elapsed_time = time.ticks_ms() - start_time
    sleep_time = ms - elapsed_time
    if sleep_time > 0:
        time.sleep_ms(sleep_time)
    start_time = time.ticks_ms()


# Sensor samples average + car present?
def check_for_car(nr = sensor_samples):
    avg_list = []
    for i in range(nr):
        avg_list.append(tof.read()) 
    car_distance = int (sum(avg_list) / len(avg_list))
    if min_distance < car_distance < max_distance:
        return True
    else:
        return False 


# Display highscore interrupt ("pin" used for pico interrupts) 
def display_show_highscore(pin):
    display.brightness(display_brightness)  
    while True:
        display.show(highscore, True)
        time.sleep_ms(50)
        if button.value() == 0:
            time.sleep(5)     
            display.write([0, 0, 0, 0])
            display.brightness(0)
            break


# Display standby animation (2nd thread)
def display_standby():
    while True:
        display.brightness(display_brightness)
        display.scroll("-", 200)
        for i in range(100):
            time.sleep_ms(15)
            if parking_check:
                display_start_counting()
                break

    
# Display counting animation (2nd thread) 
def display_start_counting():
    global start_time, highscore
    minutes = 0 
    seconds = 0 
    display.brightness(display_brightness)
    start_time = time.ticks_ms()

    # counter 00:00 
    while parking_check:
        display.numbers(minutes, seconds)
        seconds += 1
        if seconds == 60:
            seconds = 0
            minutes += 1
        sleep_ms(1000)
    display.numbers(minutes, seconds)

    # false positive?
    if parking_error: 
        display.write([0, 0, 0, 0])
        display.brightness(0)
        led_green.value(0)
        led_red.value(0)
        _thread.exit()

    # highscore? save to flash mem
    current_highscore = (int(highscore[:2]) * 60) + int(highscore[2:])          # (minutes x 60) + (seconds) 
    if (minutes * 60 + seconds) < current_highscore and current_highscore != 0:
        highscore = save_highscore_to_flash(minutes, seconds)
        time.sleep(4)
        for i in range(2):
            display.brightness(7)
            display.scroll('High    score')
            display.show(highscore, True)
            time.sleep(3)
            display.brightness(display_brightness)
    _thread.exit()


# Sensor logic
def sensor_logic():
    global parking_check, parking_error
    parking_check = True 
    button.irq(trigger=Pin.IRQ_RISING, handler = None)  #type: ignore 
    park_time = time.time()   

    while True:
        sensor_read = tof.read() 
        if sensor_read > error_distance:
            continue                          
        elif sensor_read < max_distance:                      
            if not led_red.value():
                led_red.value(1)
        else:
            parking_check = False # stops counting thread
            break

    # outside of expected range?
    park_time = time.time() - park_time 
    if min_park_time > park_time or park_time > max_park_time:
        led_red.value(0)
        button.irq(trigger=Pin.IRQ_RISING, handler = display_show_highscore)
        parking_error = True
        time.sleep(5)
        parking_error = False
        _thread.start_new_thread(display_standby, ())

    else:
        # toggle green led, parking complete!
        led_green.value(1)
        for i in range(5):
            led_green.toggle()
            led_red.toggle()
            time.sleep(0.5)
        led_red.value(0)
        led_green.value(1) 

        # restart interupt handler, sleep 30s, cleanup
        button.irq(trigger=Pin.IRQ_RISING, handler = display_show_highscore)
        time.sleep(30)
        led_green.value(0)
        display.write([0, 0, 0, 0])
        display.brightness(0)
        gc.collect()

        # Succes! loop forever
        while True:
            try:
                pass
            except:
                pass


# Init display, distance sensor
tof = init_tof_sensor() 
highscore = read_highscore_from_flash()
display = tm1637.TM1637(clk = Pin(15), dio = Pin(14))
display.write([0, 0, 0, 0])
display.brightness(0)


# Main loop
def main_core():
    _thread.start_new_thread(display_standby, ())
    while True:
        try:
            for i in range(const(5000)):
                average = check_for_car()
                if average:                                               
                    sensor_logic()
            gc.collect()
        except KeyboardInterrupt:
            exit()
        except:
            machine.reset() # error? reboot
            pass


# Interrupt init, start main loop
button.irq(trigger = Pin.IRQ_FALLING, handler = display_show_highscore)
main_core()

