from dataclasses import dataclass
from typing import List

@dataclass
class StepperMotor:
    pins: list  # GPIO pins
    step: int   # Keep track of steps
    speed: int  # Speed: full vs half step and CW vs CCW.
    coils: dict # Array of pulses to keep track of array rotation. H-half, F-full. Two arrays [CW, CCW]

# speed
# 4 - Full step CW
# 3 - Half step CW
# 2 - STOP [0,0,0,0]
# 1 - Half step CCW
# 0 - Full step CCW
@dataclass
class Machine:
    stepper: List[StepperMotor]

m1 = StepperMotor([12, 16, 20, 21], 0, 2, {"Harr1":[0,1], "Farr1":[0,1], "arr2":[0,1], "HarrOUT":[0,1], "FarrOUT":[0,1]})

mach = Machine([m1])

for i in range(len(self.mach.stepper)):          # Setup each stepper motor
    self.mach.stepper[i].speed[2] = [0,0,0,0]    # Speed 2 is hard coded as stop
    for rotation in range(2):                                     # Setup starting array for each rotation (CW,CCW) and H-half/F-full step
        self.mach.stepper[i].coils["Harr1"][rotation] = [0,0,1,1]
        self.mach.stepper[i].coils["Farr1"][rotation] = [0,0,1,1]
        self.mach.stepper[i].coils["arr2"][rotation] = [0,0,0,1]  # place holder for CW array rotation later
        self.mach.stepper[i].coils["arr3"][rotation] = [0,0,1,0]  # place holder for CCW array rotation later
    for pin in self.mach.stepper[i].pins:                         # Setup each pin in each stepper
        #GPIO.setup(pin,GPIO.OUT)                                 # Uncomment to setup GPIOs
        self.main_logger.info("pin {0} Setup".format(pin))
