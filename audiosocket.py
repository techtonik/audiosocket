"""
Implementation of Raw Audio Socket server spec in pure Python
http://code.google.com/p/rainforce/wiki/RawAudioSocket

"""


#-- CHAPTER 1: CONTINUOUS SOUND PLAYBACK WITH WINDOWS WINMM LIBRARY --
#
# Based on tutorial "Playing Audio in Windows using waveOut Interface"
# by David Overton

import ctypes
from ctypes import wintypes

# 1. Open Sound Device

# --- define necessary data structures from mmsystem.h
HWAVEOUT = wintypes.HANDLE
WAVE_FORMAT_PCM = 0x1
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

wavefx = WAVEFORMATEX(
  WAVE_FORMAT_PCM,
  2,     # nChannels
  44100, # SamplesPerSec
  705600,# AvgBytesPerSec = 44100 SamplesPerSec * 16 wBitsPerSample
  4,     # nBlockAlign = 2 nChannels * 16 wBitsPerSample / 8 bits per byte
  16,    # wBitsPerSample
  0
)

#-- /CHAPTER 1 --
