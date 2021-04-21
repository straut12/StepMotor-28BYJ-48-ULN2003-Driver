import RPi.GPIO as GPIO
import time, logging, sys

logging.basicConfig(level=logging.DEBUG) # Set to CRITICAL to turn logging off. Set to DEBUG to get variables. Set to INFO for status messages.
logging.info("GPIO version: {0}".format(GPIO.VERSION))

def setuparray(stepcount):
    global Seq
    Seq = []      # Create Seq array. Will hold the pulse counts
    if stepcount == 4:  # Full step
        Seq = [i for i in range(0, stepcount)] # initialize the full array
        Seq[0] = [1,0,0,1]
        Seq[1] = [1,1,0,0]
        Seq[2] = [0,1,1,0]
        Seq[3] = [0,0,1,1]
    elif stepcount == 8:  # Half step
        Seq = [i for i in range(0, stepcount)] # note - could also use seq.append to build the array
        Seq[0] = [1,0,0,1]
        Seq[1] = [1,0,0,0]
        Seq[2] = [1,1,0,0]
        Seq[3] = [0,1,0,0]
        Seq[4] = [0,1,1,0]
        Seq[5] = [0,0,1,0]
        Seq[6] = [0,0,1,1]
        Seq[7] = [0,0,0,1]
 
def sendPulses(pulse1, pulse2, pulse3, pulse4):
    GPIO.output(M1in1, pulse1)
    GPIO.output(M1in2, pulse2)
    GPIO.output(M1in3, pulse3)
    GPIO.output(M1in4, pulse4)
    logging.debug("{0} {1} {2} {3}".format(pulse1, pulse2, pulse3, pulse4))
 
def CW(delay, steps, stepcount):
    for i in range(steps):
        for j in range(stepcount):
            sendPulses(Seq[j][0], Seq[j][1], Seq[j][2], Seq[j][3])
            time.sleep(delay)
 
def CCW(delay, steps, stepcount):
    for i in range(steps):
        for j in reversed(range(stepcount)):
            sendPulses(Seq[j][0], Seq[j][1], Seq[j][2], Seq[j][3])
            time.sleep(delay)

# Initialize Hardware
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
M1in1 = 12
M1in2 = 16
M1in3 = 20
M1in4 = 21
GPIO.setup(M1in1, GPIO.OUT)
GPIO.setup(M1in2, GPIO.OUT)
GPIO.setup(M1in3, GPIO.OUT)
GPIO.setup(M1in4, GPIO.OUT)

# Initialize arrays/variables
Seq = []
stepcount = 4 # Change to 4 or 8 to test full vs half step
setuparray(stepcount)

steps = 1     # Use 1 to confirm the sequence. Use 10 to check the motors
delay = 0.0015  # Delay in seconds (1.5ms)

# Main loop
if __name__ == '__main__':
    try:
        logging.debug("CW")
        for i in range(steps):
            CW(delay, steps, stepcount)
        logging.debug("CCW")
        for i in range(steps):
            CCW(delay, steps, stepcount)
    except KeyboardInterrupt:
        sendPulses(0,0,0,0)
        sys.exit()
    finally:
        GPIO.cleanup()
        logging.info("GPIO cleaned up")