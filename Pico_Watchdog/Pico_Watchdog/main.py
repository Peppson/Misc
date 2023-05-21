
from machine import Pin
start_button = Pin(18, Pin.IN, Pin.PULL_UP) 

if start_button:
    import Pico_watchdog 

