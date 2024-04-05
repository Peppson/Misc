
from machine import Pin
start_button = Pin(18, Pin.IN, Pin.PULL_UP) 

# Don't start program if "debug button" is pressed during boot 
if start_button:
    import pico_watchdog 

