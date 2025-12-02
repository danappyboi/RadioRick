import board
from adafruit_ads1x15 import ADS1015, AnalogIn, ads1x15


i2c = board.I2C()
ads = ADS1015(i2c)

def get_pot(pot_pin):
    """Value from 0 - 65535"""
    if pot_pin == 0:
        chan = AnalogIn(ads, ads1x15.Pin.A0)
    elif pot_pin == 1:
        chan = AnalogIn(ads, ads1x15.Pin.A1)
    else: 
        #should never reach here
        chan = -1
    return chan.value