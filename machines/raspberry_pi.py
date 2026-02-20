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
    def __init__(self, in1=23, in2=24, ena=12, lock_pin=16, pwm_freq=1000):
        # BCM Pin Mapping: Physical 16->23, Physical 18->24, Physical 32->12
        self.in1 = in1
        self.in2 = in2
        self.ena_pin = ena
        self.lock_pin = lock_pin
        self.pwm_freq = pwm_freq
        self.pwm = None
        self.status = "connected"


    def connect(self, method, ip, port, com, baud, timeout=10):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup([self.in1, self.in2, self.lock_pin, self.ena_pin], GPIO.OUT)
        
        # Initialize PWM on the ENA pin
        self.pwm = GPIO.PWM(self.ena_pin, self.pwm_freq)
        self.pwm.start(0)
        
        self.connected = True
        logging.info(f"GPIO Initialized: IN1={self.in1}, IN2={self.in2}, ENA={self.ena_pin}")
        return {"status": "connected"}
    
    def is_connected(self):
        return True

    def screw(self, direction: str, duration: float = 0, speed: int = 50):
        if not self.connected: raise RuntimeError("GPIO not initialized")
        
        direction = direction.upper()
        duty = max(0, min(100, speed)) # Ensure speed is 0-100%

        if direction == "CW":
            GPIO.output(self.in1, GPIO.HIGH)
            GPIO.output(self.in2, GPIO.LOW)
            self.pwm.ChangeDutyCycle(duty)
        elif direction == "CCW":
            GPIO.output(self.in1, GPIO.LOW)
            GPIO.output(self.in2, GPIO.HIGH)
            self.pwm.ChangeDutyCycle(duty)
        else: # STOP
            GPIO.output(self.in1, GPIO.LOW)
            GPIO.output(self.in2, GPIO.LOW)
            self.pwm.ChangeDutyCycle(0)
            return ["STOP"]

        if duration > 0:
            time.sleep(duration)
            self.screw("STOP")

        return [f"{direction} at {speed}% for {duration}s"]
    
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
