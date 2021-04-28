import utime, ubinascii, micropython, network, re, ujson
from lib.umqttsimple import MQTTClient
from machine import Pin, PWM
from lib.uMstep28byjuln2003 import Stepper    # Import stepper module from lib.
import gc
gc.collect()
micropython.alloc_emergency_exception_buf(100)

def connect_wifi(WIFI_SSID, WIFI_PASSWORD):
    station = network.WLAN(network.STA_IF)

    station.active(True)
    station.connect(WIFI_SSID, WIFI_PASSWORD)

    while station.isconnected() == False:
        pass

    print('Connection successful')
    print(station.ifconfig())

def mqtt_setup(IPaddress):
    global MQTT_CLIENT_ID, MQTT_SERVER, MQTT_USER, MQTT_PASSWORD, MQTT_SUB_TOPIC, MQTT_REGEX
    with open("stem", "rb") as f:    # Remove and over-ride MQTT/WIFI login info below
      stem = f.read().splitlines()
    MQTT_SERVER = IPaddress   # Over ride with MQTT/WIFI info
    MQTT_USER = stem[0]         
    MQTT_PASSWORD = stem[1]
    WIFI_SSID = stem[2]
    WIFI_PASSWORD = stem[3]
    MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id())
    MQTT_SUB_TOPIC = []
    # Specific MQTT_SUB_TOPICS for ADC, servo, stepper are .appended below
    MQTT_REGEX = rb'nred2esp/([^/]+)/([^/]+)' # b'txt' is binary format. Required for umqttsimple to save memory
                                              # r'txt' is raw format for easier reg ex matching
                                              # 'nred2esp/+' would also work but would not return groups
                                              # () group capture. Useful for getting topic lvls in on_message
                                              # [^/] match a char except /. Needed to get topic lvl2, lvl3 groups
                                              # + will match one or more. Requiring at least 1 match forces a lvl1/lvl2/lvl3 topic structure
                                              # * could also be used for last group and then a lvl1/lvl2 topic would also be matched

def mqtt_connect_subscribe():
    global MQTT_CLIENT_ID, MQTT_SERVER, MQTT_SUB_TOPIC, MQTT_USER, MQTT_PASSWORD
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_SERVER, user=MQTT_USER, password=MQTT_PASSWORD)
    client.set_callback(mqtt_on_message)
    client.connect()
    print('(CONNACK) Connected to {0} MQTT broker'.format(MQTT_SERVER))
    for topics in MQTT_SUB_TOPIC:
        client.subscribe(topics)
        print('Subscribed to {0}'.format(topics)) 
    return client

def mqtt_on_message(topic, msg):
    global MQTT_REGEX
    global mqtt_controlsD, mqtt_stepreset
    msgmatch = re.match(MQTT_REGEX, topic)
    if msgmatch:
        incomingD = ujson.loads(msg.decode("utf-8", "ignore")) # decode json data
        incomingID = [msgmatch.group(0), msgmatch.group(1), msgmatch.group(2), type(incomingD)]
        if incomingID[1] == b'stepperZCMD':
            if incomingID[2] == b'controls':
                mqtt_controlsD = incomingD
            elif incomingID[2] == b'stepreset':
                mqtt_stepreset = incomingD  # Boolean to flag for resetting the steps

def mqtt_reset():
    print('Failed to connect to MQTT broker. Reconnecting...')
    utime.sleep_ms(5000)
    machine.reset()

def create_stepper(m1pins, m2pins, numbermotors):
    global MQTT_SUB_TOPIC, device, outgoingD, mqtt_controlsD, mqtt_stepreset
    MQTT_SUB_TOPIC.append(b'nred2esp/stepperZCMD/+')
    device.append(b'stepper')
    outgoingD[b'stepper'] = {}
    outgoingD[b'stepper']['data'] = {}
    outgoingD[b'stepper']['send_always'] = True
    mqtt_controlsD={"delay":[0,300], "speed":[3,3], "mode":[0,0], "inverse":[False,True], "step":[2038,2038], "startstep":[0,0]}
    mqtt_stepreset = False    # used to reset steps thru nodered gui
    for pin in m1pins:
        pinsummary.append(pin)
    if m2pins is not None:
        for pin in m2pins:
            pinsummary.append(pin)
    return Stepper(m1pins, m2pins, numbermotors, setupinfo=True)

def main():
    global pinsummary
    global mqtt_controlsD, mqtt_stepreset  # Stepper motor variables used in mqtt on_message
    global device, outgoingD                          # Containers setup in 'create' functions and used for Publishing mqtt
    
    #===== SETUP VARIABLES ============#
    # Setup mqtt variables (topics and data containers) used in on_message, main loop, and publishing
    # Further setup of variables is completed in specific 'create_device' functions
    mqtt_setup('10.0.0.115')
    device = []    # mqtt lvl2 topic category and '.appended' in create functions
    outgoingD = {} # container used for publishing mqtt data
        
    # umqttsimple requires topics to be byte format. For string.join to work on topics, all items must be the same, bytes.
    ESPID = b'/esp32A'  # Specific MQTT_PUB_TOPICS created at time of publishing using string.join (specifically lvl2.join)
    MQTT_PUB_TOPIC = [b'esp2nred/', ESPID]
  
    # Used to stagger timers for checking msgs, getting data, and publishing msgs
    on_msgtimer_delay_ms = 250
    # Period or frequency to check msgs, get data, publish msgs
    on_msg_timer_ms = 500     # Takes ~ 2ms to check for msg
    getdata_sndmsg_timer_ms = 500   # Can take > 7ms to publish msgs

    #=== SETUP DEVICES ===#
    # Boot fails if pin 12 is pulled high
    # Pins 34-39 are input only and do not have internal pull-up resistors. Good for ADC
    # Items that are sent as part of mqtt topic will be binary (b'item)
    pinsummary = []
    
    # Stepper needs delays < 1ms to run at fastest rpm
    stepper_dataON = True
    track_mainloop_time = True
    m1pins = [5,18,19,21]
    m2pins = [12,14,27,26]
    numbermotors = 2
    motor = create_stepper(m1pins, m2pins, numbermotors)

    print('Pins in use:{0}'.format(sorted(pinsummary)))
    #==========#
    # Connect and create the client
    try:
        mqtt_client = mqtt_connect_subscribe()
    except OSError as e:
        mqtt_reset()
    # MQTT setup is successful, publish status msg and flash on-board led
    mqtt_client.publish(b'status'.join(MQTT_PUB_TOPIC), b'esp32 connected, entering main loop')
    # Initialize flags and timers
    checkmsgs = False
    get_data = False
    sendmsgs = False    
    t0onmsg_ms = utime.ticks_ms()
    utime.sleep_ms(on_msgtimer_delay_ms)
    t0_datapub_ms = utime.ticks_ms()
    t0loop_us = utime.ticks_us()
    
    while True:
        try:
            if utime.ticks_diff(utime.ticks_ms(), t0onmsg_ms) > on_msg_timer_ms:
                checkmsgs = True
                t0onmsg_ms = utime.ticks_ms()
            if utime.ticks_diff(utime.ticks_ms(), t0_datapub_ms) > getdata_sndmsg_timer_ms:
                get_data = True
                sendmsgs = True
                t0_datapub_ms = utime.ticks_ms()
            
            motor.step(mqtt_controlsD)  # Main function to drive all motors. As msg come in from nodered gui will update controls.
            
            if track_mainloop_time:
                tmain_us = utime.ticks_diff(utime.ticks_us(), t0loop_us)   # Monitor how long main loop is taking
                t0loop_us = utime.ticks_us()
            
            if checkmsgs:
                mqtt_client.check_msg()
                checkmsgs = False
                
            if mqtt_stepreset:  # If step reset trigger received from node red dashboard then reset the steps and reply with command for node red to reset gauge
                motor.resetsteps()
                mqtt_stepreset = False
                tempdevice = b'nredZCMD'
                mqtt_client.publish(tempdevice.join(MQTT_PUB_TOPIC), "resetstepgauge")
                
            if get_data:
                if stepper_dataON: 
                    outgoingD[b'stepper']['data'] = motor.getdata() # Get steps, rpm, etc info to update the node red dashboard
                get_data = False

            if sendmsgs:   # Send messages for all devices setup
                if track_mainloop_time: outgoingD[b'stepper']['data']['tmain_usi'] = tmain_us
                for item in device:
                    if outgoingD[item]['send_always']:
                        mqtt_client.publish(item.join(MQTT_PUB_TOPIC), ujson.dumps(outgoingD[item]['data'])) # Send motor data (steps, rpm, etc) back to node-red dashboard
                    else:
                        if outgoingD[item]['send']:
                            mqtt_client.publish(item.join(MQTT_PUB_TOPIC), ujson.dumps(outgoingD[item]['data']))
                            outgoingD[item]['send'] = False
                sendmsgs = False
                
        except OSError as e:
            mqtt_reset()

if __name__ == "__main__":
    # Run main loop            
    main()
