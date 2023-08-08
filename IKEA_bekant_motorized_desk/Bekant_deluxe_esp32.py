
########## Bekant Deluxe 5.9 [ESP32] ##########
# Shitshow but works!

#659
#1058
#659
#1



import machine, time, ssd1306, _thread, gc
from ssd1306 import SSD1306_I2C
from micropython import const
from machine import Pin, I2C
from write import Write
from gfx import GFX
from oled.fonts import ubuntu_12, ubuntu_15, ubuntu_20
from vl53l0x import VL53L0X
gc.collect()


# Pins external resistor 4.7k ohm pull down + internal pulldown
knapp_1 = Pin(23, Pin.IN, Pin.PULL_DOWN)
knapp_2 = Pin(35, Pin.IN, Pin.PULL_DOWN)
knapp_3 = Pin(32, Pin.IN, Pin.PULL_DOWN)
knapp_4 = Pin(34, Pin.IN, Pin.PULL_DOWN)

gpio_up = Pin(14, Pin.OUT, Pin.PULL_DOWN)    #14 (off = 25)
gpio_down = Pin(2, Pin.OUT, Pin.PULL_DOWN)   #2  (off = 27)
gpio_up.value(0)
gpio_down.value(0)


# Offsets const()
pre_offset = const(15)         # hur många mm innan target, ska ström brytas?  
target_offset = const(1)       # hur nära (+-) target i mm som är godkänt      
try_offset = const(5)          # hur många försök på finjustering              
cal_offset = const(16)         # +- i mm calibrering på totalhöjden (med bord)           
min_höjd = const(642)          # min höjd utan cal_offset (642)              
max_höjd = const(1259)         # max höjd utan cal_offset (1259)


# Globals
interrupt_off = 0
error_on = 0


# Oled display init
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=const(400000))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled.contrast(const(800))
oled.rotate(0)
oled.fill(0)
gfx = GFX(128, 64, oled.pixel)
write20 = Write(oled, ubuntu_20)
write15 = Write(oled, ubuntu_15)
write12 = Write(oled, ubuntu_12)


# Time of Flight sensor init (tof)
if 0x29 not in i2c.scan():
    print("Failed to find device")
    raise RuntimeError()
    
tof = VL53L0X(i2c)
budget = tof.measurement_timing_budget_us
tof.set_measurement_timing_budget(const(40000)) 
tof.set_Vcsel_pulse_period(tof.vcsel_period_type[0], 18) #12 (18max) range   18
tof.set_Vcsel_pulse_period(tof.vcsel_period_type[1], 14) #8  (14max) range   14
for x in range(3):
    tof.ping() # första reading alltid fel, så tar den i boot fasen

    
# Läs in sparad bordshöjd från log.csv
with open("log.csv", "r") as f:
    höjd_1       = int(f.readline(6))  #rad 0
    höjd_2       = int(f.readline(6))  #rad 1
    höjd_current = int(f.readline(6))  #rad 2
    oled_display = int(f.readline(6))  #rad 3
time.sleep(0.01)



def read_from_flash(row):
    with open("test.csv", "r") as f:
        for i in range(row):
            value = f.readline().strip()
            
    return value




########## Functions ##########


# Spara ny höjd till log.csv
def write_to_file():
    listan = [höjd_1, höjd_2, höjd_current, oled_display]
    with open("log.csv", "w") as f:
        for i in listan:
            f.write(f"{i}\n") 
    time.sleep(0.01)
        
    
# på min/max höjd?
def min_max_check():
    if höjd_current < (min_höjd + 3):  
        return 8   
    elif höjd_current > (max_höjd - 3): 
        return 9
    else:
        return 1
  
  
# Finjustering time.sleep()
def sleep_time_calc(skillnad):
    if skillnad > 10:
        return 0.54
    elif skillnad > 5 <= 10:
        return 0.4
    elif skillnad > 3 < 5:
        return 0.28
    elif skillnad > 1 <= 3:
        return 0.27
    else:
        return 0.24
 
   
# Beräkna sensor average från avg_list[]
def sensor_avg_calc(nr):
    return round((float(sum(nr))) / (len(nr)))


# Skapa list[] med sensor samples 
def sensor_sample():
    do_once = 0
    avg_list = []
    for x in range(60):
        reading = tof.ping()
        avg_list.append(reading)
        if len(avg_list) >= 50 and do_once == 0:
            avg_list.pop(0)
            do_once = 1
            
    return sensor_avg_calc(avg_list)


# Spara höjd på vilken knapp? 
def save_to_knapp():
    global höjd_current, höjd_1, höjd_2, oled_display, interrupt_off
    interrupt_off = 1
    avg_list = []
    oled_display = 5
    vilken_knapp = 0
    for x in range(const(500)):
        time.sleep(0.01)
        
        # return ifall ingen knapp är vald
        if x > const(450):
            oled_display = (min_max_check())
            return

        # knapp logic, how to if-sats lul 
        elif ((knapp_1.value() == 1 and knapp_2.value() == 0)) or ((knapp_1.value() == 0 and knapp_2.value() == 1)): 
            oled_display = 6
            start_tid = time.ticks_ms()
            run_once = 0
            
            # append sensor readings till list[] för average, medans knapp är intryckt för save
            while knapp_1.value() == 1 or knapp_2.value() == 1:
                if len(avg_list) < 90: 
                    reading = tof.ping()
                    avg_list.append(reading)
                else:
                    pass
                
                # vilken knapp har tryckts?
                if run_once == 0:
                    run_once = 1
                    if knapp_1.value() == 1 and knapp_2.value() == 0:
                        vilken_knapp = 1
                    elif knapp_1.value() == 0 and knapp_2.value() == 1:
                        vilken_knapp = 2
                    else: # error?
                        del avg_list
                        return
                    
            tid_pressed = time.ticks_ms() - start_tid

            # knapp intryckt för kort
            if tid_pressed <= const(4100):
                oled_display = 3
                del avg_list
                time.sleep(1.3)
                oled_display = (min_max_check())
                return
            
            # knapp intryckt mer än 4s
            else:
                # spara på vilken knapp?
                if vilken_knapp == 1: 
                    oled_display = 21      
                elif vilken_knapp == 2:
                    oled_display = 22
                
                # fortsätt append medans "saved to button x!"
                for i in range(52):
                    avg_list.append(tof.ping())
                
                # cleanup + write to log.csv
                avg_list.pop(0)
                höjd_current = sensor_avg_calc(avg_list)
                del avg_list
                if vilken_knapp == 1:
                    höjd_1 = höjd_current      
                elif vilken_knapp == 2:
                    höjd_2 = höjd_current
                oled_display = (min_max_check())                
                write_to_file()
                return
        else:
            pass

    
# Auto upp/ner till target höjd + finjustering
def auto_move_table(target):
    global höjd_current, oled_display, sensor_read, error_on, interrupt_off
    interrupt_off = 1
    sensor_read = tof.ping()
    
    # redan på samma höjd?   
    if (höjd_current <= (target + 2)) and (höjd_current >= (target - 2)):
        if error_on == 0:
            oled_display = 2 
            time.sleep(1.5)
            oled_display = (min_max_check()) 
            return
        if error_on == 1: # skippar ovanstående "redan på samma höjd?" if error == 1" så man kan köra igen
            error_on = 0
            return
    
    # åka till min höjd?
    if (höjd_current > target) and (target < min_höjd + 5):
        while sensor_read > (target + pre_offset):
            gpio_down.value(1)
            sensor_read = tof.ping()
            if oled_display != 10:
                oled_display = 10 
        gpio_down.value(1)
        time.sleep(1.2)
        gpio_down.value(0)
        höjd_current = target
        oled_display = 12
        time.sleep(2.5)
        oled_display = (min_max_check())
        write_to_file()
        return

    # åka till max höjd?
    if (höjd_current < target) and (target > max_höjd - 5):
        while sensor_read < (target - pre_offset):
            gpio_up.value(1)
            sensor_read = tof.ping()
            if oled_display != 11: 
                oled_display = 11  
        gpio_up.value(1)
        time.sleep(1.2)
        gpio_up.value(0)
        höjd_current = target
        oled_display = 12
        time.sleep(2.5)
        oled_display = (min_max_check())
        write_to_file()
        return
    
    # ner mot target normalt
    if höjd_current > target:
        while sensor_read > (target + pre_offset):
            gpio_down.value(1)
            sensor_read = tof.ping()
            if oled_display != 10: 
                oled_display = 10 
            
    # upp mot target normalt
    else:
        while sensor_read < (target - pre_offset):
            gpio_up.value(1)
            sensor_read = tof.ping()
            if oled_display != 11: 
                oled_display = 11 
     
    
    # Finjustering till target, bara godkänt när +- 1mm från target
    gpio_up.value(0)
    gpio_down.value(0)
    oled_display = 14

    # adjust max (try_offset) times
    for x in range(try_offset):
        avg = sensor_sample()
        
        # on target? är avg == (target +- 1mm)?
        if (avg == target) or ((avg <= (target + target_offset)) and (avg >= (target - target_offset))):
            break
        
        # efter x finjusterings försök
        elif x == (try_offset - 1):
            oled_display = 4
            error_on = 1
            gc.collect()
            return
        
        # adjust down
        elif avg > target:
            skillnad = avg - target #hur länge ska vi åka ner?  
            gpio_down.value(1)
            time.sleep(sleep_time_calc(skillnad))
            gpio_down.value(0)
            
        # adjust up
        elif avg < target:
            skillnad = target - avg #hur länge ska vi åka up?
            gpio_up.value(1)
            time.sleep(sleep_time_calc(skillnad))
            gpio_up.value(0)
    
    # on target!
    if avg > 16: # buggar ur annars
        höjd_current = target
        oled_display = 12
        time.sleep(2.5)
        oled_display = (min_max_check())
        write_to_file() 
    
                                         
# Upp eller ner manuellt, knapp_3 eller knapp_4       
def manual_move_table(knapp1, knapp2):
    global höjd_current, oled_display, sensor_read, interrupt_off
    interrupt_off = 1
    time.sleep(0.04)
    
    # gpio upp/ner + oled_display global (sensor) beroende på vilken knapp
    if knapp1 == knapp_4:
        gpio = gpio_up
        sensor = 11
    else:
        gpio = gpio_down
        sensor = 10

    # knapp_3 och knapp_4 tryckta samtidigt? 
    if knapp1.value() == 1 and knapp2.value() == 1:
        save_to_knapp()
        gc.collect()
        return
    
    # endast 1 knapp tryckt?
    elif knapp1.value() == 1 and knapp2.value() == 0:
        while knapp1.value() == 1:
            sensor_read = tof.ping()
            gpio.value(1)
            if oled_display != sensor:
                oled_display = sensor      
            else:
                pass
            
        # Beräkna ny avg höjd eller bli interruptad
        gpio.value(0)
        avg_list = []
        for x in range(54):
            if knapp1.value() == 1 or knapp2.value() == 1:
                del avg_list
                return
            else:
                sensor_read = tof.ping()
                avg_list.append(sensor_read)
                if len(avg_list) >= 53:
                    avg_list.pop(0)
                if x > 4 and oled_display != 0: # forsätt visa sensor på skärm kort tid efter knapp har släppts
                    oled_display = 0 

        höjd_current = sensor_avg_calc(avg_list)
        del avg_list
        oled_display = (min_max_check())
        write_to_file()
        gc.collect()
          
          
# Main Core. Polling istället för interrupt, fungerar mkt bättre
def main_core():
    global interrupt_off
    while True:
        try:
            for i in range (50):
                for j in range(const(5000)):
                    
                    # vilken knapp?
                    if knapp_1.value() == 1 and interrupt_off == 0:
                        auto_move_table(höjd_1)

                    elif knapp_2.value() == 1 and interrupt_off == 0:
                        auto_move_table(höjd_2)
 
                    elif knapp_3.value() == 1 and interrupt_off == 0:
                        manual_move_table(knapp_3, knapp_4)
                        
                    elif knapp_4.value() == 1 and interrupt_off == 0:
                        manual_move_table(knapp_4, knapp_3)

                # interrupt reset
                interrupt_off = 0
                
            # garbage collect
            gc.collect()
            
        except:
            machine.reset()    



########## Core1 ##########


# Core1 oled detaljer    
def core1_grid():
    oled.fill(0)
    write12.text("Min                          Max", 5, 41)
    write12.text("   '     '     '     '     '     '     '", 0, 52)
    gfx.rect(0, 0, 128, 64, 1)
    
    
# Sensor i "realtime" up/down # Spagetthi 
def core1_grid_moving(nr):
    gfx.fill_rect(const(116), 4, 8, 9, 0)
    debounce = 0
    while oled_display == nr:
        math = (sensor_read - const(642)) / (const(617))  # (x - min) / (max - min) = %
        math_sensor = ((sensor_read + 16) / 10)
        
        if oled_display != nr:
            break
        # nr/up i cm
        elif math_sensor < const(100):
            write20.text("   " + str(math_sensor)[:4], 22, 18) #22 18
        else:
            write20.text(str(math_sensor)[:5], 23, 18)         #22 18
        # bar down
        if nr == 10:
            if (sensor_read < min_höjd + 8) and (debounce == 0):
                gfx.rect(3, 41, 22, 14, 1)
                debounce = 1
            else:
                gfx.fill_rect(int(10 + (math * const(124))), 59, (116 - (math * const(124))), 3, 0) # inverterad progress bar för att "ta bort" den andra    
        # bar up
        else:
            if (sensor_read > min_höjd + 8) and (debounce == 0):
                gfx.rect(3, 41, 22, 14, 0) # inverterad för att "ta bort"
                debounce = 1
            else:
                gfx.fill_rect(2, 59, ((math * 124) + 8), 3, 1) # progress bar (% * antal pixlar) 
        oled.show()


# höjd_current på display
def core1_höjd_current():
    math = (höjd_current - const(642)) / (const(617))           # (x - min) / (max - min) = %
    gfx.fill_rect(2, 59, (int(math * 124) + 8), 3, 1)           # progress bar (% * antal pixlar)
    math_sensor = (höjd_current + 16)/10                        # över/under tretal?
    
    if math_sensor < const(100):
        write20.text("   " + str(math_sensor)[:4] + " cm   ", 22, 18)
    else:
        write20.text(str(math_sensor)[:5] + " cm   ", 23, 18)
        
 
# Inväntar core1_display commands och sedan visar på skärm
def oled_core1():
    oled_display_old = 0
    grid = 0
    while True:
        try:
            # uppdatera endast om ny info finns
            if oled_display != oled_display_old:
                oled_display_old = oled_display
                
                # samma höjd?
                if oled_display == 2:
                    oled.fill(0)
                    grid = 0
                    gfx.rect(0, 0, 128, 64, 1)
                    write20.text("Already on", 17, 10)
                    write20.text(str((höjd_current + 16)/10) + " cm!", 29, 32)
                
                # error
                elif oled_display == 4:
                    oled.fill(0)
                    grid = 0
                    gfx.rect(0, 0, 128, 64, 1)
                    write20.text("ERROR!", 31, 11)
                    write12.text("Wrong height, go again", 7, 37)
                
                # save on button?
                elif oled_display == 5:
                    oled.fill(0)
                    grid = 0
                    gfx.rect(0, 0, 128, 64, 1)
                    write20.text("Save on", 29, 10) 
                    write15.text("which button?", 19, 32)
                
                # progressbar, till "Too short" eller "Saved on button x!"
                elif oled_display == 6:
                    run_once_2 = 0
                    
                    # knapp intryckt för spara
                    while True:
                        if run_once_2 == 0:
                            for i in range(const(96)):
                                gfx.fill_rect(2, 60, (i*1.3), 2, 1)
                                oled.show()
                                if oled_display != 6:
                                    break
                            run_once_2 = 1
                        if oled_display != 6:
                                    break

                    # too short  
                    if oled_display == 3:                 
                        oled.fill(0)
                        write20.text("Too short!", 19, 21)
                        gfx.rect(0, 0, 128, 64, 1)
                        
                    # button 1
                    elif oled_display == 21:
                        oled.fill(0)
                        gfx.rect(0, 0, 128, 64, 1)
                        write20.text("Saved on", 25, 10)
                        write20.text("button 1!", 25, 30)
                        
                    # button 2
                    elif oled_display == 22:
                        oled.fill(0)
                        gfx.rect(0, 0, 128, 64, 1)
                        write20.text("Saved on", 25, 10)
                        write20.text("button 2!", 25, 30)
                    else:
                        pass
                
                # sensor up/down   
                elif (oled_display == 10) or (oled_display == 11):
                    if grid == 0:
                        core1_grid()
                        grid = 1 #core1 gillar inte globals
                    if oled_display == 10:
                        core1_grid_moving(10)
                    elif oled_display == 11:
                        core1_grid_moving(11)

                # höjd_current + min/max. buggar ur ifall man inte har gfx.rect() precis under här... _thread i micropython...
                elif (oled_display == 1) or (oled_display == 8) or (oled_display == 9):
                    if grid == 0:
                        core1_grid()
                        grid = 1
                        
                    # på någon av de sparade knapparna?
                    if (höjd_current <= höjd_1 + 2) and (höjd_current >= höjd_1 - 2):
                        write12.text("1", const(117), 2)
                    elif (höjd_current <= höjd_2 + 2) and (höjd_current >= höjd_2 - 2):
                        write12.text("2", const(117), 2)

                    # på min/max eller ej
                    if oled_display == 1:
                        gfx.rect(3, 41, 22, 14, 0)  # inverterad
                        gfx.rect(99, 41, 25, 14, 0) # inverterad
                    elif oled_display == 8:
                        gfx.rect(3, 41, 22, 14, 1)  # min
                        gfx.rect(99, 41, 25, 14, 0) # inverterad 
                    elif oled_display == 9:
                        gfx.rect(3, 41, 22, 14, 0)  # inverterad
                        gfx.rect(99, 41, 25, 14, 1) # max
                    core1_höjd_current()
                  
                # on target!
                elif oled_display == 12:
                    oled.fill(0)
                    write20.text("On Target!", 16, 20)
                    gfx.rect(0, 0, 128, 64, 1)
                    oled.show()
                    grid = 0
 
                # adjust
                elif oled_display == 14:
                    grid = 0
                    while oled_display == 14:
                        count = ""
                        for x in range(4):
                            oled.fill(0)
                            write20.text("Adjust" + count, 31, 21)
                            gfx.rect(0, 0, 128, 64, 1)
                            oled.show()
                            if oled_display != 14:
                                break
                            count += "."
                            time.sleep(0.12)
                            
                oled.show()
            else:
                pass                 
        except:
            # krashar inte ifall error
            pass 

gc.collect()
_thread.start_new_thread(oled_core1, ())
main_core()




