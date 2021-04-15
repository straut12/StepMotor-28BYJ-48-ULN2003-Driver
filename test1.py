import RPi.GPIO as GPIO
import time, logging, sys

logging.basicConfig(level=logging.DEBUG) # Set to CRITICAL to turn logging off. Set to DEBUG to get variables. Set to INFO for status messages.
logging.info("GPIO version: {0}".format(GPIO.VERSION))

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
M1in1 = 12
M1in2 = 16
M1in3 = 20
M1in4 = 21

M2in1 = 19
M2in2 = 13
M2in3 = 6
M2in4 = 5

StepCount = 8

if StepCount == 4:  # Full step
    delay = 0.0015
    Seq = []
    Seq = [i for i in range(0, StepCount)]
    Seq[0] = [1,0,0,1]
    Seq[1] = [1,1,0,0]
    Seq[2] = [0,1,1,0]
    Seq[3] = [0,0,1,1]
elif StepCount == 8:  # Half step
    delay = 0.0015
    StepCount = 8
    Seq = [
        [1,0,0,1],
        [1,0,0,0],
        [1,1,0,0],
        [0,1,0,0],
        [0,1,1,0],  #
        [0,0,1,0],
        [0,0,1,1],
        [0,0,0,1]
        ]

GPIO.setup(M1in1, GPIO.OUT)
GPIO.setup(M1in2, GPIO.OUT)
GPIO.setup(M1in3, GPIO.OUT)
GPIO.setup(M1in4, GPIO.OUT)
GPIO.setup(M2in1, GPIO.OUT)
GPIO.setup(M2in2, GPIO.OUT)
GPIO.setup(M2in3, GPIO.OUT)
GPIO.setup(M2in4, GPIO.OUT)
 
def setStep(l1, l2, l3, l4):
    GPIO.output(M1in1, l1)
    GPIO.output(M1in2, l2)
    GPIO.output(M1in3, l3)
    GPIO.output(M1in4, l4)
    GPIO.output(M2in1, l1)
    GPIO.output(M2in2, l2)
    GPIO.output(M2in3, l3)
    GPIO.output(M2in4, l4)
    logging.debug("{0} {1} {2} {3}".format(l1, l2, l3, l4))
 
def forward(delay, steps):
    for i in range(steps):
        for j in range(StepCount):
            setStep(Seq[j][0], Seq[j][1], Seq[j][2], Seq[j][3])
            time.sleep(delay)
 
def backwards(delay, steps):
    for i in range(steps):
        for j in reversed(range(StepCount)):
            setStep(Seq[j][0], Seq[j][1], Seq[j][2], Seq[j][3])
            time.sleep(delay)
 
if __name__ == '__main__':
    try:
        while True:
            steps = 508
            logging.debug("CW")
            forward(delay, int(steps))
            steps = 508
            logging.debug("CCW")
            backwards(delay, int(steps))
    except KeyboardInterrupt:
        setStep(0,0,0,0)
        sys.exit()
    finally:
        GPIO.cleanup()
        logging.info("GPIO cleaned up")