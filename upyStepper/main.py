def on_message(topic, msg):
    global incomingID, cpuMHz, controlsD, interval, stepreset
    #print("Received topic(tag): {0}".format(topic))
    msgmatch = re.match(MQTT_REGEX, topic)
    if msgmatch:
        incomingD = ujson.loads(msg.decode("utf-8", "ignore")) # decode json data
        incomingID = [msgmatch.group(0), msgmatch.group(1), msgmatch.group(2), type(incomingD)]
        if incomingID[2] == b'controls':
            controlsD = incomingD
        elif incomingID[2] == b'interval':
            interval = incomingD
        elif incomingID[2] == b'stepreset':
            stepreset = incomingD
        #Uncomment prints for debugging. Will print the JSON incoming payload and unpack the converted dictionary
        #print("Received topic(tag): {0}".format(topic))
        #print("JSON payload: {0}".format(msg.decode("utf-8", "ignore")))
        #print("Unpacked dictionary (converted JSON>dictionary)")
        #for key, value in incomingD.items():
        #  print("{0}:{1}".format(key, value))

def connect_and_subscribe():
    global MQTT_CLIENT_ID, MQTT_SERVER, MQTT_SUB_TOPIC, MQTT_USER, MQTT_PASSWORD
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_SERVER, user=MQTT_USER, password=MQTT_PASSWORD)
    client.set_callback(on_message)
    client.connect()
    print('(CONNACK) Connected to {0} MQTT broker'.format(MQTT_SERVER))
    for topics in MQTT_SUB_TOPIC:
        client.subscribe(topics)
        print('Subscribed to {0}'.format(topics)) 
    return client

def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Reconnecting...')
    sleep(10)
    machine.reset()

try:
    mqtt_client = connect_and_subscribe()          # Connect and create the client
except OSError as e:
    restart_and_reconnect()

# MQTT setup is successful.
# Publish generic status confirmation easily seen on MQTT Explorer
# Initialize dictionaries and start the main loop.
mqtt_client.publish(b"status", b"esp32 connected, entering main loop")
led = Pin(2, Pin.OUT) #2 is the internal LED
led.value(1)
print
sleep(1)
led.value(0)  # flash led to know main loop starting

# Using polling for checking messages and getting data from stepper motor slowed the esp32 code/motors down sginificantly.
# Using staggered hardware timers to periodically check messages and get steps/rpm data from motors improved motor speed.
checkmsgs = False
checkdata = False
sendmsgs = False

def checkmessages(msgtimer):
    global checkmsgs
    checkmsgs = True
    
def checkdata(datatimer):
    global checkdata
    checkdata = True

def sendmessages(pubtimer):
    global sendmsgs
    sendmsgs = True
    
msgtimer = Timer(1)
msgtimer.init(period=600, mode=Timer.PERIODIC, callback=checkmessages)
sleep_ms(200)
datatimer = Timer(2)
datatimer.init(period=600, mode=Timer.PERIODIC, callback=checkdata)
sleep_ms(200)
pubtimer = Timer(3)
pubtimer.init(period=600, mode=Timer.PERIODIC, callback=sendmessages)

t0loop_us = utime.ticks_us()
#==== MAIN LOOP ========#
while True:
    try:
        motor.step(controlsD, interval)  # Main function to drive motors. As msg come in from nodered gui will update controls and mode1 increment interval.
        t0main_us = utime.ticks_diff(utime.ticks_us(), t0loop_us)
        t0loop_us = utime.ticks_us() 
        if checkmsgs:
            #print("check messages")
            mqtt_client.check_msg()
            if stepreset:  # If step reset trigger received from node red dashboard then reset the steps and reply with command for node red to reset gauge
                      motor.resetsteps()
                      stepreset = False
                      mqtt_client.publish(MQTT_PUB_TOPIC2, "resetstepgauge")
            checkmsgs = False       
        if checkdata:
            stepdata, rpm, looptime, cpufreq , speed, delay = motor.getdata() # Get steps, rpm, etc info to update the node red dashboard
            for i in range(numbermotors):
                outgoingD['motor' + str(i) + 'i'] = i  # The 'i' added to the end tells nodered it is an integer.
                outgoingD['steps' + str(i) + 'i'] = stepdata[i]
                outgoingD['rpm' + str(i) + 'f'] = rpm[i]
                outgoingD['looptime' + str(i) + 'f'] = looptime[i]
                outgoingD['cpufreqi'] = cpufreq
                outgoingD['speed' + str(i) + 'i'] = speed[i]
                outgoingD['delayf'] = delay
                outgoingD['main_msf'] = t0main_us / 1000
            checkdata = False
        if sendmsgs:
            mqtt_client.publish(MQTT_PUB_TOPIC1, ujson.dumps(outgoingD)) # Send motor data (steps, rpm, etc) back to node-red dashboard
            sendmsgs = False
    except OSError as e:
        restart_and_reconnect()