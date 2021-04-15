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
motor1 = [12,16,20,21]
motor2 = [19,13,6,5]
delay=.001 # delay between each sequence step. .001 is the fast the motors would still function

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
arr1 = [0,0,1,1]

arr2 = [0,0,0,1] # for clockwise
arr3 = [0,0,1,0] # for counter clockwise

def cw():
  global arr1, arr2
  arrOUT = arr1[-1:]+arr1[:-1] # rotates array values 1 place to the right
  arr1 = arr2                  
  arr2 = arrOUT
  logging.debug(arrOUT)
  GPIO.output(motor1, arrOUT)
  #GPIO.output(motor2, arrOUT)
  sleep(delay)

def ccw():
  global arr1, arr3
  arrOUT = arr1[1:]+arr1[:1] # rotates array values 1 place to the left for reverse. 
  arr1 = arr3
  arr3 = arrOUT 
  logging.debug(arrOUT)
  GPIO.output(motor1, arrOUT)
  #GPIO.output(motor2, arrOUT)
  sleep(delay)

# Start main loop
try:
  logging.debug("cw")
  logging.debug(" 1  2  3  4")
  for i in range(8):
    cw()
  logging.debug("ccw")
  logging.debug(" 1  2  3  4")
  for i in range(8):
    ccw()
except KeyboardInterrupt:
  GPIO.output(motor1, (0,0,0,0))
  GPIO.output(motor2, (0,0,0,0))
  sys.exit()
finally:
  GPIO.cleanup()
  logging.info("GPIO cleaned up")
