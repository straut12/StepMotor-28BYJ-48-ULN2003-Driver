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
import sys, logging, json
from logging.handlers import RotatingFileHandler
from os import path
from pathlib import Path
import paho.mqtt.client as mqtt
from dataclasses import dataclass
from typing import List
import stepper28byj

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
    MQTT_PUB_TOPIC1 = 'pi/stepper/status'
    MQTT_PUB_TOPIC2 = 'pi/stepper/resetgauge'

    outgoingD = {}
    # Initialize incomingD array/variables. Actual values over-written in stepper create below. From here on will be updated by node-red gui thru user input. Main controller for stepper motors.
    incomingD = {"delay":[1.6,1.6], "speed":[3,3], "mode":[0,0], "inverse":[False,True], "step":[2038, 2038], "startstep":[0,0]}
    interval = [97,97]
    
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
    
    # Done inside Mstep28byjuln2003 mdoule
    

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
    motor = stepper28byj.Stepper()
    try:
        while True:
            motor.step(incomingD, interval) # Pass instructions for stepper motor for testing
            outgoingA = motor.getsteps()
            if outgoingA is not None:
                for i, items in enumerate(outgoingA[1]):
                    outgoingD['motori'] = i
                    outgoingD['stepsi'] = outgoingA[1][i]
                    mqtt_client.publish(MQTT_PUB_TOPIC1, json.dumps(outgoingD))
            if stepreset:
                motor.resetsteps()
                stepreset = False
                mqtt_client.publish(MQTT_PUB_TOPIC2, "reset")
    except KeyboardInterrupt:
        main_logger.info("Pressed ctrl-C")
    finally:
        motor.cleanupGPIO()
        main_logger.info("GPIO cleaned up")