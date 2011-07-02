"""
Implementation of Raw Audio Socket server spec in pure Python
http://code.google.com/p/rainforce/wiki/RawAudioSocket

"""


#-- CHAPTER 1: CONTINUOUS SOUND PLAYBACK WITH WINDOWS WINMM LIBRARY --
#
# Based on tutorial "Playing Audio in Windows using waveOut Interface"
# by David Overton

import ctypes

# 1. Open Sound Device

# mmsystem.h
from ctypes import wintypes

HWAVEOUT = wintypes.HANDLE


#-- /CHAPTER 1 --
