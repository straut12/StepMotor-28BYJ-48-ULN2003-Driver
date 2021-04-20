from time import time, sleep, sleep_us, sleep_ms
from umqttsimple import MQTTClient
import ubinascii
import machine
import micropython
import network
import esp
import re
from machine import Pin, Timer
import ujson
from uMstep28byjuln2003B import Stepper
esp.osdebug(None)
import gc
gc.collect()

if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print('woke from a deep sleep')

with open("stem", "rb") as f:
  stem = f.read().splitlines()

#==== MQTT SETUP ====#
MQTT_SERVER = '10.0.0.115'
MQTT_USER = stem[0] 
MQTT_PASSWORD = stem[1] 
MQTT_SUB_TOPIC = []          # + is wildcard for that level
MQTT_SUB_TOPIC.append(b'nred2esp/stepperZCMD/+')
#MQTT_SUB_TOPIC.append(b'nred2esp/servoZCMD/+')
MQTT_REGEX = rb'nred2esp/([^/]+)/([^/]+)'
MQTT_PUB_TOPIC1 = b'esp2nred/stepperZDATA/motordata'
MQTT_PUB_TOPIC2 = b'esp2nred/nredZCMD/resetstepgauge'
MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id())
WIFI_SSID = stem[2]
WIFI_PASSWORD = stem[3]

# Initialize global variables
# cpuMHz, controlsD, interval, stepresetare are updated in mqtt on_message
cpuMHz = 240000000 # Can use 160000000 or 80000000 to drop power consumption by 10-20mA (almost 50%)
interval = [97,97]
controlsD={"delay":[0.1,0.3], "speed":[3,3], "mode":[0,0], "inverse":[False,False], "step":[2038,2038], "startstep":[0,0]}
stepreset = False    # used to reset steps thru nodered gui
incomingID = ["entire msg", "lvl2", "lvl3", "datatype"]
outgoingD = {'motor0i':0, 'motor1i':0}  # need both motors initialized for nodered function

#==== HARDWARE SETUP ====#
m1pins = [5,18,19,21]
m2pins = [27,14,12,13]
numbermotors = 2
motor = Stepper(m1pins, m2pins, numbermotors, cpuMHz)

#==== CONNECT MQTT ====#
station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(WIFI_SSID, WIFI_PASSWORD)

while station.isconnected() == False:
  pass

print('Connection successful')
print(station.ifconfig())