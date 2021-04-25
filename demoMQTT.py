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
import sys, logging, json, re
from logging.handlers import RotatingFileHandler
from os import path
from pathlib import Path
import paho.mqtt.client as mqtt
from dataclasses import dataclass
from typing import List
import stepper28byj
from time import perf_counter, perf_counter_ns

if __name__ == "__main__":

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

        exp_file_handler = RotatingFileHandler('{}/exp_debug.log'.format(log_dir), maxBytes=10**6, backupCount=5) # 1MB file
        exp_file_handler.setLevel(logging.INFO)
        exp_file_handler.setFormatter(log_file_format)

        exp_errors_file_handler = RotatingFileHandler('{}/exp_error.log'.format(log_dir), maxBytes=10**6, backupCount=5)
        exp_errors_file_handler.setLevel(logging.WARNING)
        exp_errors_file_handler.setFormatter(log_file_format)

        main_logger.addHandler(console_handler)
        main_logger.addHandler(exp_file_handler)
        main_logger.addHandler(exp_errors_file_handler)
        return main_logger
    
    # Can comment/uncomment to switch between the two methods of logging
    #basicConfig root logger
    #logging.basicConfig(level=logging.INFO)                      # Can comment/uncomment to switch
    #logging.info("Setup with basicConfig root logger")

    # getLogger (includes file logging)
    logging = setup_logging(path.dirname(path.abspath(__file__)))  # Can comment/uncomment to switch
    logging.info("Setup with getLogger console/file logging module") 
    
    #====   SETUP MQTT =================#
    # Get login info and setup subscribe/publish topics (receiving/sending messages)
    # Initialize incoming/outgoing dictionaries for receiving/sending (on_message and publish)
    # Create mqtt_client object
    # Define callback functions

    home = str(Path.home())                       # Import mqtt and wifi info. Remove if hard coding in python script
    with open(path.join(home, "stem"),"r") as f:
        user_info = f.read().splitlines()

    MQTT_SERVER = '10.0.0.115'                    # Replace with IP address of device running mqtt server/broker
    MQTT_USER = user_info[0]                      # Replace with your mqtt user ID
    MQTT_PASSWORD = user_info[1]                  # Replace with your mqtt password

    MQTT_CLIENT_ID = 'RPi4Uncom'
    #MQTT_CLIENT_ID = 'RPi3AP'

    MQTT_SUB_TOPIC = []          # + is wildcard for that level
    MQTT_SUB_TOPIC.append('nred2pi/stepperZCMD/+')
    #MQTT_SUB_TOPIC.append('nred2pi/servoZCMD/+')
    MQTT_REGEX = r'nred2pi/([^/]+)/([^/]+)'
    
    MQTT_PUB_TOPIC = 'pi2nred/stepper/'
    MQTT_PUB_TOPIC1 = MQTT_PUB_TOPIC + MQTT_CLIENT_ID
    MQTT_PUB_TOPIC2 = 'pi2nred/nredZCMD/resetstepgauge'

    # Initialize on_message array/variables. From here on will be updated by node-red gui thru user input. Main controller for stepper motors.
    mqtt_stepreset = False   # used to reset steps thru nodered gui
    outgoingD = {}          # container for decoding mqtt json payload
    mqtt_controlsD = {"delay":[0.8,1.0], "speed":[2,2], "mode":[0,0], "inverse":[False,True], "step":[2038, 2038], "startstep":[0,0]}
    incomingID = ["entire msg", "lvl2", "lvl3", "datatype"]  # break mqtt topic into levels: lvl1/lvl2/lvl3
    
    #==== HARDWARE SETUP ===============# 
    
    m1pins = [12, 16, 20, 21]
    m2pins = [19, 13, 6, 5]
    motor = stepper28byj.Stepper(m1pins, m2pins)  # can enter 1 to 2 list of pins (up to 2 motors)
    
    mqtt_client = mqtt.Client(MQTT_CLIENT_ID) # Create mqtt_client object
    
    def on_connect(client, userdata, flags, rc):
        """ on connect callback verifies a connection established and subscribe to TOPICs"""
        logging.info("attempting on_connect")
        if rc==0:
            mqtt_client.connected = True
            for topic in MQTT_SUB_TOPIC:
                client.subscribe(topic)
                logging.info("Subscribed to: {0}\n".format(topic))
            logging.info("Successful Connection: {0}".format(str(rc)))
        else:
            mqtt_client.failed_connection = True  # If rc != 0 then failed to connect. Set flag to stop mqtt loop
            logging.info("Unsuccessful Connection - Code {0}".format(str(rc)))

    def on_message(client, userdata, msg):
        """on message callback will receive messages from the server/broker. Must be subscribed to the topic in on_connect"""
        global mqtt_controlsD, mqtt_stepreset
        logging.debug("Received: {0} with payload: {1}".format(msg.topic, str(msg.payload)))
        msgmatch = re.match(MQTT_REGEX, msg.topic)   # Check for match to subscribed topics
        if msgmatch:
            incomingD = json.loads(str(msg.payload.decode("utf-8", "ignore"))) 
            incomingID = [msgmatch.group(0), msgmatch.group(1), msgmatch.group(2), type(incomingD)] # breaks msg topic into groups - group/group1/group2
            if incomingID[2] == 'controls':
                mqtt_controlsD = incomingD
            elif incomingID[2] == 'stepreset':
                mqtt_stepreset = incomingD
        # Debugging. Will print the JSON incoming payload and unpack it
        #logging.debug("Topic grp0:{0} grp1:{1} grp2:{2}".format(msgmatch.group(0), msgmatch.group(1), msgmatch.group(2)))
        #incomingD = json.loads(str(msg.payload.decode("utf-8", "ignore")))
        #logging.debug("Payload type:{0}".format(type(incomingD)))
        #if isinstance(incomingD, (str, bool, int, float)):
        #    logging.debug(incomingD)
        #elif isinstance(incomingD, list):
        #    for item in incomingD:
        #        logging.debug(item)
        #elif isinstance(incomingD, dict):
        #    for key, value in incomingD.items():  
        #        logging.debug("{0}:{1}".format(key, value))

    def on_publish(client, userdata, mid):
        """on publish will send data to broker"""
        #Debugging. Will unpack the dictionary and then the converted JSON payload
        #logging.debug("msg ID: " + str(mid)) 
        #logging.debug("Publish: Unpack outgoing dictionary (Will convert dictionary->JSON)")
        #for key, value in outgoingD.items():
        #    logging.debug("{0}:{1}".format(key, value))
        #logging.debug("Converted msg published on topic: {0} with JSON payload: {1}\n".format(MQTT_PUB_TOPIC1, json.dumps(outgoingD))) # Uncomment for debugging. Will print the JSON incoming msg
        pass 

    def on_disconnect(client, userdata,rc=0):
        logging.debug("DisConnected result code "+str(rc))
        mqtt_client.loop_stop()
    
    #==== MAIN LOOP ====================#
    # Start/bind mqtt functions
    # Create a couple flags to handle a failed attempt at connecting. If user/password is wrong we want to stop the loop.
    mqtt.Client.connected = False          # Flag for initial connection (different than mqtt.Client.is_connected)
    mqtt.Client.failed_connection = False  # Flag for failed initial connection
    # Bind/link to our callback functions
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
    t0_sec = perf_counter() # sec Counter for getting stepper data. Future feature - update interval in  node-red dashboard to link to perf_counter
    msginterval = 0.1       # Adjust interval to increase/decrease number of mqtt updates.
    t0loop_ns = perf_counter_ns() # nanosec Counter for how long it takes to run motor and get messages
    
    try:
        while True:
            motor.step(mqtt_controlsD) # Pass instructions for stepper motor for testing
            t0main_ns = perf_counter_ns() - t0loop_ns
            t0loop_ns = perf_counter_ns()
            if (perf_counter() - t0_sec) > msginterval:
                stepperdata = motor.getdata()
                if stepperdata != "na":
                    stepperdata["main_msf"] = t0main_ns/1000000
                    mqtt_client.publish(MQTT_PUB_TOPIC1, json.dumps(stepperdata))
                if mqtt_stepreset:
                    motor.resetsteps()
                    mqtt_stepreset = False
                    mqtt_client.publish(MQTT_PUB_TOPIC2, "resetstepgauge")
                t0_sec = perf_counter()
    except KeyboardInterrupt:
        logging.info("Pressed ctrl-C")
    finally:
        motor.cleanupGPIO()
        logging.info("GPIO cleaned up")
