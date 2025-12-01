from gpiozero import LED
from time import sleep

led = LED(21) # Create an LED object connected to BCM pin 17

while True:
    led.on()  # Turn the LED on
    sleep(1)  # Wait for 1 second
    led.off() # Turn the LED off
    sleep(1)  # Wait for 1 second