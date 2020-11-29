# Standard Python modules
from time import sleep

# Import everything from the audiosocket module
from audiosocket import *

# Create a new Audiosocket instance, passing it binding
# information in a tuple just as you would a raw socket
audiosocket = Audiosocket(("10.0.0.18", 1121))

# This will block until a connection is received, returning
# a connection object when one occurs
conn = audiosocket.listen()


print('Received connection from {0}'.format(conn.peer_addr))


# While a connection exists, send all
# received audio back to Asterisk (creates an echo)
while conn.connected:
  audio_data = conn.read()
  conn.write(audio_data)


print('Connection with {0} over'.format(conn.peer_addr))
