
from machine import Pin
button = Pin(2, Pin.IN, Pin.PULL_DOWN) 

# Debug
if button.value():
    pass
# Normal operation
else: 
    import garage_parking_assistant
    


