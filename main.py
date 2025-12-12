"""
Important Links:
https://learn.adafruit.com/adafruit-4-channel-adc-breakouts/python-circuitpython
https://learn.adafruit.com/character-lcd-with-raspberry-pi-or-beaglebone-black/usage
https://medium.com/@thedyslexiccoder/how-to-set-up-a-raspberry-pi-4-with-lcd-display-using-i2c-backpack-189a0760ae15
https://rplcd.readthedocs.io/en/stable/usage.html
"""

import subprocess
import time
from threading import Thread, Lock
from radioStations import radio_stations
import board
from adafruit_ads1x15 import ADS1015, AnalogIn, ads1x15
from RPLCD.i2c import CharLCD
import RPi.GPIO as GPIO

#TODO: add error correction in case the stream can't be accessed

# Port related variables
i2c = board.I2C()
ads = ADS1015(i2c)
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=20, rows=4, dotsize=8)

BUTTON_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

volume_chan = AnalogIn(ads, ads1x15.Pin.A1)     # Channel for volume potentiometer
station_chan = AnalogIn(ads, ads1x15.Pin.A0)    # Channel for the station potentiometer
POT_MAX = 26600                                 # Max value of the potentiometer

# Thread locks
lcd_lock = Lock()
station_lock = Lock()
player_lock = Lock()
adc_lock = Lock()

player_process = None
current_station_index = 0
use_bluetooth = False

def read_adc(channel):
    """Thread-safe ADC reading"""
    with adc_lock:
        return channel.value

def send_to_display(text):
    """Displays the given text on the LCD Display"""
    with lcd_lock:
        lcd.clear()
        lcd.write_string(text)

def switch_audio_output(use_bt):
    """Switches from bluetooth to onboard speaker"""
    try:
        if use_bt:
            # Get Bluetooth sink name (adjust if your device has a different name pattern)
            result = subprocess.run(
                ["pactl", "list", "short", "sinks"],
                capture_output=True, text=True
            )
            # Look for bluez sink
            for line in result.stdout.splitlines():
                if "bluez" in line.lower():
                    sink_name = line.split()[1]
                    subprocess.run(["pactl", "set-default-sink", sink_name])
                    print(f"Switched to Bluetooth sink: {sink_name}")
                    return True
            print("No Bluetooth sink found!")
            return False
        else:
            # Switch to onboard audio (usually alsa sink)
            result = subprocess.run(
                ["pactl", "list", "short", "sinks"],
                capture_output=True, text=True
            )
            # Look for alsa sink (onboard audio)
            for line in result.stdout.splitlines():
                if "alsa" in line.lower() and "bluez" not in line.lower():
                    sink_name = line.split()[1]
                    subprocess.run(["pactl", "set-default-sink", sink_name])
                    print(f"Switched to onboard sink: {sink_name}")
                    return True
            print("No onboard sink found!")
            return False
    except Exception as e:
        print(f"Error switching audio: {e}")
        return False

"""Threads"""
def volume_thread():
    """Constantly checking the volume and updating accordingly"""
    global player_process
    last_percent = -1

    while True:
        volumePot = read_adc(volume_chan)
        percent = 100 - int((volumePot/POT_MAX)*100) #reverse the potentiometer
        if abs(percent - last_percent) > 2:
            with player_lock:
                if player_process and player_process.stdin:
                    try:
                        player_process.stdin.write(f"VOLUME {percent}\n")
                        player_process.stdin.flush()
                        last_percent = percent
                    except:
                        pass
        time.sleep(0.05)  # 20 reads/sec

def play_station(station_num):
    """Changes the station to a given station number"""
    global player_process
    print(f"play station called for station {station_num}")
    
    # if theres already a player in process, kill it
    if player_process:
        print("Terminating old player...")
        player_process.terminate()
        try:
            player_process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            print("Process didn't terminate, killin it")
            player_process.kill()
            player_process.wait()
        player_process = None

    print("Starting new player...")
    station = radio_stations[station_num]
    url = station["url"]

    # Start new player
    player_process = subprocess.Popen(
        ["mpg123", "-R", "-q", "-o", "pulse"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    player_process.stdin.write(f"LOAD {url}\n")
    player_process.stdin.flush()
    print(f"Player started for {station['name']}")

    name = station["name"]
    city = station["city"]
    output = "BT" if use_bluetooth else "Speaker"

    send_to_display(f"{city} [{output}]\r\n{name}") #TODO: add song title!!!

    print("play_station done")

def station_thread():
    """Constantly checks the station knob and updates accordingly"""
    global current_station_index
    last_station = -1
    current_reading = -1
    stable_count = 0    # counter for stable readings
    
    while True:
        stationPot = read_adc(station_chan)
        station_num = min(int((stationPot / POT_MAX) * len(radio_stations)), len(radio_stations) - 1)
        
        # DEBUG: Print what we're seeing
        print(f"Raw pot: {stationPot}, Station: {station_num}, Stable: {stable_count}, Last: {last_station}")
        
        # Check if reading is stable
        if station_num == current_reading:
            stable_count += 1
        else:
            current_reading = station_num
            stable_count = 0

        # Only switch if we have 5 stable readings AND it's different from current station
        if stable_count >= 5 and station_num != last_station:
            print(f"SWITCHING TO STATION {station_num}")
            current_station_index = station_num
            play_station(station_num)
            last_station = station_num
            stable_count = 0
            
        time.sleep(0.05)

def button_thread():
    """Monitors button press to toggle between Bluetooth and onboard audio"""
    global use_bluetooth, current_station_index
    last_button_state = None
    
    while True:
        button_state = GPIO.input(BUTTON_PIN)
        
        # Button pressed (LOW because of pull-up resistor)
        if button_state != last_button_state and last_button_state != None:
            time.sleep(0.05)  # Debounce
            button_state = GPIO.input(BUTTON_PIN)
            
            should_use_bluetooth = (button_state == GPIO.LOW)
            if should_use_bluetooth != use_bluetooth:
                use_bluetooth = should_use_bluetooth
                print("we finna switch")

                # Switch PipeWire sink
                if switch_audio_output(use_bluetooth):
                    # Update display without restarting player
                    station = radio_stations[current_station_index]
                    name = station["name"]
                    city = station["city"]
                    output = "BT" if use_bluetooth else "Onboard"
                    send_to_display(f"{city} [{output}]\r\n{name}")
                else:
                    # Switch failed, revert
                    use_bluetooth = not use_bluetooth
                
        last_button_state = button_state
        time.sleep(0.05)

# Start threads
v_thread = Thread(target=volume_thread, daemon=True)
v_thread.start()

s_thread = Thread(target=station_thread, daemon=True)
s_thread.start()

b_thread = Thread(target=button_thread, daemon=True)
b_thread.start()

# m_thread = Thread(target=metada, daemon=True)
# m_thread.start()

# Start first station
play_station(current_station_index)

# Keep main thread alive
s_thread.join()
