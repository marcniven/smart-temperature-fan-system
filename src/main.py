import time
import smbus
import RPi.GPIO as GPIO
import threading

GPIO.setmode(GPIO.BCM)

# Thermistor setup
ADDRESS = 0x48
THERMISTOR_CH = 0x41
VOLTAGE = 3.3
LEVELS = 255
bus = smbus.SMBus(1)
COOL_V = 2.95
WARM_V = 2.6
COLDEST_V = 3.01 #room temp for testing purposes
HOTTEST_V = 2.4 #max temp for testing purposes with hair dryer as heat source 

# LED setup
LED_PIN = 21
LED_FREQ = 60 
LED_OFF = 0
GPIO.setup(LED_PIN, GPIO.OUT)
led_pwm = GPIO.PWM(LED_PIN, LED_FREQ)
led_pwm.start(LED_OFF)

# Servo Motor setup
SERVO_PIN = 18
NEUTRAL_DC = 6.5
MIN_DC = 2.5
MAX_DC = 10.5
MOTOR_FREQ = 50
HIGH_TIME=0.00001
LOW_TIME=1-HIGH_TIME
START_ANGLE = -45
END_ANGLE = 45
STEP_ANGLE = 15
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo_pwm = GPIO.PWM(SERVO_PIN, MOTOR_FREQ)
servo_pwm.start(NEUTRAL_DC)
fan_speed = None

# Ultrasonic Sensor setup
TRIG = 27
ECHO = 17
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
SPEED_OF_SOUND = 340.0 / 10000 
DIST_THRESHOLD = 10

# Gets temperature (in voltage) from thermistor
def read_temp_voltage():
    bus.write_byte(ADDRESS, THERMISTOR_CH)
    value = bus.read_byte(ADDRESS)
    voltage = value * VOLTAGE / LEVELS
    return voltage

# Gets distance from ultrasonic sensor
def measure_distance():
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(HIGH_TIME)
    GPIO.output(TRIG, GPIO.LOW)
    while GPIO.input(ECHO) == False:
        start = time.time()
    while GPIO.input(ECHO) == True:
        end = time.time()
    duration = end - start
    distance = duration * SPEED_OF_SOUND * 1000000 / 2 
    return distance

# Move servo motor (fan) based on fan_speed
def fan_oscillation():
    global fan_speed
    while True:
        if fan_speed == "slow":
            for angle in range(START_ANGLE, END_ANGLE + 1, STEP_ANGLE):
                duty = NEUTRAL_DC + (angle / 90.0) * (MAX_DC - NEUTRAL_DC)
                servo_pwm.ChangeDutyCycle(duty)
                time.sleep(0.2)
            for angle in range(END_ANGLE, START_ANGLE - 1, -STEP_ANGLE):
                duty = NEUTRAL_DC + (angle / 90.0) * (MAX_DC - NEUTRAL_DC)
                servo_pwm.ChangeDutyCycle(duty)
                time.sleep(0.2)

        elif fan_speed == "fast":
            servo_pwm.ChangeDutyCycle(MIN_DC)
            time.sleep(0.5)
            servo_pwm.ChangeDutyCycle(MAX_DC)
            time.sleep(0.5)

        else:
            servo_pwm.ChangeDutyCycle(NEUTRAL_DC)
            time.sleep(0.5)

# Background thread for fan movement while ultrasonic sensor is running
threading.Thread(target=fan_oscillation, daemon=True).start()

try:
    while True:
        temp_voltage = read_temp_voltage()
        distance = measure_distance()
        person_detected = distance < DIST_THRESHOLD

        # LED brightness inversely proportional to temp voltage
        duty_cycle = max(min((COLDEST_V - temp_voltage) / (COLDEST_V - HOTTEST_V) * 100, 100), 0)
        led_pwm.ChangeDutyCycle(duty_cycle)

        # Determine and set fan_speed
        if temp_voltage > COOL_V:
            fan_speed = None  # room is cool, fan off

        elif WARM_V < temp_voltage <= COOL_V:
            if person_detected:
                fan_speed = "fast"  # room is warm and person detected, fan speed fast
            else:
                fan_speed = "slow"  # room is warm, no person detected, fan speed slow

        else: 
            fan_speed = "fast"  # room is hot, fan speed fast

        print(f"TEMP: {temp_voltage:.4f} V | LED: {duty_cycle:.1f}% | DIST: {distance:.2f} cm | FAN: {fan_speed}")

        time.sleep(1)

except KeyboardInterrupt:
    print("Exiting program...")

finally:
    led_pwm.stop()
    fan_speed = None
    time.sleep(1.0)
    servo_pwm.stop()
    GPIO.cleanup()

