# Standard Python modules
from threading import Thread

# Audiosocket module
from audiosocket import *


# Create a globally accessible audiosocket instance
audiosocket = Audiosocket(('0.0.0.0', 1121))


# Upsample received (output) audio to CD quality, then downsample it back
# to telephone quality before sending it (input)

"""
*** Please note that I have occasionally encountered an audioop
'not a whole number of frames' error while reading data, please let
 me know if you encounter this excessively
"""
audiosocket.prepare_output(outrate=44000, channels=2)
audiosocket.prepare_input(inrate=44000, channels=2)


# The port attribute is useful when you've let the operating system
# choose an open for you (when passing 0 as the socket's bind port)
print('Listening for new connections from Asterisk on port {0}'.format(audiosocket.port))


# The function which each individual call will be sent off to
def handle_connection(call):

  cntr = 0
  print('Received connection from {0}'.format(call.peer_addr))

  while call.connected:
    audio_data = call.read()
    call.write(audio_data)

    # Hangup the call after receiving 1000 audio frames
    if cntr == 1000:
      call.hangup()

    cntr += 1


  print('Connection with {0} is now over'.format(call.peer_addr))



# Listen for new connections forever, giving each one its
# own thread to execute within. When accepting connections in this style,
# you wouldn't want to have any timeout on the socket.

while True:
  call = audiosocket.listen()  

  call_thread = Thread(target=handle_connection, args=(call,))
  call_thread.start()
