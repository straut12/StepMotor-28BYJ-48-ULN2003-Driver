<link rel="stylesheet" href="./images/sj4u.css"></link>

# [STEM Just 4 U Home Page](https://stemjust4u.com/)
## This project involves operating a 28BYJ-48 stepper motor with a ULN2003 driver board and RPi/esp32 

The 28BYJ-48 is a slower motor (max rpm ~15-20) but provides more precision and control compared to a regular DC motor. They are brushless, having a cogged wheel and four electromagnets. In your code you only have to send a HIGH signal to energize the coils. The electromagnet will attract the nearest teeth of the wheel driving the motor one step. However getting the correct sequence of pulses to turn the electromagnets on in a specific order is important.

Motor is controlled using mqtt via node-red dashboard.

[Link to Stepper Project Web Site](https://stemjust4u.com/steppermotor)  

![StepperMotor](images/28byjuln2003.png#200x-150y-5rad)

## Materials 
* Materials ​
* RPi
* esp32 (need to set to .24GHz)
* 28BYJ-48 stepper motor with a ULN2003 driver board
​​
### Stepper Motor Background
![StepperMotor](images/StepperMotor.gif#200sq-5rad)
[By Wapcaplet; Teravolt.The original uploader was Teravolt at English Wikipedia. - Transferred from en.wikipedia to Commons by Fastilysock using CommonsHelper., GFDL](https://commons.wikimedia.org/w/index.php?curid=10011776)

>Frame 1: The top electromagnet (1) is turned on, attracting the nearest teeth of the gear-shaped iron rotor. With the teeth aligned to electromagnet 1, they will be slightly offset from right electromagnet (2).

>Frame 2: The top electromagnet (1) is turned off, and the right electromagnet (2) is energized, pulling the teeth into alignment with it. 

>Frame 3: The bottom electromagnet (3) is energized; another rotation occurs.

>Frame 4: The left electromagnet (4) is energized, rotating again. When the top electromagnet (1) is again enabled, the rotor will have rotated by one tooth position. wiki link 

Note - the wiki diagram/description above involves energizing each electromagnet individually. The actual code below either alternates between single/dual magnets energized (half step) or energizing two magnets at once (full step).

![StepperMotor](images/stepper-pulses.png#250x-200y-5rad)
[By Misan2010 - Own work, CC BY 3.0, ](https://commons.wikimedia.org/w/index.php?curid=9787501)

## Specs

​The 28BYJ-48 is 4 coil unipolar

* 5V (use an external source for the 5V)
* Power usage - I measured 0.2A (1W) at full step and 0.21A(1.1W) at half step
* Only requires a sequence of simple on/off pulses to each coil to drive the motor (compared to a servo that requires varying duty cycle)
### ULN2003 Driver board
* Unfortunately the RPi pins can not provide the 5V/220mA+ required by the 28BYJ so a ULN2003 driver and external power source is needed. The ULN2003 has 7 Darlington transistor pairs. 4 of the 7 are used for the stepper motor setup (IN1-4). There are also 4 leds that represent the pulses. In debugging mode, if you step through the code you can see the lights mirror the array of on/off pulses sent.

Half Step mode:  
64 steps per revolution (360°/5.625°)  
Gear ratio is 63.68:1  
64*63.68 = 4076 (half steps) --> and 8 seq so 509.5 sets per revolution  

Full step mode:  
32 steps per revolution (360°/ 11.25°)  
Gear ratio is 63.68:1  
32*63.68 = 2038 (full steps)  

Full step mode will be faster but less torque than half step mode.

### Sending the pulses
- A specific sequence or order of pulses is required to create the magnetic fields which repulse or attract the magnet on the shaft causing it to rotate. You reverse that spequence to turn the motor the opposite direction.
- Frequence of the pulses determines the speed. There is an adjustable delay, sleep, in the program after sending pulses to the motor. 
- The number of pulses you send will determine how many turns of the motor. I programmed two modes. (1) a continuous mode where the motor keeps running and (2) an incremental mode where you send a specified number of pulses and then stop.

You will need an array to send the pulses to the motor/driver. I first followed [peppe8o](https://peppe8o.com/control-a-simple-stepper-motor-with-a-raspberry-pi/) suggestion of using python array rotation to implement the sequence in my code. This worked fine for the RPi4 (2GHz) but the esp32 was too slow (0.24GHz) causing too large of a delay after sending the pulse to the motor. So I ended up using array rotation for the RPi and a pre defined array sequence for the esp32.

## Two Methods to Create the Array Sequence (High Pulses)

esp32: Pre define the array sequence and then step thru it. This is the simpler method and fewer on-the-fly calculations, which helps out the lower powered esp32. It also helped to use the machine.freq() function to set the esp32 cpu to 0.24GHz (uses both cores) versus the default 0.16GHz.
When including the msqtt msg check/publish time I could not get the 

RPi: Array rotation. Define the first sequence (for both the single/dual pulse or odd/even seq) and then create the remaining sequences on the fly by shifting the values. Even at 0.24GHz, doing array rotation on the fly (along with listening for commands and publishing stepper status data vai mqtt) was too much for the esp32. The delay time between sending pulses to the motor was too long and varied too much resulting in a slow, inconsistent motor.

The 8 sequence table below is for half-step, first power coil IN4 only, then coils IN3/4 both powered, then coil IN3 only, etc.

|-|SEQ1|SEQ2|SEQ3|SEQ4|SEQ5|SEQ6|SEQ7|SEQ8|
|-|----|----|----|----|----|----|-----|--|
|IN4| 1| 1| 0| 0|0 | 0|0 | 1|
|IN3| 0| 1| 1| 1|0 | 0|0 | 0|
|IN2| 0| 0| 0| 1|1 | 1|0 | 0|
|IN1| 0| 0| 0| 0|0 | 1|1 | 1|

You can see two alternating sequences, odd and even.
Odd seq 1,3,5,7. The 1 (pulse) is shifted one place over each time.  
`1 0 0 0`  
`0 1 0 0`  
`0 0 1 0`  
`0 0 0 1`  

Even (seq 2,4,6,8). The two 1's (pulses) are shifted one place over each time.  
`1 0 0 1`  
`1 1 0 0`  
`0 1 1 0`  
`0 0 1 1`  

In full step the array is only the even sequences. Always 2 high pulses sent (two electromagnets energized).  
`Seq[0] = [1,0,0,1]`  
`Seq[1] = [1,1,0,0]`  
`Seq[2] = [0,1,1,0]`  
`Seq[3] = [0,0,1,1]`  

In half step you have both odd and even seq. Alternating 1 to 2 high pulses.  
`Seq[0] = [1,0,0,1]`  
`Seq[1] = [1,0,0,0]`  
`Seq[2] = [1,1,0,0]`  
`Seq[3] = [0,1,0,0]`  
`Seq[4] = [0,1,1,0]`  
`Seq[5] = [0,0,1,0]`  
`Seq[6] = [0,0,1,1]`  
`Seq[7] = [0,0,0,1]`  

For opposite rotation (CCW) you just step thru the arrays in reverse order.

For the RPi array rotation - slicing can be used as the method for shifting the values one place to the right or left.
CW shift the 1's one place to the right with   
`array = array[-1:]+array[:-1]`  
CCW shift the 1's one place to the left with  
`array = array[1:]+array[:1]`  

>For the RPi: To handle all the arrays (full, half, CW and CCW) for multiple stepper motors I used a dataclass. A dataclass is a simpler version of a Class. One disadvantage is that it requires python3.7+. Other options (ie namedTuple) are compared in this towardsdatascience article. 

>My setup -  One data class, StepperMotor, that holds the pin numbers, step counts, and all the sequences (coils). Then a second dataclass, Machine, that only has a list/array of the first stepper dataclass. This allowed me to get the code working for one stepper motor and then easily add more motors in the list. The code just has to loop thru the instructions for each motor in the list. I only used 2 motors but it could be scaled up to more. 

```
from dataclasses import dataclass  
from typing import List  
@dataclass  
class StepperMotor:  
    pins: list  
    mode: int  
    step: int  
    speed: list  
    coils: dict  

@dataclass  
class Machine:  
    stepper: List[StepperMotor]  
```
## Initial Test Results

In my 1/2 step testing, to get the max rpm, without stalling, the time between pulses (delay) needed to be ~0.8ms.  
* 0.8ms x 8seq = 6.4ms period.
* 1/6.4ms = 156Hz frequency
* 156Hz x 60sec/508 = 18rpm

I was able to do this with the RPi. But the esp32 was more difficult.
The esp32 mqtt receive/publish time was too large so I used 3 offset hardware timers to spread the time out.
* timer 1: check messages from mqtt broker
* timer 2: get step,rpm,etc data from stepper motor
* timer 3: send the data to mqtt broker
Each timer ran on a 600ms cycle and were offset by 200ms.  So every 200ms one of these longer checks were being performed. This smoothed out the motor significantly.
However the total loop time still hovered around 1.8ms.

RPi4 (2GHz) and esp32 (set to .24GHz)  
My results with shortest delay and not stalling the motor
* RPi4: 1/2 step 0.8ms delay  x 8seq = 6.4ms period = 156Hz = 18rpm
* RPi4: Full step 1.8ms delay x 4seq = 7.2ms period = 139Hz = 16rpm
* esp32: 1/2 step 1.8ms delay x 8seq = 14.4ms period = 71Hz = 8rpm
* esp32: Full step 1.8ms delay x 4seq = 7.2ms period = 139Hz = 16rpm

You can easily increase the delay to slow the motors down to 3-4rpm.
|Pulse from IN1|Device|
|-|-|
|![StepperMotor](images/rpi-halfstep.jpg#150x-100y-5rad)|RPi Halfstep  ~150Hz 18rpm
![StepperMotor](images/rpi-fullstep.jpg#150x-100y-5rad)|RPi Fullstep  ~140Hz 16rpm
![StepperMotor](images/esp32-halfstep.jpg#150x-100y-5rad)|esp32 Halfstep ~70Hz 8rpm

Need to do more tests to measure how much torque each condition produces.

I also included a time counter to measure the entire loop. You can see the spikes when the devices does a mqtt receive/publish. The esp32 show significantly more variation in loop time compared to the RPi. However there was nothing else running on the Pi when running the tests.

## Python vs uPython Notes

I had multiple differences between python and upython.

CPU freq was important. To get the cpu freq and display it on nodered dashboard
esp32: machine.freq() and can set it with machine.freq(240000000)
RPI: f = open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
cpufreq = int(f.read()) / 1000

To get shorter delays on upython use sleep_us --> sleep_us(int variable)

For time counters:
(can use timeit in python for code snippets)
RPi python: perf_counter_ns() gives the time in nanosec as an integer. _ns added in 3.7+
perf_counter includes sleep/delay times

esp32: utime.ticks_us() give the time in usec.
Can use utime.ticks_diff(utime.ticks_us(), prev_time) to caclulate the delta

Trying to print or write debug lines to a file made the loops run slower. Print is the slowest.  
RPi4 time to write to a file was ~0.009ms  
esp32 time to write to a file was ~0.38ms  

## Pin Connection

The stepper motor power (5V) is connected to an external power source.  
The IN1-4 connection is fairly easy. Just pick 4 GPIO pins and set to OUT (will be a digital 0/1 signal).  

Pins for my RPi setup  
`m1pins = [12, 16, 20, 21]`  
`m2pins = [19, 13, 6, 5]`  

Pins for my esp32 setup  
`m1pins = [5,18,19,21]`  
`m2pins = [27,14,12,13]`  

>General Troubleshooting - I was getting a lot of stutter on one motor. Keep spare parts for swapping out hardware. In my case swapping motors/drivers didn't fix the issue. After trying different GPIO pins it went away. I had one pin that was causing the issue. 

>Create a sandbox.py file that you use to play around with different python code. Make sure the code works how you think it should, on a small scale, before inserting into your working program.

>Logging with RotatingFileHandler. One challenge debugging the program is the 1000+  steps/lines occurring per second in the loop. It was hard to follow the sequence and find issues. Using RotatingFileHandler you can output debugging lines to a log file (also specify a memory limit where it rolls over to another log file). Each 1MB log file could capture ~5k debugging lines. There I could search for keywords I put in the debugging line and follow the code.

## Code

For my code mqtt-node-red setup is required for sending commands to the stepper motors and getting information (rpms, loop time, etc) back.

My workflow
1. Initialize an empty github repository with a README and .gitignore (python)
2. Go to RPi directory and clone  
`$ git clone git@github.com:user/repo.git` (ssh copied from github)
3. ​​Create virtual env  
`$ python3 -m venv .venv`  
`$ source .venv/bin/activate`  
4. Install packages​ (can download requirements.txt from my github)  
`(.venv)$ pip3 install -r requirements.txt`

If working with venv inside vscode make sure and select the venv Python interpreter in bottom left.

RPi has minimal requirements. Paho-mqtt for mqtt and RPi.GPIO for sending pulses.  
demoMQTT.py  (script)  
/stepper28byj  
|    |-Mstep28byjuln2003.py (stepper module)  

Code Sections in main script demoMQTT.py
1. Logging/debugging control set with level
DEBUG (variables+status prints)
INFO (status prints)
CRITICAL (prints turned off)
2. Initialize MQTT variables and define callback functions.
Used regex for subscribing and receiving messages. This allows a generic topic to be entered and less updating between projects. 
    - MQTT_SUB_TOPIC = [ ]
    - Made subscribe topic an array so future topics can be easily added with .append. Just comment out the topic not interested in for that project.
    - MQTT_SUB_TOPIC.append('nred2pi/stepperZCMD/+')
    - \+ indicates any topics starting with nred2pi/stepperZCMD/ will be subscribed to.
    - Good reference article by [hivemq](https://www.hivemq.com/blog/mqtt-essentials-part-5-mqtt-topics-best-practices/)
    - Regex topic is used for match in the on_message function
    - MQTT_REGEX = r'nred2pi/([^/]+)/([^/]+)'
    - r' indicates raw string. Do not treat backslash as escape character
    - (...) Isolates part of the full match (can be referred to by ID)
    - [^/] Matches any character except for the / since already included in the text
    - \+ matches as many as possible
    - A useful website for understanding the syntac is [regex101](www.regex101.com)

    - mqtt_controlsD is main command container sent to stepper motors via mqtt (nodered)
    - delay - the delay (ms) after sending pulses to stepper motors
speed - 0=fullstepCCW, 1=halfstepCCW, 2=stop, 3=halfstepCW, 4=fullstepCW
    - inverse - boolean flag for two motor setup. Motor1 will be inverse rotation motor 2.
    - mode - 0:continuous 1:increment mode. Use "step" to calculate distance to go, step to that distance, then stop. (note - when complete revolution is made it stops regardless)
    - step - Distance to step in mode 1
    - startstep - Flag to start stepping in mode 1.

3. MQTT setup (get server info align topics to match node-red)
SUBSCRIBE TOPIC
    - Used regex for subscribing and matching msg topics.
    - Use msgmatch.group(x) to isolate the message and assign variables.
​
​
4. Hardware Setup (set pins, create objects for external hardware)

Using BCM GPIO number for pins

Pins for my RPi setup
m1pins = [12, 16, 20, 21]  
m2pins = [19, 13, 6, 5]  

Pins for my esp32 setup  
m1pins = [5,18,19,21]  
m2pins = [27,14,12,13]  

motor = stepper28byj.Stepper(m1pins, m2pins)  
More motor lists can be passed as an argument. However I only tested with two. My node-red dashboard is only setup for 2 motors and would need to be adjusted for more.

5. Start/bind MQTT functions
    - Enter main loop
    - Receive msg/instructions (subscribed) from node-red via mqtt broker/server
    - Perform actions
    - Publish status/instructions to node-red via mqtt broker/server
Configure outgoing dictionary here


esp32  
/upyStepper/main.py and uMstep28byjuln2003 module plus boot.   (umqttsimple file does not change and is in older project githubs. I always keep this file on my esp32 unchanged)

# Node Red Charts/Flows

Node red flows are in github node red folder.

I started with a simple dashboard that set the delay (ms), speed (half vs full step) and a START/STOP. Then added gauges for setup below.

![StepperMotor](images/nodered-dashboard2.gif#500x-300y)


[Link to MQTT-Node-Red Setup](https://stemjust4u.com/mqtt-influxdb-nodered-grafana)  