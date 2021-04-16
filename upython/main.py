from machine import Pin
import ujson
from uMstep28byjuln2003 import Stepper


def on_message(topic, msg):
  #print("sub cd function %s %s %s" % (topic, msg, MQTT_SUB_TOPIC1))
  global newmsg, incomingD, interval, stepreset
  if topic == MQTT_SUB_TOPIC[0]:
    incomingD = ujson.loads(msg.decode("utf-8", "ignore")) # decode json data to dictionary
  if topic == MQTT_SUB_TOPIC[1]:
    interval = ujson.loads(msg.decode("utf-8", "ignore")) 
  if topic == MQTT_SUB_TOPIC[2]:
    stepreset = ujson.loads(msg.decode("utf-8", "ignore")) 
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
  client.subscribe(MQTT_SUB_TOPIC[0])
  print('Subscribed to {0}'.format(MQTT_SUB_TOPIC[0]))
  client.subscribe(MQTT_SUB_TOPIC[1])
  print('Subscribed to {0}'.format(MQTT_SUB_TOPIC[1]))
  client.subscribe(MQTT_SUB_TOPIC[2])
  print('Subscribed to {0}'.format(MQTT_SUB_TOPIC[2]))
  print('Connected to {0} MQTT broker'.format(MQTT_SERVER))
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

outgoingD = {}
incomingD = {}
newmsg = False

interval = [97,97]
incomingD={"delay":[1,1], "speed":[3,3], "mode":[0,0], "inverse":[False,False], "step":[2038,2038], "startstep":[0,0]}
pins = [5,18,19,21]
motor = Stepper(pins)
while True:
    try:
      mqtt_client.check_msg()
      motor.step(incomingD, interval)
      outgoingA = motor.getsteps()
      if outgoingA is not None:
            outgoingD['stepsi'] = outgoingA[1]
            outgoingD['motori'] = 0
            mqtt_client.publish(MQTT_PUB_TOPIC1, ujson.dumps(outgoingD))
      if stepreset:
            motor.resetsteps()
            stepreset = False
            mqtt_client.publish(MQTT_PUB_TOPIC2, "reset")
      #if newmsg:                              # INCOMING: New msg/instructions received        
      #  for key, value in incomingD.items():
      #      direction = key
      #      duty = int(value)
      #      mqtt_client.publish(MQTT_PUB_TOPIC1, ujson.dumps(outgoingD))
      #  newmsg = False
    except OSError as e:
      restart_and_reconnect()