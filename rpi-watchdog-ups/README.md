# rpi-watchdog-ups
Monitors two Raspberry Pis using optocouplers to keep them separate from the watchdog.  
It also checks for power outages using a hall effect current sensor. 
 
Everything is connected to a UPS. If there's a longer power outage, the watchdog will shut down all the Pis and send a status email.  

Additionally, a SSD1306 screen displays the system status.


## Hardware

&nbsp;