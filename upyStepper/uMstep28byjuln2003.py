#!/usr/bin/env python3

"""
28BYJ-48 Stepper motor with ULN2003 Driver board
Motor instructions received via mqtt from a node-red server

See HARDWARE/MQTT initialize in boot.py for Wiring and TOPICS

Wiring
Motor1
IN1,2,3,4

"""
from machine import Pin
from time import time, sleep_us
import utime, uos
import math

class Stepper:   # command comes from node-red GUI
    def __init__(self, m1pin, m2pin, numbermotors=1):
        self.logfile = False
        if self.logfile:
            dataFile = "esp32time.csv"
            mode = "wb" if dataFile in uos.listdir() else "r+" # Create data file and write out header #
            self.f = open(dataFile, "wb")
            self.f.write("step,time\n")
        self.numbermotors = numbermotors
        if self.numbermotors == 2:
            self.stepperpin = [[Pin(m1pin[0], Pin.OUT),Pin(m1pin[1], Pin.OUT),Pin(m1pin[2], Pin.OUT),Pin(m1pin[3], Pin.OUT)]
, [Pin(m2pin[0], Pin.OUT),Pin(m2pin[1], Pin.OUT),Pin(m2pin[2], Pin.OUT),Pin(m2pin[3], Pin.OUT)]]
        elif self.numbermotors == 1:
            self.stepperpin = [[Pin(m1pin[0], Pin.OUT),Pin(m1pin[1], Pin.OUT),Pin(m1pin[2], Pin.OUT),Pin(m1pin[3], Pin.OUT)], [0]]
        self.steppersteps = [0, 0]           # Keep track of how many steps each motor has taken
        self.stepperspeed = [[0,1,2,3,4], [0,1,2,3,4]]      # Will keep track of coil pulses for each speed
        self.steppercoils = [{"Harr1":[0,1], "Farr1":[0,1], "arr2":[0,1], "arr3":[0,1], "HarrOUT":[0,1], "FarrOUT":[0,1]}, {"Harr1":[0,1], "Farr1":[0,1], "arr2":[0,1], "arr3":[0,1], "HarrOUT":[0,1], "FarrOUT":[0,1]}]
        self.FULLREVOLUTION = 4076    # Steps per revolution
        # Setup and intialize motor parameters
        self.startstepping = [False,False]  # Flag send from node red gui to start stepping in incremental mode
        self.targetstep = [291,291]         # When incremental stepping started will calculate the target step to stop at
        self.rpmtime0 = [utime.ticks_us(), utime.ticks_us()]
        self.tloop = utime.ticks_us()
        self.rpmsteps0 = [0, 0]
        self.outgoing = [False, [0, 0]]  # Container for getting how many steps each motor is at. Boolean is flag if there is valid results
        for i in range(self.numbermotors):
            self.stepperspeed[i][2] = [0,0,0,0]  # speed 2 is hard coded as stop
            for rotation in range(2):        # Setup each pin in each stepper
                self.steppercoils[i]["Harr1"][rotation] = [0,0,1,1]
                self.steppercoils[i]["Farr1"][rotation] = [0,0,1,1]
                self.steppercoils[i]["arr2"][rotation] = [0,0,0,1]
                self.steppercoils[i]["arr3"][rotation] = [0,0,1,0]

    def step(self, controls, interval):
        ''' LOOP THRU EACH STEPPER AND THE TWO ROTATIONS (CW/CCW) AND SEND COIL ARRAY (HIGH PULSES) '''
        if self.logfile: self.f.write("ENTIRE LOOP,{0}\n".format(utime.ticks_diff(utime.ticks_us(), self.tloop))) ################ 
        if self.logfile: self.tloop = utime.ticks_us() ##################
        self.command = controls
        self.interval = interval
        for i in range(self.numbermotors):
            if self.logfile: t0 = utime.ticks_us() ##################
            stepspeed = self.command["speed"][i]         # Speed from node red. stepspeed is a local variable for this loop
            if stepspeed > 2:
                if not self.command["inverse"][i]:       # Inverse flag from node red.
                    rotation = 1
                else:
                    rotation = 0
            elif stepspeed < 2:
                if not self.command["inverse"][i]:
                    rotation = 0
                else:
                    rotation = 1
                    
            if stepspeed == 3 or stepspeed == 1:  # Half step calculation
                if rotation == 1:            # H is for half-step. Do array rotation (slicing) by 1 place to the right for CW
                    self.steppercoils[i]["HarrOUT"][rotation] = self.steppercoils[i]["Harr1"][rotation][-1:] + self.steppercoils[i]["Harr1"][rotation][:-1]
                    self.steppercoils[i]["Harr1"][rotation] = self.steppercoils[i]["arr2"][rotation]
                    self.steppercoils[i]["arr2"][rotation] = self.steppercoils[i]["HarrOUT"][rotation]
                else:                        # Array rotation (slicing) 1 place to the left for CCW. And use arr3
                    self.steppercoils[i]["HarrOUT"][rotation] = self.steppercoils[i]["Harr1"][rotation][1:] + self.steppercoils[i]["Harr1"][rotation][:1]
                    self.steppercoils[i]["Harr1"][rotation] = self.steppercoils[i]["arr3"][rotation]
                    self.steppercoils[i]["arr3"][rotation] = self.steppercoils[i]["HarrOUT"][rotation]
                    
            if stepspeed == 4 or stepspeed == 0:  # Full step calculation            
                if rotation == 1:            # F is for full-step. Do array rotation (slicing) by 1 place to the right for CW
                    self.steppercoils[i]["FarrOUT"][rotation] = self.steppercoils[i]["Farr1"][rotation][-1:] + self.steppercoils[i]["Farr1"][rotation][:-1]
                    self.steppercoils[i]["Farr1"][rotation] = self.steppercoils[i]["FarrOUT"][rotation]
                else:                        # Array rotation (slicing) 1 place to the left for CCW 
                    self.steppercoils[i]["FarrOUT"][rotation] = self.steppercoils[i]["Farr1"][rotation][1:] + self.steppercoils[i]["Farr1"][rotation][:1]
                    self.steppercoils[i]["Farr1"][rotation] = self.steppercoils[i]["FarrOUT"][rotation]
            
            # Now that coil array updated set the 4 available speeds/direction. Half step CW & CCW. Full step CW & CCW.
            if not self.command["inverse"][i]: # Normal rotation pattern. speed 3/4=rot1(CW). speed 0/1=rot0 (CCW). 
                self.stepperspeed[i][0] = self.steppercoils[i]["FarrOUT"][0]
                self.stepperspeed[i][1] = self.steppercoils[i]["HarrOUT"][0]
                self.stepperspeed[i][3] = self.steppercoils[i]["HarrOUT"][1]
                self.stepperspeed[i][4] = self.steppercoils[i]["FarrOUT"][1]
            elif self.command["inverse"][i]:  # Inverse rotation pattern. speed 3/4=rot0(CCW). speed 0/1=rot1 (CW). 
                self.stepperspeed[i][0] = self.steppercoils[i]["FarrOUT"][1]
                self.stepperspeed[i][1] = self.steppercoils[i]["HarrOUT"][1]
                self.stepperspeed[i][3] = self.steppercoils[i]["HarrOUT"][0]
                self.stepperspeed[i][4] = self.steppercoils[i]["FarrOUT"][0]
            stepspeed = self.command["speed"][i]         # stepspeed is a temporary variable for this loop

            if self.logfile: self.f.write("calculate-coils,{0}\n".format(utime.ticks_diff(utime.ticks_us(), t0))) ################ 
            if self.logfile: t0 = utime.ticks_us() ##################

            # If mode is 1 (incremental stepping) and startstep has been flagged from node-red gui then startstepping
            if self.command["mode"][i] == 1 and stepspeed != 2 and self.command["startstep"][i] == 1:
                self.startstepping[i] = True
                self.command["startstep"][i] = 0 # startstepping triggered and targetstep calculated. So turn off this if cond
                if stepspeed > 2: # moving CW 
                    if math.fabs(self.steppersteps[i]) + self.command["step"][i] <= self.FULLREVOLUTION: # Set the target step based on node-red gui target and current step for that motor
                        self.targetstep[i] = math.fabs(self.steppersteps[i]) + self.command["step"][i]
                    else:
                        self.targetstep[i] = self.FULLREVOLUTION
                else:      # moving CCW
                    self.targetstep[i] = self.steppersteps[i] - self.command["step"][i]
                    if self.targetstep[i] < (self.FULLREVOLUTION * -1):
                        self.targetstep[i] = (self.FULLREVOLUTION * -1)
                #print("2:STRTSTP ON - Motor:{0} Mode:{1} startstep:{2} startstepping:{3} machStep:{4} targetstep:{5}".format(i, self.command["mode"], self.command["startstep"], self.startstepping, self.steppersteps, self.targetstep))
            
            # Mode set to 1 (incremental stepping) but haven't started stepping. Stop motor (stepspeed=2) and set the target step (based on node-red gui)
            # Will wait until startstep flag is sent from node-red GUI before starting motor
            if self.command["mode"][i] == 1 and not self.startstepping[i]:
                stepspeed = 2
                self.command["speed"][i] = 2
                #print("1:MODE1      - Motor:{0} Mode:{1} startstep:{2} startstepping:{3} machStep:{4} targetstep:{5}".format(i, self.command["mode"], self.command["startstep"], self.startstepping, self.steppersteps, self.targetstep))
            
            # IN INCREMENT MODE1. Keep stepping until the target step is met. Then reset the startstepping/startstep(nodered) flags.
            elif self.command["mode"][i] == 1 and self.startstepping[i]:
                #print("3:STEPPING   - Motor:{0} Mode:{1} startstep:{2} startstepping:{3} machStep:{4} targetstep:{5}".format(i, self.command["mode"], self.command["startstep"], self.startstepping, self.steppersteps, self.targetstep))
                if math.fabs((math.fabs(self.steppersteps[i]) - math.fabs(self.targetstep[i]))) < 2: # if delta is less than 2 then target met. Can't use 0 since full step increments by 2
                    #print("4:DONE-M1OFF - Motor:{0} Mode:{1} startstep:{2} startstepping:{3} machStep:{4} targetstep:{5}".format(i, self.command["mode"], self.command["startstep"], self.startstepping, self.steppersteps, self.targetstep))
                    self.startstepping[i] = False

            if self.logfile: self.f.write("increment-mode-logic,{0}\n".format(utime.ticks_diff(utime.ticks_us(), t0))) #######
            if self.logfile: t0 = utime.ticks_us() ##################


            # SEND COIL ARRAY (HIGH PULSES) TO GPIO PINS AND UPDATE STEP COUNTER
            for coil in range(4):
                self.stepperpin[i][coil].value(self.stepperspeed[i][stepspeed][coil])  # output the coil array (speed/direction) to the GPIO pins.
            #print("{0} {1} {2} {3}".format(self.stepperspeed[stepspeed][0],self.stepperspeed[stepspeed][1],self.stepperspeed[stepspeed][2],self.stepperspeed[stepspeed][3]))
            self.steppersteps[i] = self.stepupdate(stepspeed, self.steppersteps[i])  # update the motor step based on direction and half vs full step
            # IF FULL REVOLUTION - reset the step counter
            #print("FULL REVOLUTION -- Motor:{0} Steps:{1} Mode:{2} startstepping:{3} coils:{4}".format(i, self.steppersteps, self.command["mode"], self.startstepping, self.stepperspeed[self.command["speed"]]))
            if (math.fabs(self.steppersteps[i]) > self.FULLREVOLUTION):  # If hit full revolution reset the step counter. If want to step past full revolution would need to later add a 'not startstepping'
                #print("FULL REVOLUTION -- Motor:{0} Steps:{1} Mode:{2} startstepping:{3} coils:{4}".format(i, self.steppersteps, self.command["mode"], self.startstepping, self.stepperspeed[self.command["speed"]]))
                self.steppersteps[i] = 0

            if self.logfile: self.f.write("send-pulses-to-motor,{0}\n".format(utime.ticks_diff(utime.ticks_us(), t0))) ############
            
        #if self.logfile: t0 = utime.ticks_us() ##################
        #sleep_us(int(self.command["delay"][0]*1000))  # delay can be updated from node-red gui. Needs optimal setting for the motors. Currently one delay for all motors
        #if self.logfile: self.f.write("sleep-for-motors,{0}\n".format(utime.ticks_diff(utime.ticks_us(), t0))) ###########

    def getdata(self):
        ''' Publish how many steps the motor is at to node red for updating the step gauges in dashboard '''
        if self.logfile: t0 = utime.ticks_us() ##################
        for i in range(self.numbermotors):
            self.outgoing[0] = False
            stepspeed = self.command["speed"][i]
            if stepspeed != 2 and self.interval[i] > 1 and (math.fabs(self.steppersteps[i]) % self.interval[i]) == 2 : # If motor is turning and step is a approx multiple of interval (from nodered gui) then send status to node-red
                self.outgoing[1][i] = self.steppersteps[i]
                self.outgoing[0] = True
                rpm = ((self.steppersteps[i]-self.rpmsteps0[i])/self.FULLREVOLUTION)/(utime.ticks_diff(utime.ticks_us(), self.rpmtime0[i])/60000000)
                self.rpmsteps0[i] = self.steppersteps[i]
                self.rpmtime0[i] = utime.ticks_us()
                #if rpm > 0:
                #    print("m{0} rpm: {1}".format(i, rpm))
            elif stepspeed != 2 and self.command["mode"][i] == 1 and self.interval[i] == 1 and (math.fabs(self.targetstep[i]) - math.fabs(self.steppersteps[i])) < 50 : # If interval is 1 only send msg update when taking small amount of steps
                self.outgoing[1][i] = self.steppersteps[i]
                self.outgoing[0] = True
        if self.logfile: self.f.write("getsteps,{0}\n".format(utime.ticks_diff(utime.ticks_us(), t0))) ###########
        if self.outgoing[0]:
            return self.outgoing  # Only return values if one of the motors had an update

    def resetsteps(self):
        ''' Reset the step counters on all motors '''
        for i in range(self.numbermotors):
            self.steppersteps[i] = 0

    def stepupdate(self, spd, stp):
        ''' Will update the motor step counter based on full vs half speed and CW vs CCW. half = 1, full = 2'''
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

    def closedebugfile(self):
        self.f.close()