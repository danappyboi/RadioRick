from gpiozero import Button
import board
import busio
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from signal import pause
import time
from threading import Thread

class RadioSimulator:
    def __init__(self):
        # Initialize I2C bus
        i2c = busio.I2C(board.SCL, board.SDA)
        
        # Create ADS1015 object
        ads = ADS.ADS1015(i2c)
        
        # Set up play/pause button (connected to GPIO17)
        self.play_button = Button(17)
        
        # Set up volume potentiometer (connected to channel 0)
        self.volume_pot = AnalogIn(ads, ADS.P0)
        
        # Set up station switching potentiometer (connected to channel 1)
        self.station_pot = AnalogIn(ads, ADS.P1)
        
        # State variables
        self.is_playing = False
        self.current_volume = 0
        self.current_station = 0
        self.station_count = 10
        
        # Bind button event
        self.play_button.when_pressed = self.toggle_playback
        
        # Start monitoring threads
        self.monitor_controls()
    
    def toggle_playback(self):
        """Toggle play/pause state"""
        self.is_playing = not self.is_playing
        if self.is_playing:
            print("Playing")
            # Call your play function here
        else:
            print("Paused")
            # Call your pause function here
    
    def get_volume(self):
        """Read volume value (0-100)"""
        # ADS1015 value range is 0-26400 for the raw value
        # Convert to percentage
        return int((self.volume_pot.value / 26400) * 100)
    
    def get_station_index(self):
        """Read station index"""
        # Map potentiometer value to station count
        ratio = self.station_pot.value / 26400
        return int(ratio * (self.station_count - 0.001))
    
    def monitor_controls(self):
        """Continuously monitor potentiometer changes"""
        def check_volume():
            while True:
                new_volume = self.get_volume()
                # Only update when volume changes by more than 2% (reduce jitter)
                if abs(new_volume - self.current_volume) > 2:
                    self.current_volume = new_volume
                    print(f"Volume adjusted to: {self.current_volume}%")
                    # Call your volume setting function here
                time.sleep(0.1)
        
        def check_station():
            while True:
                new_station = self.get_station_index()
                if new_station != self.current_station:
                    self.current_station = new_station
                    print(f"Switched to station {self.current_station + 1}")
                    # Call your station switching function here
                time.sleep(0.1)
        
        # Run monitoring in background threads
        Thread(target=check_volume, daemon=True).start()
        Thread(target=check_station, daemon=True).start()

if __name__ == "__main__":
    radio = RadioSimulator()
    print("Radio simulator started")
    
    try:
        pause()  # Keep program running
    except KeyboardInterrupt:
        print("\nProgram exited")