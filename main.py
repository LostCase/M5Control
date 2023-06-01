#-----------------------
# info
#-----------------------

# Control box for the air vent

print('LOAD: main.py')

#-----------------------
# variables
#-----------------------

wifi_essid = 'Gosti'
wifi_password = 'Gosti931'

eziot_api_key = 'N7KY8XR4RLKGCQOY' 
eziot_api_secret = 'MRTJU4N536TH69ES'
eziot_group_Control = 'Control'
eziot_device_Control = 'Control'
eziot_device_Button = 'OnOffButton1'
eziot_group_Outside = 'Temperature'
eziot_device_Outside = "Sensor1"
eziot_group_Parent = 'Temperature'
eziot_device_Parent = "SensorInsideParent"

tempOutsideLCL = 13 # when outside temperature is too cold
tempInsideUCL = 21 # target inside temperature
tempInsideLCL = 19 
hysteresis = 0.5 # temperature hysteresis
tUCL = tempInsideUCL
tLCL = tempInsideLCL


#-----------------------
# imports
#-----------------------


import sys
import time
from machine import Pin, I2C
import pcf8574
import eziot_micropython_minimal as eziot


#-----------------------
# main loop
#-----------------------

def run():

    # setup loop (loop forever)
    while 1:

        # catch
        try:

            # set up wifi
            #eziot.wifi_scan()
            eziot.wifi_connect(wifi_essid,wifi_password)

            # set up eziot
            eziot.api_key = eziot_api_key
            eziot.api_secret = eziot_api_secret
            # initialize i2c
            i2c = I2C(scl=Pin(32), sda=Pin(26))
            print('i2c is initialized')
            # set up relay
            pcf = pcf8574.PCF8574(i2c, 39) # relay board i2c address is 39
            print('pfc is initialized')
            # set up screen display with NeoPixel
            #pinNeo = Pin(27, Pin.OUT) # Pin number 27 is the LED matrix
            #np = NeoPixel(pinNeo, 25) # 25 LEDs in the matrix
            #np[0]= (255,255,255)
            #np.write()
            
            # set up button pin:
            #btnPin = Pin(39, Pin.IN) # pin 39 is button
            # function loop (loop forever)
            floops = 0
            mode = 0 # turn OFF the fan by default
            
            tempOutsideLCL = 13 # when outside temperature is too cold
            tempInsideUCL = 21 # target inside temperature
            tempInsideLCL = 19 
            hysteresis = 0.5 # temperature hysteresis
            tUCL = tempInsideUCL
            tLCL = tempInsideLCL

            while 1:
                
                # track loops
                floops += 1
                print('LOOP:',floops)
                
                for row in eziot.get_data(after = 0, group = eziot_group_Control, device = eziot_device_Button):
                    print('Pulling the mode from the server')
                    mode = row[6]
                    print('updated mode is ', mode)
                    
                # MAIN logic section
                #Control conventions: data1(power): 0=Off, 1=On, None=ignore. data2(mode): 0=Off, 1=On, 2=Auto, 3 = error
#                 print('main logic section')
                print('mode is ', mode)
                if mode == 0: #manual OFF
                    print('manual OFF mode')
                    pcf.pin(1, 1) # set pin 1 LOW
                    eziot.post_data(group=eziot_group_Control,device=eziot_device_Control,data1=0,data2=0,data3=None,data4=None)
                    print('LOADED OFF to EZIOT')
                elif mode == 1: #manual ON
                    print('manual ON mode')
                    pcf.pin(1, 0) # set pin 1 HIGH
                    eziot.post_data(group=eziot_group_Control,device=eziot_device_Control,data1=1,data2=1,data3=None,data4=None)
                    print('LOADED ON to EZIOT')
                elif mode == 2: # AUTO
                    print('AUTO mode')
                    #first load and get data to update the time stamp
                    eziot.post_data(group=eziot_group_Control,device=eziot_device_Control,data1=None,data2=2,data3=None,data4=None)
                    for row in eziot.get_data(after = 0, group = eziot_group_Control, device = eziot_device_Control):
                        timeNow = row[1] # this gets the most up-to-date time
                        print('Time Now:', timeNow)
                    
                    # load the temperature data from the outside sensor
                    print('loading the outside sensor data')
                    for row in eziot.get_data(after = 0, group = eziot_group_Outside, device = eziot_device_Outside):
                        timeO, tempO, humO, co2O, vocO  = row[1] ,row[6], row[7], row[8], row[9]
                        print('time=', timeO, ' temp=',tempO,' hum=',humO,' co2=', co2O,' voc=', vocO )
                        
                    # load the temperature data from the parent sensor
                    print('loading the parent sensor data')
                    for row in eziot.get_data(after = 0, group = eziot_group_Parent, device = eziot_device_Parent):
                        timeP, tempP, humP  = row[1] ,row[6], row[7]
                        print('time=', timeP, ' temp=',tempP,' hum=',humP)

                    # calculate conditions
#                    inRangeO = (tempO > -10) and (tempO < 50)
                    inRangeO = -10 < tempO < 50
                    inRangeP = 5 < tempP < 50
                    tooCold = tempO < tempOutsideLCL
                    stinky = vocO > 50
                    cooling = tempP > tempO
        
                    timeSince = (timeNow - timeO) /60 # time interval in minutes
                    print('Time since the last temperature update ', timeSince)
                    if timeSince > 15:
                        print('Temperature sensor seems to be stuck') #if >15 min turn off the fan
                        pcf.pin(1, 1) # set pin 1 LOW
                        eziot.post_data(group=eziot_group_Control,device=eziot_device_Control,data1=0,data2=30,data3=None,data4=None)
                    elif (not inRangeO) or (not inRangeP):
                        print('Temperature out of range')
                        pcf.pin(1, 1) # set pin 1 LOW
                        eziot.post_data(group=eziot_group_Control,device=eziot_device_Control,data1=0,data2=31,data3=None,data4=None)
                    elif stinky:
                        print('Too Stinky')
                        pcf.pin(1, 1) # set pin 1 LOW
                        eziot.post_data(group=eziot_group_Control,device=eziot_device_Control,data1=0,data2=32,data3=None,data4=None)                                            
                    elif cooling:
                        print('Cooling mode')
                        print('Control limits tLCL=', tLCL,'tUCL=', tUCL) #line 89
                        if tempP>tUCL:
                            print('Turning ON the Parent Fan')
                            pcf.pin(1, 0) # set pin 1 HIGH if outside temp is below the setpoint
                            eziot.post_data(group=eziot_group_Control,device=eziot_device_Control,data1=1,data2=2,data3=None,data4=None)
                            tUCL = tempInsideUCL - hysteresis
                            tLCL = tempInsideLCL 
                        elif tempP<tLCL:
                            print('Turning OFF the Parent Fan')
                            pcf.pin(1, 1) # set pin 1 LOW
                            eziot.post_data(group=eziot_group_Control,device=eziot_device_Control,data1=0,data2=2,data3=None,data4=None)
                            tLCL = tempInsideLCL + hysteresis
                            tUCL = tempInsideUCL
                                                    
                #end of AUTO logic
                    
                # wait for next loop
                # you may want to add deep sleep here
                print('Sleeping for 10 seconds')
                time.sleep(10)

                #instead of just waiting, blink an LED on pin2
#                 for x in range(150):
#                     Pin(2,Pin.OUT,value=1)
#                     time.sleep_ms(200)
#                     Pin(2,Pin.IN)
#                     time.sleep_ms(3800)
                    

        # end loop            
        except KeyboardInterrupt:
            print('KeyboardInterrupt')
            break # end loop

        # error (show and retry, never end)
        except Exception as e:
            sys.print_exception(e)
            print('Major ERROR in main loop.')
            print('Pause 10 seconds...',end=' ')
            time.sleep(10)
            print('continue.')

#-----------------------
# self run
#-----------------------

if __name__ == '__main__':
    run()

#-----------------------
# end
#-----------------------
