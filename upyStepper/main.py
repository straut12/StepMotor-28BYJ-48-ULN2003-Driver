def on_message(topic, msg):
    global incomingID, controlsD, interval, stepreset
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

checkmsgs = False
checkdata = False

def checkmessages(msgtimer):
    global checkmsgs
    checkmsgs = True
    
def checkdata(datatimer):
    global checkdata
    checkdata = True
    
msgtimer = Timer(1)
msgtimer.init(period=800, mode=Timer.PERIODIC, callback=checkmessages)
sleep_ms(400)
datatimer = Timer(2)
datatimer.init(period=800, mode=Timer.PERIODIC, callback=checkdata)

#==== MAIN LOOP ======#
while True:
    try:
        motor.step(controlsD, interval)  # Main function to drive motors. As msg come in from nodered gui will update controls/interval
        if checkmsgs:
            #print("check messages")
            mqtt_client.check_msg()
            if stepreset:  # If step reset trigger received from node red dashboard then reset the steps and reply with command for node red to reset gauge
                      motor.resetsteps()
                      stepreset = False
                      mqtt_client.publish(MQTT_PUB_TOPIC2, "resetstepgauge")
            checkmsgs = False       
        if checkdata:
            stepdata = motor.getsteps()      # Get an update on what step each motor is at to update the node red dashboard
            if stepdata is not None:         # Only send a step update to node red on frequency (based on status increment in node red)
                  for i in range(numbermotors):
                      outgoingD['steps' + str(i) + 'i'] = stepdata[1][i]
                      outgoingD['motor' + str(i) + 'i'] = i
                  mqtt_client.publish(MQTT_PUB_TOPIC1, ujson.dumps(outgoingD))
            checkdata = False                   
    except OSError as e:
        restart_and_reconnect()