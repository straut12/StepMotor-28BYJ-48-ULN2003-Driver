#              .';:cc;.
#            .,',;lol::c.
#            ;';lddddlclo
#            lcloxxoddodxdool:,.
#            cxdddxdodxdkOkkkkkkkd:.
#          .ldxkkOOOOkkOO000Okkxkkkkx:.
#        .lddxkkOkOOO0OOO0000Okxxxxkkkk:
#       'ooddkkkxxkO0000KK00Okxdoodxkkkko
#      .ooodxkkxxxOO000kkkO0KOxolooxkkxxkl
#      lolodxkkxxkOx,.      .lkdolodkkxxxO.
#      doloodxkkkOk           ....   .,cxO;
#      ddoodddxkkkk:         ,oxxxkOdc'..o'
#      :kdddxxxxd,  ,lolccldxxxkkOOOkkkko,
#       lOkxkkk;  :xkkkkkkkkOOO000OOkkOOk.
#        ;00Ok' 'O000OO0000000000OOOO0Od.
#         .l0l.;OOO000000OOOOOO000000x,
#            .'OKKKK00000000000000kc.
#               .:ox0KKKKKKK0kdc,.
#                      ...
#
# Author: peppe8o
# Date: Feb 24th, 2020

# Import required libraries
from time import sleep
import sys, logging
import RPi.GPIO as GPIO

logging.basicConfig(level=logging.DEBUG) # Set to CRITICAL to turn logging off. Set to DEBUG to get variables. Set to INFO for status messages.
logging.info("GPIO version: {0}".format(GPIO.VERSION))

# Create list for each motor
motor1 = [14,15,18,23]
motor2 = [19,13,6,5]
delay=.0015 # delay between each sequence step. .001 is the fast the motors would still function

# Use BCM GPIO references
# instead of physical pin numbers
GPIO.setmode(GPIO.BCM)

# Set all pins as output
for pin in motor1:
  GPIO.setup(pin,GPIO.OUT)
  logging.info("Motor 1 pin {0} Setup".format(pin))


for pin in motor2:
  GPIO.setup(pin,GPIO.OUT)
  logging.info("Motor 2 pin {0} Setup".format(pin))

#initialize array for sequence shift
Harr1 = [0,1,1,0]
Farr1 = [0,1,1,0]
arr2 = [0,1,0,0]

def ccw():
  global Harr1, Farr1 # enables the edit of arr1 var inside a function
  global arr2 # enables the edit of arr2 var inside a function
  HarrOUT = Harr1[1:]+Harr1[:1] # rotates array values of 1 digit. Change to 3: and :3 for reverse
  Harr1 = arr2
  arr2 = HarrOUT
  FarrOUT = Farr1[1:]+Farr1[:1] # rotates array values of 1 digit. Change to 3: and :3 for reverse
  Farr1 = FarrOUT
  logging.debug("Half: {0} | Full: {1}".format(HarrOUT, FarrOUT))
  GPIO.output(motor1, HarrOUT)
  GPIO.output(motor2, FarrOUT)
  sleep(delay)

def cw():
  global Harr1, Farr1 # enables the edit of arr1 var inside a function
  global arr2 # enables the edit of arr2 var inside a function
  HarrOUT = Harr1[3:]+Harr1[:3] # rotates array values of 1 digit. 
  Harr1 = arr2
  arr2 = HarrOUT
  FarrOUT = Farr1[3:]+Farr1[:3] # rotates array values of 1 digit. 
  Farr1 = FarrOUT
  logging.debug("Half: {0} | Full: {1}".format(HarrOUT, FarrOUT))
  GPIO.output(motor1, HarrOUT)
  GPIO.output(motor2, FarrOUT)
  sleep(delay)

# Start main loop
try:
  while True:
    cw()
except KeyboardInterrupt:
  GPIO.output(motor1, (0,0,0,0))
  GPIO.output(motor2, (0,0,0,0))
  sys.exit()
finally:
  GPIO.cleanup()
  logging.info("GPIO cleaned up")
