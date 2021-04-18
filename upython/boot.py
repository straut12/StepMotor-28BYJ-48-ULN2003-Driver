from time import sleep
from umqttsimple import MQTTClient
import ubinascii
import machine
import micropython
import network
import esp
import re
esp.osdebug(None)
import gc
gc.collect()

if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print('woke from a deep sleep')

with open("stem", "rb") as f:
  stem = f.read().splitlines()

MQTT_SERVER = '10.0.0.115'
MQTT_USER = stem[0] 
MQTT_PASSWORD = stem[1] 
MQTT_SUB_TOPIC = []          # + is wildcard for that level
MQTT_SUB_TOPIC.append(b'nred2esp/stepperZCMD/+')
#MQTT_SUB_TOPIC.append(b'nred2esp/servoZCMD/+')
MQTT_REGEX = rb'nred2esp/([^/]+)/([^/]+)'
MQTT_PUB_TOPIC1 = b'esp2nred/stepperZDATA/motoristepsi'
MQTT_PUB_TOPIC2 = b'esp2nred/nredZCMD/resetstepgauge'
MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id())
WIFI_SSID = stem[2]
WIFI_PASSWORD = stem[3]

stepreset = False   # used to reset steps thru nodered gui


station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(WIFI_SSID, WIFI_PASSWORD)

while station.isconnected() == False:
  pass

print('Connection successful')
print(station.ifconfig())