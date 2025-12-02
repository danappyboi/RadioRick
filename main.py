"""




Important Links:
https://learn.adafruit.com/adafruit-4-channel-adc-breakouts/python-circuitpython
https://learn.adafruit.com/character-lcd-with-raspberry-pi-or-beaglebone-black/usage
"""

import subprocess
import time
from threading import Thread, Lock
from radioStations import radio_stations
import board
from adafruit_ads1x15 import ADS1015, AnalogIn, ads1x15

#TODO: add error correction in case the stream can't be accessed

i2c = board.I2C()
ads = ADS1015(i2c)

VOLUME_PIN = -1     #TODO: set to correct pin
STATION_PIN = -1    #TODO: set to correct pin

player_process = None
current_station_index = 0

def read_pot(pot_pin):
    #TODO: get max and min pot values
    """Reads the given potentiometer value and outputs an int from 0 - 99"""
    if pot_pin == 0:
        chan = AnalogIn(ads, ads1x15.Pin.A0)
    elif pot_pin == 1:
        chan = AnalogIn(ads, ads1x15.Pin.A1)
    else: 
        #should never reach here
        chan = -1
    return chan.value

def send_to_display(text):
    """Displays the given text on the LCD Display"""
    #TODO: write this function

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
    last_percent = -1
    while True:
        value = read_pot(VOLUME_PIN)
        percent = int((value/26592)*100) #TODO: find the volume conversion
        if abs(percent -  last_percent) > 2:
            subprocess.run(["amixer","-c","0","sset","PCM",f"{percent}%"])
            last_percent = percent
        time.sleep(0.05)  # 20 reads/sec

def play_station(station_num):
    """Changes the station to a given url"""
    global player_process
    # Terminate existing player if running
    if player_process:
        player_process.terminate()
        player_process.wait()

    station = radio_stations[station_num]
    url = station["url"]
    name = station["name"]
    city = station["city"]
    # Start new player
    player_process = subprocess.Popen(["mpg123", "-a", "hw:0,0", url]) 
    #TODO: "hw:0,0" is gonna need to change once we add bluetooth

    send_to_display(f"Currently In: {city}\nListening to: {name}")

def station_thread():
    """Constantly checks the station knob and updates accordingly"""
    global current_station_index
    last_station = -1
    while True:
        value = read_pot(STATION_PIN)
        station_num = int((value/26592)*len(radio_stations)) #TODO: find the actual station conversion
        if station_num != last_station:
            with station_lock:
                play_station(station_num)
            last_station = station_num


# Global lock for thread safety
station_lock = Lock()

# Start threads
v_thread = Thread(target=volume_thread, daemon=True)
v_thread.start()

s_thread = Thread(target=station_thread)
s_thread.start()

# Start first station
play_station(radio_stations[current_station_index])

# Keep main thread alive
s_thread.join()







    # # # Replace with your sink names
    # # BT_SINK = "bluez_sink.11_22_33_44_55_66.a2dp_sink"
    # # SPEAKER_SINK = "alsa_output.platform-googlevoicehat_soundcard.stereo-fallback"

    # # Choose output mode:
    # # "bt" = Bluetooth headphones
    # # "speaker" = Adafruit Speaker Bonnet
    # output_mode = "speaker"   # <-- change this anytime

    # def set_output_sink(sink):
    #     print(f"Setting audio sink to {sink}")
    #     subprocess.run(["pactl", "set-default-sink", sink])

    # def play_stream():
    #     print("Starting MP3 stream...")
    #     subprocess.run(["mpg123", "-o", "pulse", STREAM_URL])

    # if __name__ == "__main__":
    #     time.sleep(5)

    #     if OUTPUT_MODE == "bt":
    #         set_output_sink(BT_SINK)
    #     elif OUTPUT_MODE == "speaker":
    #         set_output_sink(SPEAKER_SINK)
    #     else:
    #         print("Invalid OUTPUT_MODE selected.")
    #         exit(1)

    #     while True:
    #         try:
    #             play_stream()
    #         except Exception as e:
    #             print("Playback error:", e)
    #             print("Reconnecting in 3 seconds...")
    #             time.sleep(3)
