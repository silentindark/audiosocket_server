# Standard Python modules
import socket
import audioop
from threading import Thread
from collections import namedtuple
from queue import Queue, Empty
from time import sleep


# A sort of imitation struct that holds all of the possible
# message types we can receive from AudioSocket
types_struct = namedtuple(
'types',
 [
  'uuid',    # Message payload contains UUID set in Asterisk Dialplan
  'audio',   # * Message payload contains 8KHz 16-bit mono LE PCM audio (* See Github readme)
  'silence', # Message payload contains silence (I've never seen this occur personally)
  'hangup',  # Tell Asterisk to hangup the call (This doesn't appear to ever be sent from Asterisk to us)
  'error'    # Message payload contains an error from Asterisk
 ],
defaults=
 [
  b'\x01',
  b'\x10',
  b'\x02',
  b'\x00',
  b'\xff'
 ]
)


# The size of 20ms of 8KHz 16-bit mono LE PCM represented as a
# 16 bit (2 byte, size of length header) unsigned BE integer

# This amount of the audio data mentioned above is equal 
# to 320 bytes, which is the required payload size when
# sending audio back to AudioSocket for playback on the
# bridged channel. Sending more or less data will result in distorted sound
PCM_SIZE = (320).to_bytes(2, 'big')


# Similar to one above, this holds all the possible
# error codes that can be sent to us from AudioSocket
errors_struct = namedtuple(
'errors',
 [
  'none',
  'hangup',
  'frame',
  'memory'
 ],
defaults=
 [
  b'\x00',
  b'\x01',
  b'\x02',
  b'\x04'
 ]
)


types = types_struct()
errors = errors_struct()


# Creates a new audiosocket object, this subclasses the Thread class
class new_audiosocket(Thread):
  def __init__(self, rx_audio_q=Queue(1000), tx_audio_q=Queue(1000), addr=None, port=0, timeout=None):
    Thread.__init__(self)

    # Queue objects for sending and receiving audio
    self.rx_audio_q = rx_audio_q
    self.tx_audio_q = tx_audio_q

    # If a timeout isn't manually specified, it defaults to infinite
    self.timeout = timeout

    # If an address isn't specified, bind to all available
    if not addr:
      self.addr = '0.0.0.0'
    else:
      self.addr = addr

    # If a port number isn't specified, let the OS
    # choose an available one
    self.port = port

    self.conn = None
    self.peer_addr = None
    self.uuid = None
    self.connected = False

    # By default, features of audioop (for example: resampling
    # or re-mixng input/output) are disabled
    self.audioop = None
    self.prepare_input_enabled = False
    self.prepare_output_enabled = False

    # Create the initial socket that will accept an incoming connection from AudioSocket
    self.initial_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.initial_sock.bind((self.addr, self.port))
    self.initial_sock.settimeout(self.timeout)
    self.initial_sock.listen(3)

    # If the user didn't specify a port, the one that the operating system
    # chose is availble in this attribute
    self.port = self.initial_sock.getsockname()[1]
    print('[AUDIOSOCKET NOTICE] Listening for connection from AudioSocket on port {0}'.format(self.port))


  # Optionally prepares audio sent by the user to
  # the format needed by audiosocket (16-bit, 8KHz mono LE PCM).
  # Audio sent in must be in PCM or ULAW format
  def prepare_input(self, inrate=44000, channels=2, ulaw2lin=False):
    self.prepare_input_enabled = True

    if not self.audioop:
      self.audioop = audioop

    self.in_ratecv_state = None
    self.inrate = inrate
    self.in_channels = channels
    self.in_ulaw2lin = ulaw2lin


  # Optionally prepares audio sent by audiosocket to
  # the format that the user specified
  def prepare_output(self, outrate=44000, channels=2, ulaw2lin=False):
    self.prepare_output_enabled = True

    if not self.audioop:
      self.audioop = audioop

    self.out_ratecv_state = None
    self.outrate = outrate
    self.out_channels = channels
    self.out_ulaw2lin = ulaw2lin


  # Splits data sent by AudioSocket into three different peices
  def split_data(self, data):
    if len(data) < 3:
      print('[AUDIOSOCKET ERROR] The data received was less than 3 bytes, ' + \
      'the minimum length data from Asterisk AudioSocket should be.')
      return
    else:
           # type      length (convert to an int)        payload
      return data[:1], int.from_bytes(data[1:3], 'big'), data[3:]


  # Turns the two bytes from the length header back into the
  # 16-bit BE unsigned integer they represent.
  # This is now performed when returing the data above
  def convert_length(self, length):
    return int.from_bytes(length, 'big', signed=False)


  # If the type of message received was an error, this
  # prints an explanation of the specific one that occurred
  def decode_error(self, payload):
    if payload == errors.none:
      print('[ASTERISK ERROR] No error code present')

    elif payload == errors.hangup:
      print('[ASTERISK ERROR] The called party hungup')

    elif payload == errors.frame:
      print('[ASTERISK ERROR] Failed to forward frame')

    elif payload == errors.memory:
      print('[ASTERISK ERROR] Memory allocation error')

    return


  # Gets AudioSocket audio from the rx queue
  def read(self):
    try:
      audio = self.rx_audio_q.get(timeout=0.2)

      if self.prepare_output_enabled:
        # If AudioSocket is bridged with a channel
        # using the ULAW audio codec, the user can specify
        # to have it converted to linear encoding  upon reading.
        if self.out_ulaw2lin:
          audio = self.audioop.ulaw2lin(audio, 2)

        # If the user requested an outrate different
        # from the default, then resample it to the rate they specified
        if self.outrate != 8000:
          audio, self.out_ratecv_state = self.audioop.ratecv(audio, 2, 1, 8000,
          self.outrate, self.out_ratecv_state)

        # If the user requested the output be in stereo,
        # then convert it from mono
        if self.out_channels == 2:
          audio = self.audioop.tostereo(audio, 2, 1, 1)

      return audio

    except Empty:
      print('[AUDIOSOCKET WARNING] The inbound audio queue is empty! ' + \
      'Nothing to read, returning silence')
      return byte(320)



  # Puts user supplied audio into the tx queue
  def write(self, audio):
    if self.tx_audio_q.full():
      print('[AUDIOSOCKET WARNING] The outbound audio queue is full!' Skipping frame write)
      return

    if self.prepare_input_enabled:
      # The user can also specify to have ULAW encoded source audio
      # converted to linear encoding upon being written.
      if self.in_ulaw2lin:
        # Possibly skip downsampling if this was triggered, as
        # while ULAW encoded audio can be sampled at rates other
        # than 8KHz, since this is telephony related, it's unlikely.
        audio = self.audioop.ulaw2lin(audio, 2)

      # If the audio isn't already sampled at 8KHz,
      # then it needs to be downsampled first
      if self.inrate != 8000:
        audio, self.in_ratecv_state = self.audioop.ratecv(audio, 2,
        self.in_channels, self.inrate, 8000, self.in_ratecv_state)

      # If the audio isn't already in mono, then
      # it needs to be downmixed as well
      if self.in_channels == 2:
        audio = self.audioop.tomono(audio, 2, 1, 1)

    self.tx_audio_q.put(audio)



  # Tells Asterisk to hangup the call from it's end.
  # Although after the call is hungup, the socket on Asterisk's end
  # closes the connection via an abrupt RST packet, resulting in a "Connection reset by peer"
  # error on our end. Unfortunately, using try and except around self.conn.recv() is as 
  # clean as I think it can be right now
  def hangup(self):
    print('[AUDIOSOCKET NOTICE] Sending hangup request to Asterisk')
    # Three bytes of 0 indicate a hangup message
    self.conn.send(types.hangup * 3)
    sleep(0.2)
    return



  def cleanup(self):
    self.connected = False
    print('[AUDIOSOCKET NOTICE] Ended connection with {0}'.format(self.peer_addr))
    print('[AUDIOSOCKET NOTICE] The call\'s UUID was: {0}'.format(self.uuid))

    if self.conn:
      self.conn.close()

    return



  # When the start() method of the audiosocket object is called
  # (provided by the Thread class), this run() function is executed in a separate thread
  def run(self):
    try:
      self.conn, self.peer_addr = self.initial_sock.accept()
      self.connected = True
      print('[AUDIOSOCKET NOTICE] Server received a connection from {0}'.format(self.peer_addr))
    except socket.timeout:
      self.connected = False
      print('[AUDIOSOCKET ERROR] Server didn\'t receive a connection after ' + \
      '{0} seconds, closing...'.format(self.timeout))
      self.initial_sock.close()
      return


    # The main audio receiving/sending loop, this continues
    # until AudioSocket stops sending us data, or an error occurs.
    # A disconnection can be triggered from the users end by calling the hangup() method
    while True:

      try:
        data = self.conn.recv(323)
      except ConnectionResetError:
        self.cleanup()
        return

      if not data:
        self.cleanup()
        return

      type, length, payload = self.split_data(data)

      if type == types.error:
        self.decode_error(payload)

      elif type == types.uuid:
        self.uuid = payload.hex()

      elif type == types.audio:
        # Adds received audio into the rx queue
        if self.rx_audio_q.full():
          print('[AUDIOSOCKET WARNING] The inbound audio queue is full! This most ' + \
          'likely occurred because the read() method is not being called, skipping frame')
        else:
          self.rx_audio_q.put(payload)

        # To prevent the tx queue from blocking all execution if
        # the user doesn't supply it with (enough) audio, silence is
        # generated manually and sent back to AudioSocket whenever its empty.
        if self.tx_audio_q.empty():
          self.conn.send(types.audio + PCM_SIZE + bytes(320))
        else:
          # If a single peice of audio data in the rx queue is larger than
          # 320 bytes, slice it before sending, however...
          # If the audio data to send is larger than this, then
          # it's probably in the wrong format to begin with and wont be
          # played back properly even when sliced.
          audio_data = self.tx_audio_q.get()[:320]
          self.conn.send(types.audio + len(audio_data).to_bytes(2, 'big') + audio_data)
