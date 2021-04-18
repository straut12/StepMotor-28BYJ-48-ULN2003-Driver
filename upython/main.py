from machine import Pin
import ujson
from uMstep28byjuln2003 import Stepper


def on_message(topic, msg):
    #print("sub cd function %s %s %s" % (topic, msg, MQTT_SUB_TOPIC1))
    global incomingID, controlsD, interval, stepreset #newmsg, incomingD, incomingID
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
        #newmsg = True
        #print("incoming ID:{0} data:{1}".format(incomingID, incomingD ))
  
  #if topic == MQTT_SUB_TOPIC[0]:
  #  incomingD = ujson.loads(msg.decode("utf-8", "ignore")) # decode json data to dictionary
  #if topic == MQTT_SUB_TOPIC[1]:
  #  interval = ujson.loads(msg.decode("utf-8", "ignore")) 
  #if topic == MQTT_SUB_TOPIC[2]:
  #  stepreset = ujson.loads(msg.decode("utf-8", "ignore")) 
    #newmsg = True
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

#outgoingD = {}
#incomingD = {}
#incomingID = ["msgID", "dataType"]
#newmsg = False

#==== HARDWARE SETUP ====#
m1pins = [5,18,19,21]
m2pins = [27,14,12,13]
numbermotors = 2
motor = Stepper(m1pins, m2pins, numbermotors)

#==== MQTT on_message SETUP ====#
# Initialize global variables
# controlsD, interval, stepresetare are updated in mqtt on_message
interval = [97,97]
controlsD={"delay":[1,1], "speed":[3,3], "mode":[0,0], "inverse":[False,False], "step":[2038,2038], "startstep":[0,0]}
stepreset = False
incomingID = ["entire msg", "lvl2", "lvl3", "datatype"]
outgoingD = {'motor0i':0, 'motor1i':0}  # need both motors initialized for nodered function

while True:
    try:
        mqtt_client.check_msg()           
        motor.step(controlsD, interval)
        stepdata = motor.getsteps()
        if stepdata is not None:
              for i in range(numbermotors):
                  outgoingD['steps' + str(i) + 'i'] = stepdata[1][i]
                  outgoingD['motor' + str(i) + 'i'] = i
              mqtt_client.publish(MQTT_PUB_TOPIC1, ujson.dumps(outgoingD))
        if stepreset:
              motor.resetsteps()
              stepreset = False
              mqtt_client.publish(MQTT_PUB_TOPIC2, "resetstepgauge")
        #if newmsg:                              # INCOMING: New msg/instructions received        
        #  for key, value in incomingD.items():
        #      direction = key
        #      duty = int(value)
        #      mqtt_client.publish(MQTT_PUB_TOPIC1, ujson.dumps(outgoingD))
        #  newmsg = False
    except OSError as e:
        restart_and_reconnect()