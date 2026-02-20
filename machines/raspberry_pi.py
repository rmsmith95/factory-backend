import time
import logging
import time
import logging
import os

# Check if we are running on a Raspberry Pi (Linux)
try:
    import RPi.GPIO as GPIO
    IS_RPI = True
except (ImportError, RuntimeError):
    IS_RPI = False
    logging.warning("RPi.GPIO not found or not on Pi. Switching to Mock mode.")

    # Define a Mock object to prevent NameErrors on Windows
    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        HIGH = "HIGH"
        LOW = "LOW"
        def setmode(self, mode): pass
        def setup(self, pin, mode): pass
        def output(self, pin, state): pass
        def cleanup(self): pass
        def PWM(self, pin, freq):
            return MockPWM()

    class MockPWM:
        def start(self, duty): pass
        def stop(self): pass
        def ChangeDutyCycle(self, duty): pass

    GPIO = MockGPIO()


class RaspberryPi:
    def __init__(self, dir_pin=20, pwm_pin=21, lock_pin=16, pwm_freq=1000):
        self.dir_pin = dir_pin
        self.pwm_pin = pwm_pin
        self.pwm_freq = pwm_freq
        self.pwm = None
        self.lock_pin = lock_pin
        self.connected = False

    def connect(self, method, ip, port, com, baud):
        """Initialize GPIO pins on Raspberry Pi"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.dir_pin, GPIO.OUT)
        GPIO.setup(self.pwm_pin, GPIO.OUT)
        GPIO.setup(self.lock_pin, GPIO.OUT)

        self.pwm = GPIO.PWM(self.pwm_pin, self.pwm_freq)
        self.pwm.start(0)  # start with 0% duty cycle
        # GPIO.output(self.lock_pin, GPIO.Low)  # enable motor driver

        self.connected = True
        logging.info("Connected to Raspberry Pi GPIO")
        return {"status": "connected", "type": "gpio"}

    def is_connected(self) -> bool:
        return self.connected

    def screw(self, direction: str, duration: float = 0, speed: int = 50):
        """
        direction: 'CW', 'CCW', or 'STOP'
        duration: seconds (ignored for STOP)
        speed: 0-100 (duty cycle %)
        """
        if not self.is_connected():
            logging.info("Raspberry Pi GPIO not initialized")
            raise RuntimeError("GPIO not initialized")

        direction = direction.upper()

        if direction == "STOP":
            logging.info("Stopping motor")
            self.pwm.ChangeDutyCycle(0)
            return ["STOP"]

        if direction not in ("CW", "CCW"):
            raise ValueError("Direction must be 'CW', 'CCW', or 'STOP'")

        # Set direction pin
        GPIO.output(self.dir_pin, GPIO.HIGH if direction == "CW" else GPIO.LOW)

        logging.info(f"GPIO screwdriver cmd: {direction}, speed={speed}, duration={duration}s")

        # Set speed
        self.pwm.ChangeDutyCycle(max(0, min(100, speed)))

        # Run for duration
        if duration > 0:
            time.sleep(duration)
            self.pwm.ChangeDutyCycle(0)

        return [f"{direction} {speed}% for {duration}s"]
    
    def unlock(self, time_s: float = 10.0):
        """ Retracts the solenoid lock for a specified duration. """
        # if not self.is_connected():
        #     logging.error("GPIO not initialized")
        #     return
            
        logging.info(f"Unlocking solenoid for {time_s}s")
        
        try:
            # Energize to retract (Unlock)
            GPIO.output(self.lock_pin, GPIO.HIGH) 
            time.sleep(time_s)
        finally:
            # De-energize to extend (Lock)
            GPIO.output(self.lock_pin, GPIO.LOW)
            logging.info("Solenoid locked")

    def cleanup(self):
        """Cleanup GPIO on exit"""
        if self.pwm:
            self.pwm.stop()
        GPIO.cleanup()
        self.connected = False
