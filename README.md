# Asterisk AudioSocket Server

A Python socket server for use with the [Asterisk](https://github.com/asterisk/asterisk) [AudioSocket](https://github.com/CyCoreSystems/audiosocket) Dialplan application and channel driver.

While it's intended to be used like a Python module/library (see example), you can of course use the information
provided inside of the main file to make something more custom fit for your needs.

The creator of the Asterisk-side programs also made a library himself in Golang, which you
can find in the link to the original AudioSocket project above.


**PLEASE NOTE:** While AudioSocket is an absolutely excellent tool, and still one of the only (sorta) built-in ways to extract
raw audio stream of calls from Asterisk, a few oddities exist with how it works that I've encountered, and will explain in more detail below.


## Instructions

### Intro

*What does this allow me to do?*

AudioSocket, whether used as a channel driver or Dialplan application, behaves the same and has the primary purpose of
letting us access an Asterisk channel's incoming and outgoing audio stream and use it in externally for whatever, though unless attached via ChanSpy, it cannot be used to passively 'intercept' audio on a channel (it blocks execution in the Dialplan whenever its called).

You can also use it to trigger a hangup on the channel from within your program, that's about it signaling wise, but is is really all you need.


### Server usage

After placing the `audiosocket.py` file within your projects directory, you can start using it like this:

```python
from audiosocket import *

audiosocket = new_audiosocket()
audiosocket.start()
```

This would create a new audiosocket object in a separate thread, bind it to network interfaces 
on the computer using an open port (accessible via `audiosocket.port`) an start listening for incoming connections.

If you wanted to bind it to a specific address and/or port only, you could do this:

```python
audiosocket = new_audiosocket(addr='10.0.0.5', port=3278)
audisocket.start()
```

Internally, FIFO queue objects are used to send/receive audio, but to make usage as simple as possible, queues are created by default and hidden behind the `audiosocket.read()` and `audiosocket.write(<data>)` methods.
If you wanted to pass in your own though, you can do so like this:

```python
audiosocket = new_audiosocket(rx_audio_q = Queue(), tx_audio_q = Queue())
audiosocket.start()
```


To be continued
