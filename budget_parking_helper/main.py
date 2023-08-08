
from machine import Pin
button = Pin(2, Pin.IN, Pin.PULL_DOWN) 


if button.value():
    pass
else:
    import Pico_parking_helper


