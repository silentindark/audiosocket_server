# Standard Python modules
import socket
from threading import Thread
from dataclasses import dataclass
from time import sleep

from connection import *



@dataclass
class audioop_struct:
  ratecv_state: None
  rate: int
  channels: int
  ulaw2lin: bool
  


# ********************************************************************************************
# *** Make a single, global object instance, then loop with listen() method alone where needed


# Creates a new audiosocket object
class Audiosocket:
  def __init__(self, bind_info, timeout=None):

    # By default, features of audioop (for example: resampling
    # or re-mixng input/output) are disabled
    self.user_resample = None
    self.asterisk_resample = None


    if not isinstance(bind_info, tuple):
      raise TypeError("Expected tuple (addr, port), received", type(bind_info))


    self.addr, self.port = bind_info

    self.initial_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.initial_sock.bind((self.addr, self.port))
    self.initial_sock.settimeout(timeout)
    self.initial_sock.listen(1)

    # If the user didn't specify a port, the one that the operating system
    # chose is availble in this attribute
    self.port = self.initial_sock.getsockname()[1]



  # Optionally prepares audio sent by the user to
  # the specifications needed by audiosocket (16-bit, 8KHz mono LE PCM).
  # Audio sent in must be in PCM or ULAW format
  def prepare_input(self, inrate=44000, channels=2, ulaw2lin=False):
    self.user_resample = audioop_struct(
      rate = inrate,
      channels = channels,
      ulaw2lin = ulaw2lin,
      ratecv_state = None,
    )



  # Optionally prepares audio sent by audiosocket to
  # the specifications of the user
  def prepare_output(self, outrate=44000, channels=2, ulaw2lin=False):
    self.asterisk_resample = audioop_struct(
      rate = outrate,
      channels = channels,
      ulaw2lin = ulaw2lin,
      ratecv_state = None,
    )



  def listen(self):

    conn, peer_addr = self.initial_sock.accept()
    connection = Connection(
      conn,
      peer_addr,
      self.user_resample,
      self.asterisk_resample,
    )

    connection_thread = Thread(target=connection._process, args=())
    connection_thread.start()

    return connection

    # *** If we want this single object to serve multiple simultaneous connections, accept() will have to be put in a while loop
    # If this does become the case, what is the best way to deliver the queue objects to the caller, keep them wrapped in read/write methods?
