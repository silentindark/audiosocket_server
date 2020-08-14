# Standard Python modules
from time import sleep

# Import everything from the new_audiosocket class
from audiosocket import new_audiosocket


# Create a new audiosocket instance and start listening
# for incoming connections on the provided address and port
audiosocket = new_audiosocket(addr='127.0.01', port=3278)
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
