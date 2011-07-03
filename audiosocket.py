"""
Implementation of Raw Audio Socket server spec in pure Python
http://code.google.com/p/rainforce/wiki/RawAudioSocket

"""

import sys

#-- CHAPTER 1: CONTINUOUS SOUND PLAYBACK WITH WINDOWS WINMM LIBRARY --
#
# Based on tutorial "Playing Audio in Windows using waveOut Interface"
# by David Overton

import ctypes
from ctypes import wintypes

winmm = ctypes.windll.winmm


# 1. Open Sound Device

# --- define necessary data structures from mmsystem.h
HWAVEOUT = wintypes.HANDLE
WAVE_FORMAT_PCM = 0x1
WAVE_MAPPER = -1
CALLBACK_NULL = 0
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
# --- /define

# Data must be processes in pieces that are multiple of
# nBlockAlign bytes of data at a time. Written and read
# data from a device must always start at the beginning
# of a block. Playback of PCM data can not be started in
# the middle of a sample on a non-block-aligned boundary.

hwaveout = HWAVEOUT()
wavefx = WAVEFORMATEX(
  WAVE_FORMAT_PCM,
  2,     # nChannels
  44100, # SamplesPerSec
  705600,# AvgBytesPerSec = 44100 SamplesPerSec * 16 wBitsPerSample
  4,     # nBlockAlign = 2 nChannels * 16 wBitsPerSample / 8 bits per byte
  16,    # wBitsPerSample
  0
)

# Open default wave device
ret = winmm.waveOutOpen(
  ctypes.byref(hwaveout), # buffer to receive a handle identifying
                          # the open waveform-audio output device
  WAVE_MAPPER,            # constant to point to default wave device
  ctypes.byref(wavefx),   # identifier for data format sent for device
  0, # DWORD_PTR dwCallback - callback mechanizm
  0, # DWORD_PTR dwCallbackInstance - user instance data for callback
  CALLBACK_NULL # DWORD fdwOpen - flag for opening the device
)

if ret != MMSYSERR_NOERROR:
  sys.exit('Error opening default waveform audio device (WAVE_MAPPER)')

print "Default Wave Audio output device is opened successfully"


# 2. Write Audio Blocks to Device

# --- define necessary data structures
PVOID = wintypes.HANDLE
WAVERR_BASE = 32
WAVERR_STILLPLAYING = WAVERR_BASE + 1
class WAVEHDR(ctypes.Structure):
  _fields_ = [
    ('lpData', wintypes.LPSTR), # pointer to waveform buffer
    ('dwBufferLength', wintypes.DWORD),  # in bytes
    ('dwBytesRecorded', wintypes.DWORD), # when used in input
    ('dwUser', wintypes.DWORD),          # user data
    ('dwFlags', wintypes.DWORD),
    ('dwLoops', wintypes.DWORD),  # times to loop, for output buffers only
    ('lpNext', PVOID),            # reserved, struct wavehdr_tag *lpNext
    ('reserved', wintypes.DWORD)] # reserved
# The lpData, dwBufferLength, and dwFlags members must be set before calling
# the waveInPrepareHeader or waveOutPrepareHeader function. (For either
# function, the dwFlags member must be set to zero.)
# --- /define

class AudioWriter(object):
  def __init__(self, hwaveout):
    self.hwaveout = hwaveout
    self.wavehdr = WAVEHDR()

  def play(self, data):
    """Write PCM audio data block to the output device"""
    self.wavehdr.dwBufferLength = len(data)
    self.wavehdr.lpData = data
    
    # Prepare block for playback
    if winmm.waveOutPrepareHeader(
         self.hwaveout, ctypes.byref(self.wavehdr), ctypes.sizeof(self.wavehdr)
       ) != MMSYSERR_NOERROR:
      sys.exit('Error: waveOutPrepareHeader failed')

    # Write block, returns immediately unless a synchronous driver is
    # used (not often)
    if winmm.waveOutWrite(
         self.hwaveout, ctypes.byref(self.wavehdr), ctypes.sizeof(self.wavehdr)
       ) != MMSYSERR_NOERROR:
      sys.exit('Error: waveOutWrite failed')

    # Wait until playback is finished
    while True:
      # unpreparing the header fails until the block is played
      ret = winmm.waveOutUnprepareHeader(
              self.hwaveout,
              ctypes.byref(self.wavehdr),
              ctypes.sizeof(self.wavehdr)
            )
      if ret == WAVERR_STILLPLAYING:
        continue
      if ret != MMSYSERR_NOERROR:
        sys.exit('Error: waveOutUnprepareHeader failed with code 0x%x' % ret)
      break


aw = AudioWriter(hwaveout)

df = open('95672__Corsica_S__frequency_change_approved.raw', 'rb')
while True:
  data = df.read(100000)
  if len(data) == 0:
    break
  aw.play(data)
df.close()

# x. Close Sound Device

winmm.waveOutClose(hwaveout)
print "Default Wave Audio output device is closed"

#-- /CHAPTER 1 --
