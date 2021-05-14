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

class pcolor:
    ''' Add color to print statements '''
    LBLUE = '\33[36m'   # Close to CYAN
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    DBLUE = '\33[34m'
    WOLB = '\33[46m'    # White On LightBlue
    LPURPLE = '\033[95m'
    PURPLE = '\33[35m'
    WOP = '\33[45m'     # White On Purple
    GREEN = '\033[92m'
    DGREEN = '\33[32m'
    WOG = '\33[42m'     # White On Green
    YELLOW = '\033[93m'
    YELLOW2 = '\33[33m'
    RED = '\033[91m'
    DRED = '\33[31m'
    WOR = '\33[41m'     # White On Red
    BOW = '\33[7m'      # Black On White
    BOLD = '\033[1m'
    ENDC = '\033[0m'

class CustomFormatter(logging.Formatter):
    """ Custom logging format with color """

    grey = "\x1b[38;21m"
    green = "\x1b[32m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "[%(levelname)s]: %(name)s - %(message)s"

    FORMATS = {
        logging.DEBUG: green + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logging(log_dir, logger_type, logger_name=__name__, log_level=logging.INFO, mode=1):
    ''' Create basic or custom loggers with RotatingFileHandler '''
    global _loggers
    # logger_type = basic
    # logger_type = custom with log file options below
                # log_level and mode will determine output
                    #log_level, RFHmode|  logger.x() | output
                    #------------------|-------------|-----------
                    #      INFO, 1     |  info       | print
                    #      INFO, 2     |  info       | print+logfile
                    #      INFO, 3     |  info       | logfile
                    #      DEBUG,1     |  info+debug | print only
                    #      DEBUG,2     |  info+debug | print+logfile
                    #      DEBUG,3     |  info+debug | logfile

    if logger_type == 'basic':
        if len(logging.getLogger().handlers) == 0:       # Root logger does not already exist, will create it
            logging.basicConfig(level=log_level) # Create Root logger
            custom_logger = logging.getLogger(logger_name)    # Set logger to root logging
        else:
            custom_logger = logging.getLogger(logger_name)   # Root logger already exists so just linking logger to it
    else:
        if mode == 1:
            logfile_log_level = logging.CRITICAL
            console_log_level = log_level
        elif mode == 2:
            logfile_log_level = log_level
            console_log_level = log_level
        elif mode == 3:
            logfile_log_level = log_level
            console_log_level = logging.CRITICAL

        custom_logger = logging.getLogger(logger_name)
        custom_logger.propagate = False
        custom_logger.setLevel(log_level)
        log_file_format = logging.Formatter("[%(levelname)s] - %(asctime)s - %(name)s - : %(message)s in %(pathname)s:%(lineno)d")
        #log_console_format = logging.Formatter("[%(levelname)s]: %(message)s") # Using CustomFormatter Class

        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_log_level)
        console_handler.setFormatter(CustomFormatter())

        log_file_handler = RotatingFileHandler('{}/debug.log'.format(log_dir), maxBytes=10**6, backupCount=5) # 1MB file
        log_file_handler.setLevel(logfile_log_level)
        log_file_handler.setFormatter(log_file_format)

        log_errors_file_handler = RotatingFileHandler('{}/error.log'.format(log_dir), maxBytes=10**6, backupCount=5)
        log_errors_file_handler.setLevel(logging.WARNING)
        log_errors_file_handler.setFormatter(log_file_format)

        custom_logger.addHandler(console_handler)
        custom_logger.addHandler(log_file_handler)
        custom_logger.addHandler(log_errors_file_handler)
    if custom_logger not in _loggers: _loggers.append(custom_logger)
    return custom_logger

def on_connect(client, userdata, flags, rc):
    """ on connect callback verifies a connection established and subscribe to TOPICs"""
    main_logger.info("attempting on_connect")
    if rc==0:
        mqtt_client.connected = True
        for topic in MQTT_SUB_TOPIC:
            client.subscribe(topic)
            main_logger.info("Subscribed to: {0}".format(topic))
        main_logger.info("Successful Connection: {0}".format(str(rc)))
    else:
        mqtt_client.failed_connection = True  # If rc != 0 then failed to connect. Set flag to stop mqtt loop
        main_logger.info("Unsuccessful Connection - Code {0}".format(str(rc)))

def on_message(client, userdata, msg):
    """on message callback will receive messages from the server/broker. Must be subscribed to the topic in on_connect"""
    global deviceD, MQTT_REGEX
    global mqtt_controlsD, mqtt_stepreset
    mqtt_logger.debug("Received: {0} with payload: {1}".format(msg.topic, str(msg.payload)))
    msgmatch = re.match(MQTT_REGEX, msg.topic)   # Check for match to subscribed topics
    if msgmatch:
        mqtt_payload = json.loads(str(msg.payload.decode("utf-8", "ignore"))) 
        mqtt_topic = [msgmatch.group(0), msgmatch.group(1), msgmatch.group(2), type(mqtt_payload)] # breaks msg topic into groups - group/group1/group2
        # mqtt topic --> ["entire msg", "lvl2", "lvl3", "datatype"] 
        if mqtt_topic[2] == 'controls':
            mqtt_controlsD = mqtt_payload
        elif mqtt_topic[2] == 'stepreset':
            mqtt_stepreset = mqtt_payload
    # If Debugging will print the JSON incoming payload and unpack it
    if mqtt_logger.getEffectiveLevel() == 10:
        mqtt_logger.debug("Topic grp0:{0} grp1:{1} grp2:{2}".format(msgmatch.group(0), msgmatch.group(1), msgmatch.group(2)))
        mqtt_payload = json.loads(str(msg.payload.decode("utf-8", "ignore")))
        mqtt_logger.debug("Payload type:{0}".format(type(mqtt_payload)))
        if isinstance(mqtt_payload, (str, bool, int, float)):
            mqtt_logger.debug(mqtt_payload)
        elif isinstance(mqtt_payload, list):
            mqtt_logger.debug(mqtt_payload)
        elif isinstance(mqtt_payload, dict):
            for key, value in mqtt_payload.items():  
                mqtt_logger.debug("{0}:{1}".format(key, value))

def on_publish(client, userdata, mid):
    """on publish will send data to broker"""
    #mqtt_logger.debug("msg ID: " + str(mid)) 
    pass 

def on_disconnect(client, userdata,rc=0):
    main_logger.error("DisConnected result code "+str(rc))
    mqtt_client.loop_stop()

def mqtt_setup(IPaddress):
    global MQTT_SERVER, MQTT_CLIENT_ID, MQTT_USER, MQTT_PASSWORD, MQTT_SUB_TOPIC, MQTT_PUB_LVL1, MQTT_SUB_LVL1, MQTT_REGEX
    global mqtt_client
    home = str(Path.home())                       # Import mqtt and wifi info. Remove if hard coding in python script
    with open(path.join(home, "stem"),"r") as f:
        user_info = f.read().splitlines()
    MQTT_SERVER = IPaddress                    # Replace with IP address of device running mqtt server/broker
    MQTT_USER = user_info[0]                   # Replace with your mqtt user ID
    MQTT_PASSWORD = user_info[1]               # Replace with your mqtt password
    # Specific MQTT SUBSCRIBE/PUBLISH TOPICS created inside 'setup_device' function
    MQTT_SUB_TOPIC = []
    MQTT_SUB_LVL1 = 'nred2' + MQTT_CLIENT_ID
    MQTT_REGEX = MQTT_SUB_LVL1 + '/([^/]+)/([^/]+)' # 'nred2pi/+' would also work but would not return groups
                                              # () group capture. Useful for getting topic lvls in on_message
                                              # [^/] match a char except /. Needed to get topic lvl2, lvl3 groups
                                              # + will match one or more. Requiring at least 1 match forces a lvl1/lvl2/lvl3 topic structure
                                              # * could also be used for last group and then a lvl1/lvl2 topic would also be matched
    MQTT_PUB_LVL1 = 'pi2nred/'

def setup_device(device, lvl2, publvl3, data_keys):
    global printcolor, deviceD
    if deviceD.get(device) == None:
        deviceD[device] = {}
        deviceD[device]['data'] = {}
        deviceD[device]['lvl2'] = lvl2 # Sub/Pub lvl2 in topics. Does not have to be unique, can piggy-back on another device lvl2
        topic = f"{MQTT_SUB_LVL1}/{deviceD[device]['lvl2']}ZCMD/+"
        if topic not in MQTT_SUB_TOPIC:
            MQTT_SUB_TOPIC.append(topic)
            for key in data_keys:
                deviceD[device]['data'][key] = 0
        else:
            for key in data_keys:
                for item in deviceD:
                    if deviceD[item]['data'].get(key) != None:
                        main_logger.warning(f"**DUPLICATE WARNING {device} and {item} are both publishing {key} on {topic}")
                deviceD[device]['data'][key] = 0
        deviceD[device]['pubtopic'] = MQTT_PUB_LVL1 + lvl2 + '/' + publvl3
        deviceD[device]['send'] = False
        printcolor = not printcolor # change color of every other print statement
        if printcolor: 
            main_logger.info(f"{pcolor.LBLUE}{device} Subscribing to: {topic}{pcolor.ENDC}")
            main_logger.info(f"{pcolor.DBLUE}{device} Publishing  to: {deviceD[device]['pubtopic']}{pcolor.ENDC}")
            main_logger.info(f"JSON payload keys will be:{pcolor.WOLB}{*deviceD[device]['data'],}{pcolor.ENDC}")
        else:
            main_logger.info(f"{pcolor.PURPLE}{device} Subscribing to: {topic}{pcolor.ENDC}")
            main_logger.info(f"{pcolor.LPURPLE}{device} Publishing  to: {deviceD[device]['pubtopic']}{pcolor.ENDC}")
            main_logger.info(f"JSON payload keys will be:{pcolor.WOP}{*deviceD[device]['data'],}{pcolor.ENDC}")
    else:
        main_logger.error(f"Device {device} already in use. Device name should be unique")
        sys.exit(f"{pcolor.RED}Device {device} already in use. Device name should be unique{pcolor.ENDC}")

def main():
    global deviceD, printcolor      # Containers setup in 'create' functions and used for Publishing mqtt
    global MQTT_SERVER, MQTT_USER, MQTT_PASSWORD, MQTT_CLIENT_ID, mqtt_client, MQTT_PUB_LVL1
    global _loggers, main_logger, mqtt_logger
    global mqtt_controlsD, mqtt_stepreset  # Variables for stepper mqtt control

    main_logger_level= logging.DEBUG # CRITICAL=logging off. DEBUG=get variables. INFO=status messages.
    main_logger_type = 'custom'       # 'basic' or 'custom' (with option for log files)
    RFHmode = 1 # log level and RFH mode will determine output for custom loggers
                # log_level and mode will determine output
                #log_level, RFHmode|  logger.x() | output
                #------------------|-------------|-----------
                #      INFO, 1     |  info       | print
                #      INFO, 2     |  info       | print+logfile
                #      INFO, 3     |  info       | logfile
                #      DEBUG,1     |  info+debug | print only
                #      DEBUG,2     |  info+debug | print+logfile
                #      DEBUG,3     |  info+debug | logfile
    
    _loggers = [] # container to keep track of loggers created
    main_logger = setup_logging(path.dirname(path.abspath(__file__)), main_logger_type, log_level=main_logger_level, mode=RFHmode)
    mqtt_logger = setup_logging(path.dirname(path.abspath(__file__)), 'custom', 'mqtt', log_level=logging.DEBUG, mode=1)

    MQTT_CLIENT_ID = 'pi' # Can make ID unique if multiple Pi's could be running similar devices (ie servos, ADC's) 
                          # Node red will need to be linked to unique MQTT_CLIENT_ID
    mqtt_setup('10.0.0.115') # Pass IP address
    
    deviceD = {}  # Primary container for storing all devices, topics, and data
    printcolor = True

    #==== HARDWARE SETUP ===============#
    logger_stepper = setup_logging(path.dirname(path.abspath(__file__)), 'custom', 'stepper', log_level=logging.INFO, mode=1)
    device = 'stepper'
    lvl2 = 'stepper'
    publvl3 = MQTT_CLIENT_ID + ""
    data_keys = ['delayf', 'cpufreq0i', 'main_msf', 'looptime0f', 'looptime1f', 'steps0i', 'steps1i', 'rpm0f', 'rpm1f', 'speed0i', 'speed1i']
    m1pins = [12, 16, 20, 21]
    m2pins = [19, 13, 6, 5]
    mqtt_stepreset = False   # used to reset steps thru nodered gui
    mqtt_controlsD = {"delay":[0.8,1.0], "speed":[3,3], "mode":[0,0], "inverse":[False,True], "step":[2038, 2038], "startstep":[0,0]}
    setup_device(device, lvl2, publvl3, data_keys)
    deviceD[device]['pubtopic2'] = f"{MQTT_SUB_LVL1}/nredZCMD/resetstepgauge" # Extra topic used to tell node red to reset the step gauges
    deviceD[device]['data2'] = "resetstepgauge"
    motor = stepper28byj.Stepper(m1pins, m2pins, logger=logger_stepper)  # can enter 1 to 2 list of pins (up to 2 motors)

    main_logger.info("ALL DICTIONARIES")
    for device, item in deviceD.items():
        main_logger.info(device)
        if isinstance(item, dict):
            for key in item:
                main_logger.info("\t{0}:{1}".format(key, item[key]))
        else: main_logger.info("\t{0}".format(item))

    print("\n")
    for logger in _loggers:
        main_logger.info('{0} is set at level: {1}'.format(logger, logger.getEffectiveLevel()))

    #==== START/BIND MQTT FUNCTIONS ====#
    # Start/bind mqtt functions
    # Create a couple flags to handle a failed attempt at connecting. If user/password is wrong we want to stop the loop.
    mqtt.Client.connected = False          # Flag for initial connection (different than mqtt.Client.is_connected)
    mqtt.Client.failed_connection = False  # Flag for failed initial connection
    # Bind/link to our callback functions
    mqtt_client = mqtt.Client(MQTT_CLIENT_ID) # Create mqtt_client object
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD) # Need user/password to connect to broker
    mqtt_client.on_connect = on_connect        # Bind on connect
    mqtt_client.on_disconnect = on_disconnect  # Bind on disconnect    
    mqtt_client.on_message = on_message        # Bind on message
    mqtt_client.on_publish = on_publish        # Bind on publish
    main_logger.info("Connecting to: {0}".format(MQTT_SERVER))
    mqtt_client.connect(MQTT_SERVER, 1883)    # Connect to mqtt broker. This is a blocking function. Script will stop while connecting.
    mqtt_client.loop_start()                  # Start monitoring loop as asynchronous. Starts a new thread and will process incoming/outgoing messages.
    # Monitor if we're in process of connecting or if the connection failed
    while not mqtt_client.connected and not mqtt_client.failed_connection:
        main_logger.info("Waiting")
        sleep(1)
    if mqtt_client.failed_connection:         # If connection failed then stop the loop and main program. Use the rc code to trouble shoot
        mqtt_client.loop_stop()
        sys.exit(f"{pcolor.RED}Connection failed. Check rc code to trouble shoot{pcolor.ENDC}")

    # MQTT setup is successful. Initialize dictionaries and start the main loop.   
    t0_sec = perf_counter() # sec Counter for getting stepper data. Future feature - update interval in  node-red dashboard to link to perf_counter
    msginterval = 0.1       # Adjust interval to increase/decrease number of mqtt updates.
    t0loop_ns = perf_counter_ns() # nanosec Counter for how long it takes to run motor and get messages

    try:
        while True:
            t0main_ns = perf_counter_ns() - t0loop_ns
            t0loop_ns = perf_counter_ns()
            if (perf_counter() - t0_sec) > msginterval:
                deviceD['stepper']['data'] = motor.getdata()
                if deviceD['stepper']['data'] != "na":
                    deviceD['stepper']['data']["main_msf"] = t0main_ns/1000000  # Monitor the main/total loop time
                    mqtt_client.publish(deviceD['stepper']['pubtopic'], json.dumps(deviceD['stepper']['data'])) 
                if mqtt_stepreset:
                    motor.resetsteps()
                    mqtt_stepreset = False
                    mqtt_client.publish(deviceD['stepper']['pubtopic2'], json.dumps(deviceD['stepper']['data2']))
                t0_sec = perf_counter()
            
            motor_controls = mqtt_controlsD  # Get updated motor controls from mqtt. Could change this to another source
            motor.step(motor_controls) # Pass instructions for stepper motor for testing
    except KeyboardInterrupt:
        logging.info("Pressed ctrl-C")
    finally:
        motor.cleanupGPIO()
        logging.info("GPIO cleaned up")

if __name__ == "__main__":
    main()