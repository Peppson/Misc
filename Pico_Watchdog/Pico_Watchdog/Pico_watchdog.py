

####### Pico Watchdog 5.4 #######
# micropython @ Pi Pico W
# Spaghetti enjoy
# Aktivera "home"

import machine, time, framebuf, gc, ssd1306, network, umail
from lib.oled import Write, GFX
from ssd1306 import SSD1306_I2C
from machine import Pin, I2C, WDT
from micropython import const
from lib.oled.fonts import ubuntu_20, ubuntu_15
from Wifi import secrets
gc.collect()

# Globals / constants
dog_image = False                       # start value for which image to show
stop_all_code = False                   # bad var name for keeping track if there was any errors 
pihole_debounce = False                 # debounce pi nr1 
home_debounce = False                   # debounce pi nr2 
email_sent = False                      # only once
display_state = None                    # unknown state at boot          
power_outage = False                    # power outage?
shutdown_once = False                   # shutdown pis once
power_outage_triggered = False          # snus är fint!
adc_threshold = const(3000)             # powerloss at what value?
adc_time_delay = const(10*60)           # shut down after x minutes   ????????
email_txt = ""                          
home_txt = "ok!"
pihole_txt = "ok!"
ups_txt = "ok!"
ssid = secrets[const('wifi_ssid')]
password = secrets[const('wifi_password')]
wlan = network.WLAN(network.STA_IF)


# Interrupt pins IN
pin_monitor = Pin(22, Pin.IN, Pin.PULL_DOWN)   # Oled display
pin_pihole = Pin(28, Pin.IN, Pin.PULL_DOWN)    # Pihole 
pin_home = Pin(10, Pin.IN, Pin.PULL_DOWN)      # Home Assistant
pin_ups = machine.ADC(27)                      # Ups 

# On/off pins OUT                              
gpio_2 = Pin(2, Pin.OUT, value = 0)            # pwr mosfet display                 # type: ignore
gpio_13 = Pin(13, Pin.OUT, value = 0)          # pwr opto pi 1 out                  # type: ignore
gpio_15 = Pin(15, Pin.OUT, value = 0)          # pwr opto pi 2 out                  # type: ignore
gpio_23 = Pin(23, Pin.OUT, value = 0)          # pwr wifichip                       # type: ignore

# Power OUT 3.3v for optocouplers
gpio_1 = Pin(1, Pin.OUT, value = 1)            # pwr pihole opto                    # type: ignore
gpio_9 = Pin(9, Pin.OUT, value = 1)            # pwr home opto                      # type: ignore


####### Functions #######


# Load images from flash
def load_dogos(filename):
    try:
        with open(filename, 'rb') as f:
            for _ in range(3):
                f.readline()  
            data = bytearray(f.read())
            return framebuf.FrameBuffer(data, 128, 64, framebuf.MONO_HLSB)
    except:
        machine.reset()
dog_1 = load_dogos('dog_1.pbm')
dog_2 = load_dogos('dog_2.pbm')


# Adc average 
def get_adc_average(times):
    avg_list = []
    for i in range(times):
        avg_list.append(pin_ups.read_u16())
    return sum(avg_list) / len(avg_list)


# Send email
def send_email(times):
    try:
        # setup
        wdt.feed()
        gmail_password = secrets[const('gmail_password')]             # gmail password
        sender_email = 'pico.watchdog@gmail.com'                      # sender email
        sender_name = 'Pico.watchdog'                                 # sender name 
        recipient_email = 'jw_jw2@hotmail.com'                        # recipient email
        smtp = umail.SMTP('smtp.gmail.com', 465, ssl=True)            # connect to the Gmail's SSL port
        smtp.login(sender_email, gmail_password)                      # login
        smtp.to(recipient_email)                                      # send to who?
        # content
        wdt.feed()
        smtp.write("From:" + sender_name + "<"+ sender_email+">\n")
        smtp.write("Subject:" + "Varning" + "\n")
        smtp.write(email_txt + "\n")
        smtp.send()
        smtp.quit()
        print("Email sent!")  

    except: # email error? try 5 times then error loop
        if times <= 4:
            for i in range(20):
                wdt.feed()
                time.sleep(3)
            gc.collect()
            send_email(times + 1)
        else:
            pass
        
      
# Connect to wifi 
def connect_wifi(times):
    wdt.feed()
    gpio_23.value(1)
    time.sleep(0.3)
    wlan.active(True)
    wlan.connect(ssid, password)

    # try to connect 
    max_wait = 20
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break 
        max_wait -= 1
        wdt.feed()
        time.sleep(1)
    # connection error? try 5 times > error loop
    if wlan.status() != 3: 
        if times <= 4:
            for i in range(20):
                wdt.feed()
                time.sleep(3)
            gc.collect()
            connect_wifi(times + 1)
        else:
            return False
    else:
        print('Connected:', wlan.ifconfig()[0]) 
        return True

       
# Error! wifi > send mail > error loop   
def error_found():
    global email_sent, stop_all_code
    pin_pihole.irq(trigger = Pin.IRQ_FALLING, handler = None) # type: ignore
    pin_home.irq(trigger = Pin.IRQ_FALLING, handler = None) # type: ignore
    stop_all_code = True
    display()
    gc.collect()

    # send email once
    if not email_sent:  
        if connect_wifi(0):
            send_email(0)
        shutdown_wifi()
        email_sent = True


# Shutdown wifi
def shutdown_wifi():
    wdt.feed()
    wlan.active(False)
    wlan.deinit()
    time.sleep(0.5)
    gpio_23.value(0)
    time.sleep(0.5)
    gc.collect()    


# Shutdown all raspberry pi via gpios
def shutdown_pi():
    global shutdown_once, home_txt, pihole_txt
    if not shutdown_once:
        print("Powering down pis")
        # raspberry pi 1
        gpio_13.value(1)
        time.sleep(0.4) 
        gpio_13.value(0)
        # raspberry pi 2
        time.sleep(0.1)
        gpio_15.value(1)
        time.sleep(0.4)  
        gpio_15.value(0)
        pihole_txt = "OFF"
        home_txt = "OFF"
        shutdown_once = True


# Update display
def refresh_display():
    global dog_image
    oled.fill(0)

    if stop_all_code:
        oled.blit(dog_1 , 23, 36)    # type: ignore
    elif dog_image:
        oled.blit(dog_1, 1, -1)      # type: ignore
        dog_image = False
    else:
        oled.blit(dog_2 , 1, 0)      # type: ignore
        dog_image = True

    # display text every refresh (.blit replaces the whole display...)
    write15.text(const("Home:"), 3, 5) 
    write15.text(const("Pihole:"), 3, 22)
    write15.text(const("Ups:"), 3, 39)
    write15.text(home_txt, 53, 5)
    write15.text(pihole_txt, 53, 22)
    write15.text(ups_txt, 53, 39)
    oled.show()


# Turn on display
def turn_on_display():
    global oled, gfx, write15, write20 #TODO?
    gpio_2.value(1)  
    time.sleep(0.2)

    # Oled display init
    i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=const(400000))  
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    oled.fill(0)
    oled.contrast(128) 
    gfx = GFX(128, 64, oled.pixel)  
    write20 = Write(oled, ubuntu_20)
    write15 = Write(oled, ubuntu_15)
    

# Shutdown display        
def turn_off_display():
    oled.poweroff() 
    gpio_2.value(0)
    time.sleep(0.1)


# Display turn on? shutdown? refresh?
def display():
    global display_state
    
    if pin_monitor.value() == 1:
        if display_state:
            refresh_display()
        else:
            turn_on_display()
            display_state = True        
    else:
        if display_state:
            turn_off_display()
            display_state = False
        else:
            time.sleep(0.14) # match time as if display was on


# Ups checking, ugly but works...
def power_outage_check():
    global power_outage, power_outage_time, power_outage_triggered
    wdt.feed()

    # power outage?
    if not power_outage:
        if pin_ups.read_u16() > adc_threshold:      # fast check
            pass
        elif get_adc_average(20) > adc_threshold:   # double check with average
            pass
        else:                                       # power outage! start timer
            power_outage = True
            power_outage_time = current_time 

    # power outage! 
    elif power_outage:
        # power off for more than 15 mins?
        if not power_outage_triggered and (power_outage_time + adc_time_delay) <= current_time: # power off for more than 15mins?
            power_outage_triggered = True        
            return "turn off"    

        if pin_ups.read_u16() < adc_threshold:      # pwr back? fast check
            pass
        elif get_adc_average(20) < adc_threshold:   # pwr back? double check with average
            pass
        else:                                       # power restored, stop timer
            power_outage = False
            power_outage_time = 0
            power_outage_triggered = False
            return "power back"
      

# Error checking
def check_for_error(time, name):  
    global pihole_txt, home_txt, email_txt
    if time <= current_time:
        if name == "home":
            home_txt = "ERROR"
            email_txt = "Home Assistant ERROR!"
        elif name == "pihole":
            pihole_txt = "ERROR"
            email_txt = "Pihole ERROR!"
        return True


# Pihole heartbeat interrupt
def irq_pihole(pin):
    global pihole_time, pihole_debounce
    if not pihole_debounce:   
        pihole_time = current_time + 190   
        pihole_debounce = True


# Home heartbeat interrupt
def irq_home(pin):
    global home_time, home_debounce
    if not home_debounce:
        home_time = current_time + 190
        home_debounce = True
      

# Interrupt handlers init
pin_pihole.irq(trigger = Pin.IRQ_FALLING, handler = irq_pihole)
pin_home.irq(trigger = Pin.IRQ_FALLING, handler = irq_home)


# Misc
current_time = time.time()                # current time
home_time = current_time + const(200)     # home start timer 
pihole_time = current_time + const(200)   # pihole start timer 
wdt = WDT(timeout = const(8300))          # pi pico watchdog (max timeout)
power_outage_time = 0                     # timer 
gc.collect()                              # gc


# Main loop
while not stop_all_code:
    try:
        for i in range(5):
            for j in range(5):
                wdt.feed()
                display()
                current_time = time.time()
                
                #check all Raspberry Pis for errors
                # if (check_for_error(home_time, "home")  
                # or  check_for_error(pihole_time, 'pihole')):
                #     error_found()
                #     break
                if check_for_error(pihole_time, 'pihole'):
                    error_found()
                    break

        # ups check
        power = power_outage_check()
        if power == "turn off":
            shutdown_pi()
            email_txt = "Ups low battery. Shutting down!"
            ups_txt = "OFF"
            error_found()
        elif power == "power back" and ups_txt != "ok!":
            ups_txt = "ok!"

        # debounce reset
        home_debounce = False
        pihole_debounce = False
        gc.collect()

    except KeyboardInterrupt:
        exit()
    except:
        machine.reset()
        pass


# Error found! loop forever until pico is restarted
while stop_all_code:
    try:
        for m in range(5):
            for n in range(5):
                wdt.feed()
                display()
                current_time = time.time()

        # ups check
        power = power_outage_check()
        if power == "turn off":
            shutdown_pi()
            email_txt = "Ups low battery. Shutting down!"
            ups_txt = "OFF"
            error_found()
        elif power == "power back" and ups_txt != "ok!":
            ups_txt = "ok!"  
        gc.collect()

    except KeyboardInterrupt:
        exit()
    except:
        pass # ;)
    

