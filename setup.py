#!/usr/bin/env python
from distutils.core import setup

setup(
  name = 'audiosocket',
  version = '0.7',
  author = 'anatoly techtonik',
  author_email = 'techtonik@gmail.com',
  description = 'Raw Audio Socket player in pure Python',
  long_description = """
Implementation of Raw Audio Socket server spec in pure Python.

| Author:  anatoly techtonik <techtonik@gmail.com>
| License: Public Domain (or MIT if a license is required)

http://code.google.com/p/rainforce/wiki/RawAudioSocket

""",
  license = 'Public Domain',
  url='http://bitbucket.org/techtonik/audiosocket',
  classifiers=[
        'License :: Public Domain',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Multimedia :: Sound/Audio',
  ],

  py_modules=['audiosocket'],
)
