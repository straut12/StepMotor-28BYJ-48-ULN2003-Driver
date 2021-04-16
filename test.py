from dataclasses import dataclass
from typing import List

@dataclass
class StepperMotor:
    pins: list
    mode: int
    step: int
    speed: int
    coils: dict

@dataclass
class Machine:
    stepper: List[StepperMotor]
    delay: float

m1 = StepperMotor([14, 15, 18, 23], 0, 508, 2, {"Harr1":[0,1], "Farr1":[0,1], "arr2":[0,1], "HarrOUT":[0,1], "FarrOUT":[0,1]})
m2 = StepperMotor([19, 13, 6, 5], 0, 508, 2, {"Harr1":[0,1], "Farr1":[0,1], "arr2":[0,1], "HarrOUT":[0,1], "FarrOUT":[0,1]})

#m1 = StepperMotor([14, 15, 18, 23], 0, 508, 2, [0,1], [0,1], [0,1], [0,1], [0,1])
#m2 = StepperMotor([19, 13, 6, 5], 0, 508, 2, [0,1], [0,1], [0,1], [0,1], [0,1])

mach = Machine([m1, m2], 0.0015)

mach.stepper[0].speed = 0
#print(mach.stepper[0].coils["Harr1"][0])

outgoing = ["False",[]]
for i in range(len(mach.stepper)):
    outgoing[1].append(i)
for i in range(len(mach.stepper)):
    outgoing[1][i] = 55
outgoing[0] = "True"
if not outgoing[0]:
    print(outgoing[0])
