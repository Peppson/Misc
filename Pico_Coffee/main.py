
####### Pico_Coffee 3.0 #######

# http://192.168.1.3/
# ändra ip i båda index.html för xml

import time, network, socket, _thread, gc, machine
from machine import Pin, PWM, ADC
from micropython import const
from Wifi import secrets


# Globals / constants
coffee_status = False                        # on/off?
coffee_count = 0                            # coffee count
deepsleep_time = const(8*1000*60*60)        # deepsleep processor
adc_reading = ADC(27)                       # adc pin
adc_offset = const(7000)                    # adc on/off threshold value
servo = PWM(Pin(0))                         # servo pin
servo.freq(50)                              # servo freq
servo_on = const(1650)                      # servo pos
servo_off = const(4300)                     # servo pos
servo_middle = const(3300)                  # servo pos
wlan_on = machine.Pin(23)                   # wlan turn on/off wifichip
ssid = secrets['ssid']                      # wlan ssid
password = secrets['password']              # wlan password
wlan = network.WLAN(network.STA_IF)         # wlan init


# log.csv + html 
with open("log.csv", "r") as f:
    coffee_count = int(f.readline(6))

with open("index_off.html", "r") as f:
    html = f.read()
    

####### Functions #######


# Save to flash memory
def write_to_flash_mem():
    with open("log.csv", "w") as f:
        f.write(str(coffee_count + 1))
        
    return coffee_count + 1


# Wifi connect
def Connect_wifi(ssid, password):
    wlan.active(True)
    wlan.ifconfig(('192.168.1.3','255.255.255.0','192.168.1.1','255.255.255.0')) # Static Ip
    wlan.connect(ssid, password)

    # Connect or not
    max_wait = 15
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        time.sleep(1)
                  
    # Connection error?
    if wlan.status() != 3:
        raise RuntimeError('network connection failed')
    else:
        status = wlan.ifconfig()
        print( 'ip = ' + status[0] )
              
    # Open socket
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)

    return addr, s


# Servo position
def servo_position(pos):
    servo.duty_u16(pos)
    time.sleep(0.3)
    servo.duty_u16(servo_middle)
    

# Deepsleep 
def pico_deepsleep():   
    wlan.active(False)
    wlan_on.value(0)
    time.sleep(0.3)
    machine.deepsleep(deepsleep_time)


# Init
servo.duty_u16(servo_middle)
addr, s = Connect_wifi(ssid, password)


# Main core 
def main_core(): 
    while True: 
        try:            
            # await website command
            cl, addr = s.accept()
            request = cl.recv(const(1024))
            request = (str(request)[1:17])

            # what command
            xml = request.find('/xml')
            turn_on = request.find('/toggle/on')
            turn_off = request.find('/toggle/off')
            refresh = request.find('GET / HTTP')
            deepsleep = request.find('/deepsleep')
            
            # xml 
            if xml == 5:
                cl.send(const('HTTP/1.0 200 OK\r\nContent-type: text/xml\r\n\r\n'))
                cl.send(str(coffee_status))
                cl.close()
            
            # turn on
            if turn_on == 5 and not coffee_status:
                servo_position(servo_on)
                cl.send(const('HTTP/1.0 200 OK\r\nContent-type: text/xml\r\n\r\n'))
                cl.close()
             
            # turn off
            elif turn_off == 5:
                servo_position(servo_off)
                cl.send(const('HTTP/1.0 200 OK\r\nContent-type: text/xml\r\n\r\n'))
                cl.close()
                
            # refresh
            elif refresh == 1:
                cl.send(const('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'))
                cl.send(html)
                cl.close()
                
            # deepsleep
            elif deepsleep == 5:
                time.sleep(0.5)
                pico_deepsleep()
            else:
                pass
        except:
            #machine.reset() #TODO
            pass # ;)
            

# Core 1 loop
def core1():
    global coffee_status, html
    adc_list = []
    
    while True:
        for i in range(8):

            if not wlan.isconnected():
                time.sleep(2) 
                if not wlan.status(): # still no connection?
                    machine.reset()
                
            # average adc_reading values  
            for j in range(const(100)):
                adc_list.append(adc_reading.read_u16())
            adc_avg = int((sum(adc_list)) / (len(adc_list)))
            adc_list.clear()
            
            # coffee_status update
            if adc_avg >= adc_offset and not coffee_status:
                coffee_status = True
                with open("index_on.html", "r") as f:
                    html = f.read()
                write_to_flash_mem() 
                 
            elif adc_avg < adc_offset:
                coffee_status = False
                with open("index_off.html", "r") as f:
                    html = f.read()

            time.sleep(1)
        gc.collect()

gc.collect()                      
_thread.start_new_thread(core1, ())       
main_core()



