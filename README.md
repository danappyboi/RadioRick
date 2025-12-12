# Radio Rick 
<img width="1280" height="853" alt="image" src="https://github.com/user-attachments/assets/a567f56b-635b-4984-913c-7e26d1ce7e9c" />


This is a repo for the Fall 2025 CMU 60-223 Project, [RadioRick](https://sites.google.com/andrew.cmu.edu/60-223-f25/final-project-documentation/bluestem-radio?authuser=1). For this project, we were assigned a member for FMS and the task of designing a product that would help them in their jobs. We were assigned with Rick, a mason with 50+ years of experience and little to be added to his already impressive skillset. Instead, we decided to design a gift for Rick, a radio that would listen to radio stations in Las Vegas, Paris, and Pittsburgh. This would be done by using a Raspberry Pi Zero 2 to listen to already assigned radio station that transmitted MP3 streams through urls. This would then be played on the Pi through speakers, or through bluetooth if connected, with adjustable volume and stations with physical knobs on the device. 

The main script is located in [main.py](https://github.com/danappyboi/RadioRick/blob/master/main.py), and runs immediately when the Pi boots up. Additional channels can be added through [radioStations.py](https://github.com/danappyboi/RadioRick/blob/master/radioStations.py).

Written by Helios, Hua, and Maggie (and a little bit of Claude lol)
