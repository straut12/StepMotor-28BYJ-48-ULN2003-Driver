#!/usr/bin/env python3

"""
28BYJ-48 Stepper motor with ULN2003 Driver board
Motor instructions received via mqtt from a node-red server

See HARDWARE/MQTT for TOPICS

Wiring
Motor1
IN1,2,3,4 = GPIO14,15,18,23
Motor2
IN1,2,3,4 = 19,13,6,5
"""

from time import sleep
import gpiozero as gpio0
from threading import Thread
import RPi.GPIO as GPIO
import sys, logging, json
from os import path
from pathlib import Path
import paho.mqtt.client as mqtt

if __name__ == "__main__":

    def on_connect(client, userdata, flags, rc):
        """ on connect callback verifies a connection established and subscribe to TOPICs"""
        logging.info("attempting on_connect")
        if rc==0:
            mqtt_client.connected = True          # If rc = 0 then successful connection
            client.subscribe(MQTT_SUB_TOPIC1)      # Subscribe to topic
            logging.info("Successful Connection: {0}".format(str(rc)))
            logging.info("Subscribed to: {0}\n".format(MQTT_SUB_TOPIC1))
        else:
            mqtt_client.failed_connection = True  # If rc != 0 then failed to connect. Set flag to stop mqtt loop
            logging.info("Unsuccessful Connection - Code {0}".format(str(rc)))

    def on_message(client, userdata, msg):
        """on message callback will receive messages from the server/broker. Must be subscribed to the topic in on_connect"""
        global newmsg, incomingD
        if msg.topic == MQTT_SUB_TOPIC1:
            incomingD = json.loads(str(msg.payload.decode("utf-8", "ignore")))  # decode the json msg and convert to python dictionary
            newmsg = True
            # Debugging. Will print the JSON incoming payload and unpack the converted dictionary
            logging.debug("Receive: msg on subscribed topic: {0} with payload: {1}".format(msg.topic, str(msg.payload))) 
            logging.debug("Incoming msg converted (JSON->Dictionary) and unpacking")
            for key, value in incomingD.items():
                logging.debug("{0}:{1}".format(key, value))

    def on_publish(client, userdata, mid):
        """on publish will send data to broker"""
        #Debugging. Will unpack the dictionary and then the converted JSON payload
        logging.debug("msg ID: " + str(mid)) 
        logging.debug("Publish: Unpack outgoing dictionary (Will convert dictionary->JSON)")
        for key, value in outgoingD.items():
            logging.debug("{0}:{1}".format(key, value))
        logging.debug("Converted msg published on topic: {0} with JSON payload: {1}\n".format(MQTT_PUB_TOPIC1, json.dumps(outgoingD))) # Uncomment for debugging. Will print the JSON incoming msg
        pass 

    def on_disconnect(client, userdata,rc=0):
        logging.debug("DisConnected result code "+str(rc))
        mqtt_client.loop_stop()

    def get_login_info(file):
        ''' Import mqtt and wifi info. Remove if hard coding in python file '''
        home = str(Path.home())                    # Import mqtt and wifi info. Remove if hard coding in python script
        with open(path.join(home, file),"r") as f:
            user_info = f.read().splitlines()
        return user_info

    #==== LOGGING/DEBUGGING ============#
    logging.basicConfig(level=logging.DEBUG) # Set to CRITICAL to turn logging off. Set to DEBUG to get variables. Set to INFO for status messages.

    #==== HARDWARE SETUP ===============# 

    # Create list for each motor
    motor1 = [14,15,18,23]
    motor2 = [19,13,6,5]
    delay=.0015 # delay between each sequence step. .001 is the fast the motors would still function

    GPIO.setmode(GPIO.BCM)
    for pin in motor1:
        GPIO.setup(pin,GPIO.OUT)
        logging.info("Motor 1 pin {0} Setup".format(pin))

    for pin in motor2:
        GPIO.setup(pin,GPIO.OUT)
        logging.info("Motor 2 pin {0} Setup".format(pin))

    #====   SETUP MQTT =================#
    user_info = get_login_info("stem")
    MQTT_SERVER = '10.0.0.115'                    # Replace with IP address of device running mqtt server/broker
    MQTT_USER = user_info[0]                      # Replace with your mqtt user ID
    MQTT_PASSWORD = user_info[1]                  # Replace with your mqtt password
    MQTT_CLIENT_ID = 'pi4'
    MQTT_SUB_TOPIC1 = 'pi/stepper'
    MQTT_PUB_TOPIC1 = 'pi/stepper/status'

    

    #==== START/BIND MQTT FUNCTIONS ====#
    #Create a couple flags to handle a failed attempt at connecting. If user/password is wrong we want to stop the loop.
    mqtt.Client.connected = False          # Flag for initial connection (different than mqtt.Client.is_connected)
    mqtt.Client.failed_connection = False  # Flag for failed initial connection
    # Create our mqtt_client object and bind/link to our callback functions
    mqtt_client = mqtt.Client(MQTT_CLIENT_ID) # Create mqtt_client object
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
    
    #==== MAIN LOOP ====================#
    # MQTT setup is successful. Initialize dictionaries and start the main loop.

    #t1 = Thread(target=bump_watch) # run as seperate thread
    #t1.start() # start bump watch thread
    
    def motors(command):
        global speed
        global Harr1, Farr1, arr2 # enables the edit of arr1 var inside a function
        #global Harr1, Farr1, arr2 # enables the edit of arr1 var inside a function
        HarrOUT = Harr1[1:]+Harr1[:1] # rotates array values of 1 digit. Change to 3: and :3 for reverse
        Harr1 = arr2
        arr2 = HarrOUT
        FarrOUT = Farr1[1:]+Farr1[:1] # rotates array values of 1 digit. Change to 3: and :3 for reverse
        Farr1 = FarrOUT

        #HarrOUT = Harr1[1:]+Harr1[:1] # rotates array values of 1 digit. Change to 3: and :3 for reverse
        #Harr1 = arr2
        #arr2 = HarrOUT
        #FarrOUT = Farr1[1:]+Farr1[:1] # rotates array values of 1 digit. Change to 3: and :3 for reverse
        #Farr1 = FarrOUT

        #speed[0] = 
        #speed[1] = 
        speed[2] = [0,0,0,0]
        speed[3] = HarrOUT
        speed[4] = FarrOUT
        #logging.debug("Half: {0} | Full: {1}".format(HarrOUT, FarrOUT))
        GPIO.output(motor1, speed[command["m1"]])
        GPIO.output(motor2, speed[command["m2"]])
        sleep(delay)
    
    #initialize array for sequence shift
    Harr1 = [0,1,1,0]
    Farr1 = Harr1
    arr2 = [0,1,0,0]
    arrOUT = []
    speed = [[0,0,0,0] for i in range(5)]
    outgoingD, incomingD = {}, {"m1":2, "m2":2}
    newmsg = False
    try:
        while True:
            if newmsg:                                 # INCOMING: New msg/instructions have been received
                for key, value in incomingD.items():
                    motor_id = key
                    speed_status = str(value)
                    outgoingD[motor_id + 'i'] = speed_status      
                mqtt_client.publish(MQTT_PUB_TOPIC1, json.dumps(outgoingD))
                newmsg = False                         # Reset the new msg flag
            motors(incomingD)
    except KeyboardInterrupt:
        logging.info("Pressed ctrl-C")
    finally:
        GPIO.cleanup()
        logging.info("GPIO cleaned up")   
