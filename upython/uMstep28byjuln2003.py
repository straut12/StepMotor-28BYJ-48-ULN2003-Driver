#!/usr/bin/env python3

"""
28BYJ-48 Stepper motor with ULN2003 Driver board
Motor instructions received via mqtt from a node-red server

See HARDWARE/MQTT for Wiring and TOPICS

Wiring
Motor1
IN1,2,3,4

"""
from machine import Pin
from time import sleep

class Stepper:   # command comes from node-red GUI
    def __init__(self, pins):
        self.stepperpin = [Pin(pins[0], Pin.OUT),Pin(pins[1], Pin.OUT),Pin(pins[2], Pin.OUT),Pin(pins[3], Pin.OUT)]
        self.steppersteps = 0
        self.stepperspeed = [0,1,2,3,4]
        self.steppercoils = {"Harr1":[0,1], "Farr1":[0,1], "arr2":[0,1], "arr3":[0,1], "HarrOUT":[0,1], "FarrOUT":[0,1]}
        self.FULLREVOLUTION = 4076    # Steps per revolution
        # Setup and intialize motor parameters
        self.startstepping = []
        self.targetstep = []
        self.outgoing = [False, 0]
        self.stepperspeed[2] = [0,0,0,0]
        self.outgoing[1].append(0)
        self.startstepping.append(False)  # Flag for increment stepping function
        self.targetstep.append(291)         # Increment target step. Will be updated with nodered gui
        for rotation in range(2):        # Setup each pin in each stepper
            self.steppercoils["Harr1"][rotation] = [0,0,1,1]
            self.steppercoils["Farr1"][rotation] = [0,0,1,1]
            self.steppercoils["arr2"][rotation] = [0,0,0,1]
            self.steppercoils["arr3"][rotation] = [0,0,1,0]

    def step(self, incomingD, interval):
        ''' LOOP THRU EACH STEPPER AND THE TWO ROTATIONS (CW/CCW) AND SEND COIL ARRAY (HIGH PULSES) '''
        self.command = incomingD
        self.interval = interval

        for rotation in range(2):        # Will loop thru Half and Full step and both rotations, CW and CCW
            #HALF STEP CALCULATION
            if rotation == 1:            # H is for half-step. Do array rotation (slicing) by 1 place to the right for CW
                self.steppercoils["HarrOUT"][rotation] = self.steppercoils["Harr1"][rotation][-1:] + self.steppercoils["Harr1"][rotation][:-1]
                self.steppercoils["Harr1"][rotation] = self.steppercoils["arr2"][rotation]
                self.steppercoils["arr2"][rotation] = self.steppercoils["HarrOUT"][rotation]
            else:                        # Array rotation (slicing) 1 place to the left for CCW. And use arr3
                self.steppercoils["HarrOUT"][rotation] = self.steppercoils["Harr1"][rotation][1:] + self.steppercoils["Harr1"][rotation][:1]
                self.steppercoils["Harr1"][rotation] = self.steppercoils["arr3"][rotation]
                self.steppercoils["arr3"][rotation] = self.steppercoils["HarrOUT"][rotation]
            #FULL STEP CALCULATION
            if rotation == 1:            # F is for full-step. Do array rotation (slicing) by 1 place to the right for CW
                self.steppercoils["FarrOUT"][rotation] = self.steppercoils["Farr1"][rotation][-1:] + self.steppercoils["Farr1"][rotation][:-1]
                self.steppercoils["Farr1"][rotation] = self.steppercoils["FarrOUT"][rotation]
            else:                        # Array rotation (slicing) 1 place to the left for CCW 
                self.steppercoils["FarrOUT"][rotation] = self.steppercoils["Farr1"][rotation][1:] + self.steppercoils["Farr1"][rotation][:1]
                self.steppercoils["Farr1"][rotation] = self.steppercoils["FarrOUT"][rotation]
        
        # Now that coil array updated set the 4 available speeds/direction. Half step CW & CCW. Full step CW & CCW.
        if not self.command["inverse"]: # Normal rotation pattern. speed 3/4=rot1(CW). speed 0/1=rot0 (CCW). 
            self.stepperspeed[0] = self.steppercoils["FarrOUT"][0]
            self.stepperspeed[1] = self.steppercoils["HarrOUT"][0]
            self.stepperspeed[3] = self.steppercoils["HarrOUT"][1]
            self.stepperspeed[4] = self.steppercoils["FarrOUT"][1]
        elif self.command["inverse"]:  # Inverse rotation pattern. speed 3/4=rot0(CCW). speed 0/1=rot1 (CW). 
            self.stepperspeed[0] = self.steppercoils["FarrOUT"][1]
            self.stepperspeed[1] = self.steppercoils["HarrOUT"][1]
            self.stepperspeed[3] = self.steppercoils["HarrOUT"][0]
            self.stepperspeed[4] = self.steppercoils["FarrOUT"][0]
        stepspeed = self.command["speed"]         # stepspeed is a temporary variable for this loop

        # If mode is 1 (incremental stepping) and startstep has been flagged from node-red gui then startstepping
        if self.command["mode"] == 1 and stepspeed != 2 and self.command["startstep"] == 1:
            self.startstepping = True
            self.command["startstep"] = 0 # startstepping triggered and targetstep calculated. So turn off this if cond
            if stepspeed > 2: # moving CW 
                if abs(self.steppersteps) + self.command["step"] <= self.FULLREVOLUTION: # Set the target step based on node-red gui target and current step for that motor
                    self.targetstep = abs(self.steppersteps) + self.command["step"]
                else:
                    self.targetstep = self.FULLREVOLUTION
            else:      # moving CCW
                self.targetstep = self.steppersteps - self.command["step"]
                if self.targetstep < (self.FULLREVOLUTION * -1):
                    self.targetstep = (self.FULLREVOLUTION * -1)
            #print("2:STRTSTP ON - Motor:{0} Mode:{1} startstep:{2} startstepping:{3} machStep:{4} targetstep:{5}".format(i, self.command["mode"], self.command["startstep"], self.startstepping, self.steppersteps, self.targetstep))
        
        # Mode set to 1 (incremental stepping) but haven't started stepping. Stop motor (stepspeed=2) and set the target step (based on node-red gui)
        # Will wait until startstep flag is sent from node-red GUI before starting motor
        if self.command["mode"] == 1 and not self.startstepping:
            stepspeed = 2
            self.command["speed"] = 2
            #print("1:MODE1      - Motor:{0} Mode:{1} startstep:{2} startstepping:{3} machStep:{4} targetstep:{5}".format(i, self.command["mode"], self.command["startstep"], self.startstepping, self.steppersteps, self.targetstep))
        
        # IN INCREMENT MODE1. Keep stepping until the target step is met. Then reset the startstepping/startstep(nodered) flags.
        elif self.command["mode"] == 1 and self.startstepping:
            #print("3:STEPPING   - Motor:{0} Mode:{1} startstep:{2} startstepping:{3} machStep:{4} targetstep:{5}".format(i, self.command["mode"], self.command["startstep"], self.startstepping, self.steppersteps, self.targetstep))
            if abs((abs(self.steppersteps) - abs(self.targetstep))) < 2: # if delta is less than 2 then target met. Can't use 0 since full step increments by 2
                #print("4:DONE-M1OFF - Motor:{0} Mode:{1} startstep:{2} startstepping:{3} machStep:{4} targetstep:{5}".format(i, self.command["mode"], self.command["startstep"], self.startstepping, self.steppersteps, self.targetstep))
                self.startstepping = False


        # SEND COIL ARRAY (HIGH PULSES) TO GPIO PINS AND UPDATE STEP COUNTER
        for i, coil in enumerate(self.stepper.pins):
            self.stepperpin[coil].value(self.stepperspeed[stepspeed][i])  # output the coil array (speed/direction) to the GPIO pins.
        self.steppersteps = self.stepupdate(stepspeed, self.steppersteps)  # update the motor step based on direction and half vs full step
        # IF FULL REVOLUTION - reset the step counter
        #print("FULL REVOLUTION -- Motor:{0} Steps:{1} Mode:{2} startstepping:{3} coils:{4}".format(i, self.steppersteps, self.command["mode"], self.startstepping, self.stepperspeed[self.command["speed"]]))
        if (abs(self.steppersteps) > self.FULLREVOLUTION):  # If hit full revolution reset the step counter. If want to step past full revolution would need to later add a 'not startstepping'
            #print("FULL REVOLUTION -- Motor:{0} Steps:{1} Mode:{2} startstepping:{3} coils:{4}".format(i, self.steppersteps, self.command["mode"], self.startstepping, self.stepperspeed[self.command["speed"]]))
            self.steppersteps = 0

        sleep(float(self.command["delay"])/1000)  # delay can be updated from node-red gui. Needs optimal setting for the motors.
    
    def getsteps(self):
        ''' PUBLISH HOW MANY STEPS THE MOTOR IS AT TO NODERED GUI '''
        self.outgoing[0] = False
        stepspeed = self.command["speed"]
        if stepspeed != 2 and self.interval > 1 and (abs(self.steppersteps) % self.interval) == 2 : # If motor is turning and step is a approx multiple of interval (from nodered gui) then send status to node-red
            self.outgoing[1] = self.steppersteps
            self.outgoing[0] = True
        elif stepspeed != 2 and self.command["mode"] == 1 and self.interval == 1 and (abs(self.targetstep) - abs(self.steppersteps)) < 50 : # If interval is 1 only send msg update when taking small amount of steps
            self.outgoing[1] = self.steppersteps
            self.outgoing[0] = True
        if self.outgoing[0]:
            return self.outgoing  # Only return values if one of the motors had an update

    def resetsteps(self):
        self.steppersteps = 0

    def stepupdate(self, spd, stp):
        ''' Will update the motor step counter based on full vs half speed and CW vs CCW. Details in Stepper Class'''
        if spd == 4:
            stp += 2
        elif spd ==3:
            stp += 1
        elif spd == 1:
            stp -= 1
        elif spd == 0:
            stp -= 2
        else:
            stp = stp
        return stp