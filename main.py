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
import re

#TODO: add error correction in case the stream can't be accessed

i2c = board.I2C()
ads = ADS1015(i2c)
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=20, rows=4, dotsize=8)

VOLUME_PIN = 1     
STATION_PIN = 0 
POT_MAX = 26600     #the max read of the potentiometer

player_process = None
current_station_index = 0

lcd_lock = Lock()
station_lock = Lock()
player_lock = Lock()
adc_lock = Lock()

volume_chan = AnalogIn(ads, ads1x15.Pin.A1)
station_chan = AnalogIn(ads, ads1x15.Pin.A0)

def read_adc(channel):
    """Thread-safe ADC reading"""
    with adc_lock:
        return channel.value

#TODO: change to getting the meta data
def get_stream_title(url):
    """
    Gets the artist and song title if it exists
    """
    # Run mpg123 with verbose output (-v) and to standard error (2>&1)
    # We use -q (quiet) to avoid other non-essential output and pipe stderr
    # We also use --ICY-INTERVAL to ensure metadata is processed if available
    # Max-time 1 second just to get metadata and stop
    cmd = ['mpg123', '-q', '-v', '--ICY-INTERVAL', '1', '--max-time', '1', url]
    
    try:
        # Use subprocess.Popen to run the command and capture stderr
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)
        time.sleep(0.5) 
        process.terminate() 
        
        stderr_output = process.stderr.read()
        
        # Search for the StreamTitle in the captured output
        # The output format usually looks like: ICY Info: StreamTitle='Title Here';
        match = re.search(r"ICY Info: StreamTitle='(.*?)';", stderr_output)
        
        if match:
            return match.group(1)
        else:
            return ""
            
    # should actually never get to this lol
    except FileNotFoundError:
        return "Error: mpg123 not found. Make sure it is installed and in your PATH."
    except Exception as e:
        return f"An error occurred: {e}"


def send_to_display(text):
    """Displays the given text on the LCD Display"""
    with lcd_lock:
        lcd.clear()
        lcd.write_string(text)

def get_volume():
    """Get the current volume as an int"""
    result = subprocess.run(
        ["amixer", "-c", "0", "sget", "PCM"],
        capture_output=True, text=True
    )
    # Parse output for volume
    for line in result.stdout.splitlines():
        if "Front Left:" in line:
            vol = line.split("[")[1].split("%")[0]
            return int(vol)
    return None

"""Threads"""

def volume_thread():
    """Constantly checking the volume and updating accordingly"""
    global player_process
    last_percent = -1

    while True:
        volumePot = read_adc(volume_chan)
        percent = int((volumePot/POT_MAX)*100)
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
    """Changes the station to a given url"""
    global player_process
    # Terminate existing player if running
    
    print(f"play station called for station {station_num}")
    
    if player_process:
        print("Terminating old player...")
        player_process.terminate()
        player_process.wait()
        player_process = None

    print("Starting new player...")
    station = radio_stations[station_num]
    url = station["url"]

    # Start new player
    player_process = subprocess.Popen(
        ["mpg123", "-R", "-q"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    player_process.stdin.write(f"LOAD {url}\n")
    player_process.stdin.flush()
    print(f"Player started for {station['name']}")

    #TODO: "hw:0,0" is gonna need to change once we add bluetooth

    name = station["name"]
    city = station["city"]

    send_to_display(f"{city}\r\n{name}")

    print("play_station done")
    # send_to_display(f"{city}\r\n{name}\r\n{get_stream_title}")

def NEW_station_thread():
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



def station_thread():
    """Constantly checks the station knob and updates accordingly"""
    global current_station_index
    chan = read_adc(station_chan)
    last_station = -1
    stable_count = 0    #counter for stable readings
    current_reading = -1
    while True:
        stationPot = read_adc(station_chan)
        station_num = min(int((stationPot / POT_MAX) * len(radio_stations)), len(radio_stations) - 1)
        
        if station_num == last_station:
            stable_count += 1
        else:
            stable_count = 0

        if stable_count >= 5 and station_num != last_station:
            current_station_index = station_num
            play_station(station_num)
            last_station = station_num
            stable_count = 0
            
        time.sleep(0.05)




# Start threads
v_thread = Thread(target=volume_thread, daemon=True)
v_thread.start()

s_thread = Thread(target=NEW_station_thread, daemon=True)
s_thread.start()

# m_thread = Thread(target=metada, daemon=True)
# m_thread.start()

# Start first station
play_station(current_station_index)

# Keep main thread alive
s_thread.join()

#try:
#    while True:
#        time.sleep(1)
#except KeyboardInterrupt:
#    print("\nShutting down...")
#    with player_lock:
#        if player_process:
#            player_process.terminate()
