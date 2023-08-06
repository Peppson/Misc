
// ###### Löd_Station 4.3 ######  
// old bootloader

#include <Wire.h> 
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27,20,4);

#define tempSensor A0
#define knob A7
#define iron 10
#define LED 3

const int
minTemp = 22,       // Minimum aquired iron tip temp during testing (°C)
maxTemp = 530,      // Maximum aquired iron tip temp during testing (°C)        
minADC  = 204,      // Minimum aquired ADC value during minTemp testing
maxADC  = 600,      // Maximum aquired ADC value during maxTemp testing 
maxPWM  = 255,      // Maximum PWM Power 255                                    
avgCounts = 25;     // Number of avg samples
 
int
pwm = 0,                    
knobRAW = 0,        
counter = 0,
iron_off = 0,            
setTemp = 0,        
setTempAVG = 0,
setTempAVG_old = 0,     
currentTempAVG = 0; 

float 
currentTemp = 0.0,  
store = 0.0,        
knobStore = 0.0;    

const unsigned long
off_timer = (480000),  // Turn of iron after n minutes (n * 60 * 1000)
lcdInterval = 80;

unsigned long
current_time = 0,
start_time = millis(),
currentMillis = 0,
previousMillis = 0;  


void setup(){
  pinMode(tempSensor,INPUT);   // Set Temp Sensor pin as INPUT
  pinMode(knob,INPUT);         // Set Potentiometer Knob as INPUT
  pinMode(iron,OUTPUT);        // Set MOSFET PWM pin as OUTPUT
  pinMode(LED,OUTPUT);         // Set LED Status pin as OUTPUT
  lcd.backlight();
  lcd.init();
  lcd.clear();
  lcd.setCursor(0,1);lcd.print(" Preset: ");  
  lcd.setCursor(0,0);lcd.print(" Actual: ");
  //Serial.begin(9600);
}


void loop(){

  // Gather Sensor Data
  knobRAW = analogRead(knob); 
  setTemp = map(knobRAW,0,1023,minTemp,maxTemp);                              // Scale pot analog value into temp unit
  currentTemp = map(analogRead(tempSensor),minADC,maxADC,minTemp,maxTemp);    // Scale raw analog temp values as actual temp units
  

  // Get Average of Temp Sensor and Knob
  if(counter < avgCounts){  
    store = store + currentTemp;
    knobStore = knobStore + setTemp;
    counter++;
  }
  else{
    currentTempAVG = (store/avgCounts)-1;  
    setTempAVG = (knobStore/avgCounts);

    if (((setTempAVG >= setTempAVG_old - 1) && (setTempAVG <= setTempAVG_old + 1)) || (setTempAVG_old == 0)){
      // Do nothing  
    }
    else {
      start_time = millis();  // Reset start_time only if new value
    }
    knobStore=0;  
    store=0;      
    counter=0; 
    setTempAVG_old = setTempAVG;
  }

  // Iron on after n min without any change? Turn off
  current_time = millis();
  if (current_time - start_time >= off_timer){
    iron_off = 1;
  }
  else{
    iron_off = 0;
  }


  // PWM Soldering Iron Power Control
  if(analogRead(knob) <=1 ){            // Turn off iron when knob as at its lowest (iron shutdown)
    digitalWrite(LED,LOW);
    pwm=0;
  }
  else if(currentTemp <= setTemp){      // Turn on iron when iron temp is lower than preset temp
    if(iron_off == 0){
      digitalWrite(LED,HIGH);
      pwm=maxPWM;  
    }
    else {                              // Turn off iron if iron_off == 1 (after n of minutes)
      digitalWrite(LED,LOW);
      pwm=0;
    }
  }
  else{                                 // Turn off iron when iron temp is higher than preset temp
    digitalWrite(LED,LOW);
    pwm=0;
  }
  analogWrite(iron,pwm);                // Apply the aquired PWM value from the three cases above



  // Display Data
  currentMillis = millis();           
  if (currentMillis - previousMillis >= lcdInterval){ 
    previousMillis = currentMillis;

    if(analogRead(knob)<=1){
      lcd.setCursor(10,1);lcd.print("OFF   ");
    }
    else if (iron_off == 0){
      lcd.setCursor(10,1);lcd.print(setTempAVG,1);lcd.print((char)223);lcd.print("C ");
    }
    else {
      lcd.setCursor(10,1);lcd.print("A OFF ");
    }
    if(currentTemp < minTemp + 8){
      lcd.setCursor(10,0);lcd.print("COLD  ");
    }
    else{
      lcd.setCursor(10,0);lcd.print((currentTempAVG),1);lcd.print((char)223);lcd.print("C ");
    }   
  } 
}

