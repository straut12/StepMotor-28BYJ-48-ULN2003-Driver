#!/usr/bin/env python3

"""
28BYJ-48 Stepper motor with ULN2003 Driver board
Motor instructions received via mqtt from a node-red server

See HARDWARE/MQTT for Wiring and TOPICS

Wiring
Motor1
IN1,2,3,4
Motor2
IN1,2,3,4
"""

from time import sleep
import RPi.GPIO as GPIO
import sys, logging, json
from logging.handlers import RotatingFileHandler
from os import path
from pathlib import Path
import paho.mqtt.client as mqtt
from dataclasses import dataclass
from typing import List

if __name__ == "__main__":

    # Stepper Motor Constants
    FULLREVOLUTION = 4076    # Steps per revolution
    DEFAULTDELAY = 1.6       # default delay in msec

    #==== LOGGING/DEBUGGING SETUP ============#

    def setup_logging(log_dir):
        # Create loggers
        main_logger = logging.getLogger(__name__)
        main_logger.setLevel(logging.INFO)
        log_file_format = logging.Formatter("[%(levelname)s] - %(asctime)s - %(name)s - : %(message)s in %(pathname)s:%(lineno)d")
        log_console_format = logging.Formatter("[%(levelname)s]: %(message)s")

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(log_console_format)

        exp_file_handler = RotatingFileHandler('{}/exp_debug.log'.format(log_dir), maxBytes=10**6, backupCount=5) # 10MB file
        exp_file_handler.setLevel(logging.DEBUG)
        exp_file_handler.setFormatter(log_file_format)

        exp_errors_file_handler = RotatingFileHandler('{}/exp_error.log'.format(log_dir), maxBytes=10**6, backupCount=5)
        exp_errors_file_handler.setLevel(logging.WARNING)
        exp_errors_file_handler.setFormatter(log_file_format)

        main_logger.addHandler(console_handler)
        main_logger.addHandler(exp_file_handler)
        main_logger.addHandler(exp_errors_file_handler)
        return main_logger
    
    #logging.basicConfig(level=logging.DEBUG) # Too many debug output lines. Need to use file logging with RotatingFileHandler instead of basicConfig.
    main_logger = setup_logging(path.dirname(path.abspath(__file__)))
    main_logger.info("setup logging module")
    
    #====   SETUP MQTT =================#
    # Get login info and setup subscribe/publish topics (receiving/sending messages)
    # Initialize incoming/outgoing dictionaries for receiving/sending (on_message and publish)
    # Create mqtt_client object
    # Define callback functions

    home = str(Path.home())                    # Import mqtt and wifi info. Remove if hard coding in python script
    with open(path.join(home, "stem"),"r") as f:
        user_info = f.read().splitlines()

    MQTT_SERVER = '10.0.0.115'                    # Replace with IP address of device running mqtt server/broker
    MQTT_USER = user_info[0]                      # Replace with your mqtt user ID
    MQTT_PASSWORD = user_info[1]                  # Replace with your mqtt password
    MQTT_CLIENT_ID = 'pi4'
    MQTT_SUB_TOPIC = ['pi/stepper', 'pi/stepper/interval', 'pi/stepper/stepreset']
    stepreset = False   # used to reset steps thru nodered gui
    #MQTT_SUB_TOPIC1 = 'pi/stepper'
    #MQTT_SUB_TOPIC2 = 'pi/stepper/interval'
    #MQTT_SUB_TOPIC3 = 'pi/stepper/stepreset'
    MQTT_PUB_TOPIC1 = 'pi/stepper/status'
    MQTT_PUB_TOPIC2 = 'pi/stepper/resetgauge'

    outgoingD = {}
    # Initialize incomingD array/variables. Actual values over-written in stepper create below. From here on will be updated by node-red gui thru user input. Main controller for stepper motors.
    incomingD = {"delay":DEFAULTDELAY, "speed":[2,2], "mode":[0,0], "step":[2038, 2038], "startstep":[0,0]}
    #newmsg = False   # Not using newmsg flag. Instead incomingD is directly referenced inside main motor function
    
    mqtt_client = mqtt.Client(MQTT_CLIENT_ID) # Create mqtt_client object
    
    def on_connect(client, userdata, flags, rc):
        """ on connect callback verifies a connection established and subscribe to TOPICs"""
        global MQTT_SUB_TOPIC
        main_logger.info("attempting on_connect")
        if rc==0:
            mqtt_client.connected = True          # If rc = 0 then successful connection
            for topic in MQTT_SUB_TOPIC:
                client.subscribe(topic)
                main_logger.info("Subscribed to: {0}\n".format(topic))
            main_logger.info("Successful Connection: {0}".format(str(rc)))
        else:
            mqtt_client.failed_connection = True  # If rc != 0 then failed to connect. Set flag to stop mqtt loop
            main_logger.info("Unsuccessful Connection - Code {0}".format(str(rc)))

    def on_message(client, userdata, msg):
        """on message callback will receive messages from the server/broker. Must be subscribed to the topic in on_connect"""
        global newmsg, incomingD, interval, stepreset
        if msg.topic == MQTT_SUB_TOPIC[2]:
            stepreset = json.loads(str(msg.payload.decode("utf-8", "ignore")))
            main_logger.info("Topic:{0} received: {1}".format(msg.topic, stepreset))
        if msg.topic == MQTT_SUB_TOPIC[1]:
            interval = json.loads(str(msg.payload.decode("utf-8", "ignore")))
        if msg.topic == MQTT_SUB_TOPIC[0]:
            incomingD = json.loads(str(msg.payload.decode("utf-8", "ignore")))  # decode the json msg and convert to python dictionary
            #newmsg = True
            # Debugging. Will print the JSON incoming payload and unpack the converted dictionary
            #main_logger.debug("Receive: msg on subscribed topic: {0} with payload: {1}".format(msg.topic, str(msg.payload))) 
            #main_logger.debug("Incoming msg converted (JSON->Dictionary) and unpacking")
            #for key, value in incomingD.items():
            #    main_logger.debug("{0}:{1}".format(key, value))

    def on_publish(client, userdata, mid):
        """on publish will send data to broker"""
        #Debugging. Will unpack the dictionary and then the converted JSON payload
        #main_logger.debug("msg ID: " + str(mid)) 
        #main_logger.debug("Publish: Unpack outgoing dictionary (Will convert dictionary->JSON)")
        #for key, value in outgoingD.items():
        #    main_logger.debug("{0}:{1}".format(key, value))
        #main_logger.debug("Converted msg published on topic: {0} with JSON payload: {1}\n".format(MQTT_PUB_TOPIC1, json.dumps(outgoingD))) # Uncomment for debugging. Will print the JSON incoming msg
        pass 

    def on_disconnect(client, userdata,rc=0):
        main_logger.debug("DisConnected result code "+str(rc))
        mqtt_client.loop_stop()

    #==== HARDWARE SETUP ===============# 
    @dataclass
    class StepperMotor:
        pins: list       # Pins connected to ULN2003 IN1,2,3,4
        mode: int        # Mode 0 = continuous. Mode 1 = incremental
        step: int        # Counter to keep track of motor step (0-4076 in halfstep mode)
        speed: list      # 0=fullstepCCW, 1=halfstepCCW, 2=stop, 3=halfstep CW, 4=fullstep CW
        coils: dict      # Arrays to specify HIGH pulses sent to coils.

    @dataclass
    class Machine:
        stepper: List[StepperMotor]
        delay: float    

    m1 = StepperMotor([12, 16, 20, 21], 0, 0, [0,0,0,0,0], {"Harr1":[0,1], "Farr1":[0,1], "arr2":[0,1], "arr3":[0,1], "HarrOUT":[0,1], "FarrOUT":[0,1]})
    m2 = StepperMotor([19, 13, 6, 5], 0, 0, [0,0,0,0,0], {"Harr1":[0,1], "Farr1":[0,1], "arr2":[0,1], "arr3":[0,1], "HarrOUT":[0,1], "FarrOUT":[0,1]})
    
    # Setup and intialize motor parameters
    GPIO.setmode(GPIO.BCM)
    startstepping, targetstep, interval = [],[],[]
    mach = Machine([m1, m2], DEFAULTDELAY)
    for i in range(len(mach.stepper)):          # Setup each stepper motor
        mach.stepper[i].speed[2] = [0,0,0,0]
        startstepping.append(False)  # Flag for increment stepping function
        targetstep.append(291)         # Flag for increment stepping function
        interval.append(97)         # Default interval for publishing updates. Do not want too many messages sent. Only updates if 4076 % interval == 2
        for rotation in range(2):        # Setup each pin in each stepper
            mach.stepper[i].coils["Harr1"][rotation] = [0,0,1,1]
            mach.stepper[i].coils["Farr1"][rotation] = [0,0,1,1]
            mach.stepper[i].coils["arr2"][rotation] = [0,0,0,1]
            mach.stepper[i].coils["arr3"][rotation] = [0,0,1,0]
        for pin in mach.stepper[i].pins:        # Setup each pin in each stepper
            GPIO.setup(pin,GPIO.OUT)
            main_logger.info("pin {0} Setup".format(pin))

    #==== STEPPER MOTOR FUNCTIONS =====#
    def stepupdate(spd, stp):
        ''' Will update the motor step counter based on full vs half speed and CW vs CCW. Details in Stepper Class'''
        if spd == 4:
            stp += 2
        elif spd ==3:
            stp += 1
        elif spd == 1:
            stp -= 1
        elif spd == 0:
            stp -= 2
        else:
            stp = stp
        return stp

    def motors(command):   # command comes from node-red GUI
        global mach, startstepping, targetstep, interval, stepreset

        # LOOP THRU EACH STEPPER AND THE TWO ROTATIONS (CW/CCW) AND CREATE COIL ARRAY (HIGH PULSES)
        for i in range(len(mach.stepper)):   # Loop thru each stepper
            for rotation in range(2):        # Will loop thru Half and Full step and both rotations, CW and CCW
                #HALF STEP CALCULATION
                if rotation == 1:            # H is for half-step. Do array rotation (slicing) by 1 place to the right for CW
                    mach.stepper[i].coils["HarrOUT"][rotation] = mach.stepper[i].coils["Harr1"][rotation][-1:] + mach.stepper[i].coils["Harr1"][rotation][:-1]
                    mach.stepper[i].coils["Harr1"][rotation] = mach.stepper[i].coils["arr2"][rotation]
                    mach.stepper[i].coils["arr2"][rotation] = mach.stepper[i].coils["HarrOUT"][rotation]
                else:                        # Array rotation (slicing) 1 place to the left for CCW. And use arr3
                    mach.stepper[i].coils["HarrOUT"][rotation] = mach.stepper[i].coils["Harr1"][rotation][1:] + mach.stepper[i].coils["Harr1"][rotation][:1]
                    mach.stepper[i].coils["Harr1"][rotation] = mach.stepper[i].coils["arr3"][rotation]
                    mach.stepper[i].coils["arr3"][rotation] = mach.stepper[i].coils["HarrOUT"][rotation]
                #FULL STEP CALCULATION
                if rotation == 1:            # F is for full-step. Do array rotation (slicing) by 1 place to the right for CW
                    mach.stepper[i].coils["FarrOUT"][rotation] = mach.stepper[i].coils["Farr1"][rotation][-1:] + mach.stepper[i].coils["Farr1"][rotation][:-1]
                    mach.stepper[i].coils["Farr1"][rotation] = mach.stepper[i].coils["FarrOUT"][rotation]
                else:                        # Array rotation (slicing) 1 place to the left for CCW 
                    mach.stepper[i].coils["FarrOUT"][rotation] = mach.stepper[i].coils["Farr1"][rotation][1:] + mach.stepper[i].coils["Farr1"][rotation][:1]
                    mach.stepper[i].coils["Farr1"][rotation] = mach.stepper[i].coils["FarrOUT"][rotation]
            
            # Now that coil array updated set the 4 available speeds/direction. Half step CW & CCW. Full step CW & CCW.
            mach.stepper[i].speed[0] = mach.stepper[i].coils["FarrOUT"][0]
            mach.stepper[i].speed[1] = mach.stepper[i].coils["HarrOUT"][0]
            mach.stepper[i].speed[3] = mach.stepper[i].coils["HarrOUT"][1]
            mach.stepper[i].speed[4] = mach.stepper[i].coils["FarrOUT"][1]
            stepspeed = command["speed"][i]         # stepspeed is a temporary variable for this loop

            # If mode is 1 (incremental stepping) and startstep has been flagged from node-red gui then startstepping
            if command["mode"][i] == 1 and stepspeed != 2 and command["startstep"][i] == 1:
                startstepping[i] = True
                command["startstep"][i] = 0 # startstepping triggered and targetstep calculated. So turn off this if cond
                if stepspeed > 2: # moving CW 
                    if abs(mach.stepper[i].step) + command["step"][i] <= FULLREVOLUTION: # Set the target step based on node-red gui target and current step for that motor
                        targetstep[i] = abs(mach.stepper[i].step) + command["step"][i]
                    else:
                        targetstep[i] = FULLREVOLUTION
                else:      # moving CCW
                    targetstep[i] = mach.stepper[i].step - command["step"][i]
                    if targetstep[i] < (FULLREVOLUTION * -1):
                        targetstep[i] = (FULLREVOLUTION * -1)
                main_logger.debug("2:STRTSTP ON - Motor:{0} Mode:{1} startstep:{2} startstepping:{3} machStep:{4} targetstep:{5}".format(i, command["mode"][i], command["startstep"][i], startstepping[i], mach.stepper[i].step, targetstep[i]))
            
            # Mode set to 1 (incremental stepping) but haven't started stepping. Stop motor (stepspeed=2) and set the target step (based on node-red gui)
            # Will wait until startstep flag is sent from node-red GUI before starting motor
            if command["mode"][i] == 1 and not startstepping[i]:
                stepspeed = 2
                #if abs(mach.stepper[i].step) + command["step"][i] <= FULLREVOLUTION: # Set the target step based on node-red gui target and current step for that motor
                #    targetstep[i] = abs(mach.stepper[i].step) + command["step"][i]
                #else:
                #    targetstep[i] = FULLREVOLUTION      # If the target step goes past the 360° degree mark then stop at 360° mark.
                main_logger.debug("1:MODE1      - Motor:{0} Mode:{1} startstep:{2} startstepping:{3} machStep:{4} targetstep:{5}".format(i, command["mode"][i], command["startstep"][i], startstepping[i], mach.stepper[i].step, targetstep[i]))
            
            # IN INCREMENT MODE1. Keep stepping until the target step is met. Then reset the startstepping/startstep(nodered) flags.
            elif command["mode"][i] == 1 and startstepping[i]:
                main_logger.debug("3:STEPPING   - Motor:{0} Mode:{1} startstep:{2} startstepping:{3} machStep:{4} targetstep:{5}".format(i, command["mode"][i], command["startstep"][i], startstepping[i], mach.stepper[i].step, targetstep[i]))
                if abs((abs(mach.stepper[i].step) - abs(targetstep[i]))) < 2: # if delta is less than 2 then target met. Can't use 0 since full step increments by 2
                    main_logger.debug("4:DONE-M1OFF - Motor:{0} Mode:{1} startstep:{2} startstepping:{3} machStep:{4} targetstep:{5}".format(i, command["mode"][i], command["startstep"][i], startstepping[i], mach.stepper[i].step, targetstep[i]))
                    startstepping[i] = False
                    #command["startstep"][i] = 0
            
            # PUBLISH HOW MANY STEPS THE MOTOR IS AT TO NODERED GUI
            if stepspeed != 2 and interval[i] > 1 and (abs(mach.stepper[i].step) % interval[i]) == 2 : # If motor is turning and step is a approx multiple of interval (from nodered gui) then send status to node-red
                outgoingD['motori'] = i
                outgoingD['stepsi'] = mach.stepper[i].step
                mqtt_client.publish(MQTT_PUB_TOPIC1, json.dumps(outgoingD))
            elif stepspeed != 2 and command["mode"][i] == 1 and interval[i] == 1 and (abs(targetstep[i]) - abs(mach.stepper[i].step)) < 50 : # If interval is 1 only send msg update when taking small amount of steps
                outgoingD['motori'] = i
                outgoingD['stepsi'] = mach.stepper[i].step
                mqtt_client.publish(MQTT_PUB_TOPIC1, json.dumps(outgoingD))

            # SEND COIL ARRAY (HIGH PULSES) TO GPIO PINS AND UPDATE STEP COUNTER
            if i == 0:
                j = 1
            GPIO.output(mach.stepper[i].pins, mach.stepper[i].speed[stepspeed]) # output the coil array (speed/direction) to the GPIO pins.
            mach.stepper[i].step = stepupdate(stepspeed, mach.stepper[i].step)  # update the motor step based on direction and half vs full step
            # IF FULL REVOLUTION - reset the step counter
            if (abs(mach.stepper[i].step) > FULLREVOLUTION) or stepreset:  # If hit full revolution reset the step counter. If want to step past full revolution would need to later add a 'not startstepping'
                main_logger.debug("FULL REVOLUTION -- Motor:{0} Steps:{1} Mode:{2} startstepping:{3} coils:{4}".format(i, mach.stepper[i].step, command["mode"][i], startstepping[i], mach.stepper[i].speed[command["speed"][i]]))
                mach.stepper[i].step = 0
                if stepreset:
                    for j in range(len(mach.stepper)): 
                        mach.stepper[j].step = 0
                    mqtt_client.publish(MQTT_PUB_TOPIC2, "reset")
                    stepreset = False
        sleep(float(command["delay"])/1000)  # delay can be updated from node-red gui. Needs optimal setting for the motors.

        

    #==== MAIN LOOP ====================#
    # Start/bind mqtt functions
    #Create a couple flags to handle a failed attempt at connecting. If user/password is wrong we want to stop the loop.
    mqtt.Client.connected = False          # Flag for initial connection (different than mqtt.Client.is_connected)
    mqtt.Client.failed_connection = False  # Flag for failed initial connection
    #Bind/link to our callback functions
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD) # Need user/password to connect to broker
    mqtt_client.on_connect = on_connect        # Bind on connect
    mqtt_client.on_disconnect = on_disconnect  # Bind on disconnect    
    mqtt_client.on_message = on_message        # Bind on message
    mqtt_client.on_publish = on_publish        # Bind on publish
    print("Connecting to: {0}".format(MQTT_SERVER))
    mqtt_client.connect(MQTT_SERVER, 1883) # Connect to mqtt broker. This is a blocking function. Script will stop while connecting.
    mqtt_client.loop_start()               # Start monitoring loop as asynchronous. Starts a new thread and will process incoming/outgoing messages.
    # Monitor if we're in process of connecting or if the connection failed
    while not mqtt_client.connected and not mqtt_client.failed_connection:
        print("Waiting")
        sleep(1)
    if mqtt_client.failed_connection:      # If connection failed then stop the loop and main program. Use the rc code to trouble shoot
        mqtt_client.loop_stop()
        sys.exit()
    
    # MQTT setup is successful. Initialize dictionaries and start the main loop.    
    try:
        while True:
            motors(incomingD) # Pass instructions for stepper motor from node-red gui via mqtt
    except KeyboardInterrupt:
        main_logger.info("Pressed ctrl-C")
    finally:
        GPIO.cleanup()
        main_logger.info("GPIO cleaned up")   
