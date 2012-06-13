"""
Implementation of Raw Audio Socket server spec in pure Python
http://code.google.com/p/rainforce/wiki/RawAudioSocket

Public domain work by anatoly techtonik <techtonik@gmail.com>
Use MIT License if public domain doesn't make sense for you.


Change History:

0.1 - proof of concept, loads and plays entire data file in
      one turn, uses predefined sleep interval of one second to
      avoid 100% CPU usage when checking if playback is complete
0.2 - loads data piece by piece, plays with noticeable lags due
      to the absence of buffering, 100% CPU usage, because sleep
      interval is undefined
0.3 - organize code into AudioWriter class
0.4 - playback lag is killed by double buffering, still 100% CPU
      usage because of constant polling to check for processed
      blocks
0.5 - remove 100% CPU usage by sleeping while a block is playing
"""

import sys
import time

DEBUG = False
def debug(msg):
  if DEBUG:
    print "debug: %s" % msg

#-- CHAPTER 1: CONTINUOUS SOUND PLAYBACK WITH WINDOWS WINMM LIBRARY --
#
# Based on tutorial "Playing Audio in Windows using waveOut Interface"
# by David Overton

import ctypes
from ctypes import wintypes

winmm = ctypes.windll.winmm

# --- define necessary data structures from mmsystem.h

# 1. Open Sound Device

HWAVEOUT = wintypes.HANDLE
WAVE_FORMAT_PCM = 0x1
WAVE_MAPPER = -1
MMSYSERR_NOERROR = 0

class WAVEFORMATEX(ctypes.Structure):
  _fields_ = [
    ('wFormatTag',  wintypes.WORD),
      # 0x0001	WAVE_FORMAT_PCM. PCM audio
      # 0xFFFE	The format is specified in the WAVEFORMATEXTENSIBLE.SubFormat
      # Other values are in mmreg.h 
    ('nChannels',   wintypes.WORD),
    ('SamplesPerSec',  wintypes.DWORD),
    ('AvgBytesPerSec', wintypes.DWORD),
      # for WAVE_FORMAT_PCM is the product of nSamplesPerSec and nBlockAlign
    ('nBlockAlign', wintypes.WORD),
      # for WAVE_FORMAT_PCM is the product of nChannels and wBitsPerSample
      # divided by 8 (bits per byte)
    ('wBitsPerSample', wintypes.WORD),
      # for WAVE_FORMAT_PCM should be equal to 8 or 16
    ('cbSize',      wintypes.WORD)]
      # extra format information size, should be 0

# Data must be processes in pieces that are multiple of
# nBlockAlign bytes of data at a time. Written and read
# data from a device must always start at the beginning
# of a block. Playback of PCM data can not be started in
# the middle of a sample on a non-block-aligned boundary.

CALLBACK_NULL = 0

# 2. Write Audio Blocks to Device

PVOID = wintypes.HANDLE
WAVERR_BASE = 32
WAVERR_STILLPLAYING = WAVERR_BASE + 1
class WAVEHDR(ctypes.Structure):
  _fields_ = [
    ('lpData', wintypes.LPSTR), # pointer to waveform buffer
    ('dwBufferLength', wintypes.DWORD),  # in bytes
    ('dwBytesRecorded', wintypes.DWORD), # when used in input
    ('dwUser', wintypes.DWORD),          # user data
    ('dwFlags', wintypes.DWORD),  # various WHDR_* flags set by Windows
    ('dwLoops', wintypes.DWORD),  # times to loop, for output buffers only
    ('lpNext', PVOID),            # reserved, struct wavehdr_tag *lpNext
    ('reserved', wintypes.DWORD)] # reserved
# The lpData, dwBufferLength, and dwFlags members must be set before calling
# the waveInPrepareHeader or waveOutPrepareHeader function. (For either
# function, the dwFlags member must be set to zero.)
WHDR_DONE = 1  # Set by the device driver for finished buffers
# --- /define ----------------------------------------


# -- Notes on double buffering scheme to avoid lags --
#
# Windows maintains a queue of blocks sheduled for playback.
# Any block passed through the waveOutPrepareHeader function
# is inserted into the queue with waveOutWrite.

class AudioWriter(object):
  def __init__(self):
    self.hwaveout = HWAVEOUT()
    self.wavefx = WAVEFORMATEX(
      WAVE_FORMAT_PCM,
      2,     # nChannels
      44100, # SamplesPerSec
      176400,# AvgBytesPerSec = 44100 SamplesPerSec * 4 nBlockAlign
      4,     # nBlockAlign = 2 nChannels * 16 wBitsPerSample / 8 bits per byte
      16,    # wBitsPerSample
      0
    )
    # For gapless playback, we schedule two audio blocks at a time, each
    # block with its own header
    self.headers = [WAVEHDR(), WAVEHDR()]

    #: configurable size of chunks (data blocks) read from input stream
    self.BUFSIZE = 100 * 2**10

    # Buffer playback time. The time after which the buffer is free
    self.BUFPLAYTIME = float(self.BUFSIZE) / 176400  # AvgBytesPerSec

  def open(self):
    """ 1. Open default wave device, tune it for the incoming data flow
    """
    ret = winmm.waveOutOpen(
      ctypes.byref(self.hwaveout), # buffer to receive a handle identifying
                              # the open waveform-audio output device
      WAVE_MAPPER,            # constant to point to default wave device
      ctypes.byref(self.wavefx),   # identifier for data format sent for device
      0, # DWORD_PTR dwCallback - callback function
      0, # DWORD_PTR dwCallbackInstance - user instance data for callback
      CALLBACK_NULL  # DWORD fdwOpen - flag for opening the device
    )

    if ret != MMSYSERR_NOERROR:
      sys.exit('Error opening default waveform audio device (WAVE_MAPPER)')

    debug( "Default Wave Audio output device is opened successfully" )

  def _schedule_block(self, data, header):
    """Schedule PCM audio data block for playback. header parameter
       references free WAVEHDR structure to be used for scheduling."""
    header.dwBufferLength = len(data)
    header.lpData = data

    # Prepare block for playback
    if winmm.waveOutPrepareHeader(
         self.hwaveout, ctypes.byref(header), ctypes.sizeof(header)
       ) != MMSYSERR_NOERROR:
      sys.exit('Error: waveOutPrepareHeader failed')

    # Write block, returns immediately unless a synchronous driver is
    # used (not often)
    if winmm.waveOutWrite(
         self.hwaveout, ctypes.byref(header), ctypes.sizeof(header)
       ) != MMSYSERR_NOERROR:
      sys.exit('Error: waveOutWrite failed')

  def play(self, stream):
    """Read PCM audio blocks from stream and write to the output device"""

    blocknum = len(self.headers) #: number of audio data blocks to be queued
    curblock = 0      #: start with block 0
    stopping = False  #: stopping playback when no input
    while True:
      freeids = [x for x in xrange(blocknum)
                   if self.headers[x].dwFlags in (0, WHDR_DONE)]
      if (len(freeids) == blocknum) and stopping:
        break
      debug("empty blocks %s" % freeids)

      # Fill audio queue
      for i in freeids:
        if stopping:
          break
        debug("scheduling block %d" % i)
        data = stream.read(self.BUFSIZE)
        if len(data) == 0:
          stopping = True
          break
        self._schedule_block(data, self.headers[i])

      debug("waiting for block %d" % curblock)

      # waiting until buffer playback is finished by constantly polling
      # its status eats 100% CPU time. this counts how many checks are made
      pollsnum = 0
      # avoid 100% CPU usage - with this pollsnum won't be greater than 1
      time.sleep(self.BUFPLAYTIME)

      while True:
        pollsnum += 1
        # unpreparing the header fails until the block is played
        ret = winmm.waveOutUnprepareHeader(
                self.hwaveout,
                ctypes.byref(self.headers[curblock]),
                ctypes.sizeof(self.headers[curblock])
              )
        if ret == WAVERR_STILLPLAYING:
          continue
        if ret != MMSYSERR_NOERROR:
          sys.exit('Error: waveOutUnprepareHeader failed with code 0x%x' % ret)
        break
      debug("  %s check(s)" % pollsnum)

      # Switch waiting pointer to the next block
      curblock = (curblock + 1) % len(self.headers)

  def close(self):
    """ x. Close Sound Device """
    winmm.waveOutClose(self.hwaveout)
    debug( "Default Wave Audio output device is closed" )



if __name__ == '__main__':
  aw = AudioWriter()
  aw.open()

  df = open('95672__Corsica_S__frequency_change_approved.raw', 'rb')
  aw.play(df)
  df.close()

  aw.close()

#-- /CHAPTER 1 --
