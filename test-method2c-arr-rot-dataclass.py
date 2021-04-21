from dataclasses import dataclass
from typing import List
import logging
from time import sleep
import RPi.GPIO as GPIO

@dataclass
class StepperMotor:
    pins: list  # GPIO pins
    step: int   # Keep track of steps
    speed: list  #  0=fullstepCCW, 1=halfstepCCW, 2=stop, 3=halfstep CW, 4=fullstep CW
    coils: dict # Array of pulses to keep track of array rotation. H-half, F-full. Two arrays [CW, CCW]

@dataclass
class Machine:
    stepper: List[StepperMotor]

# Create stepper motor object
m1 = StepperMotor([12, 16, 20, 21], 0, [0,0,0,0,0], {"Harr1":[0,1], "Farr1":[0,1], "arr2":[0,1], "arr3":[0,1], "HarrOUT":[0,1], "FarrOUT":[0,1]})

# Create machine object that can hold a list of stepper motors
mach = Machine([m1])

logging.basicConfig(level=logging.DEBUG) # Set to CRITICAL to turn logging off. Set to DEBUG to get variables. Set to INFO for status messages.
logging.info("GPIO version: {0}".format(GPIO.VERSION))

# Setup starting array and pins
GPIO.setmode(GPIO.BCM)
for i in range(len(mach.stepper)):          # Setup each stepper motor
    mach.stepper[i].speed[2] = [0,0,0,0]    # Speed 2 is hard coded as stop
    for rotation in range(2):                                # Setup starting array for each rotation (CW,CCW) and H-half/F-full step
        mach.stepper[i].coils["Harr1"][rotation] = [0,0,1,1]
        mach.stepper[i].coils["Farr1"][rotation] = [0,0,1,1]
        mach.stepper[i].coils["arr2"][rotation] = [0,0,0,1]  # place holder for CW array rotation later
        mach.stepper[i].coils["arr3"][rotation] = [0,0,1,0]  # place holder for CCW array rotation later
    for pin in mach.stepper[i].pins:                         # Setup each pin in each stepper
        GPIO.setup(pin,GPIO.OUT)
        logging.info("pin {0} Setup".format(pin))

delay = 0.0015
step_speed_list = [4,3,2,1,0] # Dummy list; 0=fullstepCCW, 1=halfstepCCW, 2=stop, 3=halfstep CW, 4=fullstep CW
step_speed_label = [' FullstepCW', ' HalfstepCW', '       STOP', 'HalfstepCCW', 'FullstepCCW']
for k, stepspeed in enumerate(step_speed_list): # Test the possible iterations of speed
    # For debugging change stepamount to 4 and 8 respectively to confirm sequence
    stepamount = 40 if stepspeed % 2 == 0 else 80 # Do 4 steps if stepspeed is even (full step), 0 and 4, else do full 8 steps for half-step seq
    for i in range(len(mach.stepper)):          # Test each stepper motor
        for j in range(stepamount):
            rotation = 1 if stepspeed > 2 else 0  # speed > 2 is CCW
            if stepspeed == 3 or stepspeed == 1:  # Half step calculation
                if rotation == 1:            # H is for half-step. Do array rotation (slicing) by 1 place to the right for CW
                    mach.stepper[i].coils["HarrOUT"][rotation] = mach.stepper[i].coils["Harr1"][rotation][-1:] + mach.stepper[i].coils["Harr1"][rotation][:-1]
                    mach.stepper[i].coils["Harr1"][rotation] = mach.stepper[i].coils["arr2"][rotation]
                    mach.stepper[i].coils["arr2"][rotation] = mach.stepper[i].coils["HarrOUT"][rotation]
                else:                        # Array rotation (slicing) 1 place to the left for CCW. And use arr3
                    mach.stepper[i].coils["HarrOUT"][rotation] = mach.stepper[i].coils["Harr1"][rotation][1:] + mach.stepper[i].coils["Harr1"][rotation][:1]
                    mach.stepper[i].coils["Harr1"][rotation] = mach.stepper[i].coils["arr3"][rotation]
                    mach.stepper[i].coils["arr3"][rotation] = mach.stepper[i].coils["HarrOUT"][rotation]
            if stepspeed == 4 or stepspeed == 0:  # Full step calculation          
                if rotation == 1:            # F is for full-step. Do array rotation (slicing) by 1 place to the right for CW
                    mach.stepper[i].coils["FarrOUT"][rotation] = mach.stepper[i].coils["Farr1"][rotation][-1:] + mach.stepper[i].coils["Farr1"][rotation][:-1]
                    mach.stepper[i].coils["Farr1"][rotation] = mach.stepper[i].coils["FarrOUT"][rotation]
                else:                        # Array rotation (slicing) 1 place to the left for CCW 
                    mach.stepper[i].coils["FarrOUT"][rotation] = mach.stepper[i].coils["Farr1"][rotation][1:] + mach.stepper[i].coils["Farr1"][rotation][:1]
                    mach.stepper[i].coils["Farr1"][rotation] = mach.stepper[i].coils["FarrOUT"][rotation]
                
            # Now that coil array updated set the 4 available speeds/direction. Half step CW & CCW. Full step CW & CCW. 
            mach.stepper[i].speed[0] = mach.stepper[i].coils["FarrOUT"][0]
            mach.stepper[i].speed[1] = mach.stepper[i].coils["HarrOUT"][0]
            mach.stepper[i].speed[2] = [0,0,0,0]
            mach.stepper[i].speed[3] = mach.stepper[i].coils["HarrOUT"][1]
            mach.stepper[i].speed[4] = mach.stepper[i].coils["FarrOUT"][1]

            logging.debug("{0} Pulses:{1}".format(step_speed_label[k], mach.stepper[i].speed[stepspeed]))
            GPIO.output(mach.stepper[i].pins, mach.stepper[i].speed[stepspeed])
            sleep(delay)
    logging.debug("\n")