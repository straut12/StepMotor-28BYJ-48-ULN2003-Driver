#!/usr/bin/env python3

"""
28BYJ-48 Stepper motor with ULN2003 Driver board
Motor instructions received via mqtt from a node-red server

See HARDWARE/MQTT initialize in boot.py for Wiring and TOPICS

Wiring
Motor1
IN1,2,3,4

"""
from machine import Pin, Timer
from time import sleep_us
from time import time
import utime, ujson, uos
import math
class Stepper:   # command comes from node-red GUI
    def __init__(self, m1pin, m2pin, numbermotors=1):
        self.logconsole = False
        self.logconsoleRPM = True
        self.logfile = False
        if self.logfile:
            timer = Timer(0)
            timer.init(period=7000, mode=Timer.ONE_SHOT, callback=self._closefile)
            dataFile = "esp32timeFULL.csv"
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
        self.steppercoils = [{"Half":[0,1], "Full":[0,1], "arr2":[0,1], "arr3":[0,1], "HarrOUT":[0,1], "FarrOUT":[0,1]}, {"Half":[0,1], "Full":[0,1], "arr2":[0,1], "arr3":[0,1], "HarrOUT":[0,1], "FarrOUT":[0,1]}]
        self.FULLREVOLUTION = 4076    # Steps per revolution
        # Setup and intialize motor parameters
        self.startstepping = [False,False]  # Flag send from node red gui to start stepping in incremental mode
        self.targetstep = [291,291]         # When incremental stepping started will calculate the target step to stop at
        self.outgoing = [False, [0, 0]]  # Container for getting how many steps each motor is at. Boolean is flag if there is valid results
        self.rpmtime0 = [utime.ticks_us(), utime.ticks_us()]
        self.tloop = utime.ticks_us()
        self.rpmsteps0 = [0, 0]
        self.rpm = [0,0]
        self.seq = [0,0]
        self.closefile = False
        for i in range(self.numbermotors):
            self.stepperspeed[i][2] = [0,0,0,0]  # speed 2 is hard coded as stop
            for rotation in range(2):        # Setup each pin in each stepper
                self.steppercoils[i]["Half"][rotation] = [
                                                        [1,0,0,1],
                                                        [1,0,0,0],
                                                        [1,1,0,0],
                                                        [0,1,0,0],
                                                        [0,1,1,0],
                                                        [0,0,1,0],
                                                        [0,0,1,1],
                                                        [0,0,0,1]
                                                        ]
                self.steppercoils[i]["Full"][rotation] = [
                                                        [1,0,0,1],
                                                        [1,1,0,0],
                                                        [0,1,1,0],
                                                        [0,0,1,1]
                                                        ]

    def step(self, controls, interval):
        ''' LOOP THRU EACH STEPPER AND THE TWO ROTATIONS (CW/CCW) AND SEND COIL ARRAY (HIGH PULSES) '''
        if self.logfile: self.f.write("ENTIRE LOOP,{0}\n".format(utime.ticks_diff(utime.ticks_us(), self.tloop))) ################ 
        if self.logfile: self.tloop = utime.ticks_us() ##################
        if self.closefile:
            self._closefile()
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
                self.stepperspeed[i][stepspeed] = self.steppercoils[i]["Half"][rotation][self.seq[i]]
                self.seq[i] = self._Hsequpdate(rotation, self.seq[i])
            if stepspeed == 4 or stepspeed == 0:  # Full step calculation
                if self.seq[i] > 3:
                    self.seq[i] = 3
                self.stepperspeed[i][stepspeed] = self.steppercoils[i]["Full"][rotation][self.seq[i]]
                self.seq[i] = self._Fsequpdate(rotation, self.seq[i])
                
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
                if self.logconsole: self._printdebug(i, "2: STRTSTP ON ")

            # Mode set to 1 (incremental stepping) but haven't started stepping. Stop motor (stepspeed=2) and set the target step (based on node-red gui)
            # Will wait until startstep flag is sent from node-red GUI before starting motor
            if self.command["mode"][i] == 1 and not self.startstepping[i]:
                stepspeed = 2
                self.command["speed"][i] = 2
                if self.logconsole: self._printdebug(i, "1: MODE1      ")

            # IN INCREMENT MODE1. Keep stepping until the target step is met. Then reset the startstepping/startstep(nodered) flags.
            elif self.command["mode"][i] == 1 and self.startstepping[i]:
                if self.logconsole: self._printdebug(i, "3: STEPPING      ")
                if math.fabs((math.fabs(self.steppersteps[i]) - math.fabs(self.targetstep[i]))) < 2: # if delta is less than 2 then target met. Can't use 0 since full step increments by 2
                    if self.logconsole: self._printdebug(i, "4:DONE INCREMNT")
                    self.startstepping[i] = False

            if self.logfile: self.f.write("increment-mode-logic,{0}\n".format(utime.ticks_diff(utime.ticks_us(), t0))) #######
            if self.logfile: t0 = utime.ticks_us() ##################


            # SEND COIL ARRAY (HIGH PULSES) TO GPIO PINS AND UPDATE STEP COUNTER
            for coil in range(4):
                self.stepperpin[i][coil].value(self.stepperspeed[i][stepspeed][coil])  # output the coil array (speed/direction) to the GPIO pins.
            if self.logconsole: self._printdebug(i, "COIL INFORMTION")
            self.steppersteps[i] = self._stepupdate(stepspeed, self.steppersteps[i])  # update the motor step based on direction and half vs full step    
            
            # IF FULL REVOLUTION - reset the step counter
            if (math.fabs(self.steppersteps[i]) > self.FULLREVOLUTION):  # If hit full revolution reset the step counter. If want to step past full revolution would need to later add a 'not startstepping'
                if self.logconsole: self._printdebug(i, "FULL REVOLUTION")
                self.steppersteps[i] = 0

            if self.logfile: self.f.write("send-pulses-to-motor,{0}\n".format(utime.ticks_diff(utime.ticks_us(), t0))) ############
        
        # DELAY FOR MOTORS TO UPDATE
        if self.logfile: t0 = utime.ticks_us() ##################
        sleep_us(int(self.command["delay"][0]*1000))  # delay can be updated from node-red gui. Needs optimal setting for the motors. Currently one delay for all motors
        if self.logfile: self.f.write("sleep-for-motors,{0}\n".format(utime.ticks_diff(utime.ticks_us(), t0))) ###########
    
    def getsteps(self):
        ''' Publish how many steps the motor is at to node red for updating the step gauges in dashboard '''
        if self.logfile: t0 = utime.ticks_us() ##################
        for i in range(self.numbermotors):
            self.outgoing[0] = False
            stepspeed = self.command["speed"][i]
            if stepspeed != 2:
                self.outgoing[1][i] = self.steppersteps[i]
                self.outgoing[0] = True
                rpm = ((self.steppersteps[i]-self.rpmsteps0[i])/self.FULLREVOLUTION)/(utime.ticks_diff(utime.ticks_us(), self.rpmtime0[i])/60000000)
                if rpm > 0:
                    self.rpm[i] = rpm
                self.rpmsteps0[i] = self.steppersteps[i]
                self.rpmtime0[i] = utime.ticks_us()
            else:
                self.rpm[i] = 0
        if self.logconsoleRPM: print("m0rpm: {0} m1rpm: {1}".format(self.rpm[0], self.rpm[1]))    
        if self.logfile: self.f.write("getsteps,{0}\n".format(utime.ticks_diff(utime.ticks_us(), t0))) ###########
        if self.outgoing[0]:    
            return self.outgoing  # Only return values if one of the motors had an update

    def resetsteps(self):
        ''' Reset the step counters on all motors '''
        for i in range(self.numbermotors):
            self.steppersteps[i] = 0

    def _Hsequpdate(self, rot, seq):
        if rot == 0:
            if seq == 7:
                seq = 0
            else:
                seq += 1
        if rot == 1:
            if seq == 0:
                seq = 7
            else:
                seq -= 1
        return seq                    
                
    def _Fsequpdate(self, rot, seq):
        if rot == 0:
            if seq == 3:
                seq = 0
            else:
                seq += 1
        if rot == 1:
            if seq == 0:
                seq = 3
            else:
                seq -= 1
        return seq 
    
    def _stepupdate(self, spd, stp):
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
            
    def _closefile(self, timer):
        print("closing file and stopping motors")
        for i in range(self.numbermotors):
            for coil in range(4):
                self.stepperpin[i][coil].value(self.stepperspeed[i][2][coil]) # Stop motors
        self.f.close()
        
    def _printdebug(self, i, msg):
        print("{0}: m{1} Steps:{2} Mode:{3} strtstppng:{4} coils:{5}".format(msg, i, self.steppersteps[i], self.command["mode"], self.startstepping, self.stepperspeed[i][self.command["speed"][i]]))