#!/Library/Frameworks/Python.framework/Versions/3.7/bin/python3

# Standard Python modules
from time import sleep

# Import everything from the audiosocket server
from audiosocket import new_audiosocket


# Create a new audiosocket instance and start listening
# for incoming connections on the provided address and port
audiosocket = new_audiosocket(addr='10.0.0.18', port=1121)
audiosocket.start()


# Wait until the socket receives a connection
while not audiosocket.connected:
  sleep(1)


# While a connection exists, send all
# received audio back to Asterisk (creates an echo)
while audiosocket.connected:
  audio_data = audiosocket.read()
  audiosocket.write(audio_data)


print('Connection over')
