
import ossaudiodev as oss

audio = oss.open('w')
audio.setfmt(oss.AFMT_S16_LE)
audio.channels(2)
audio.speed(44100)
audio.writeall(open('sample.raw', 'rb').read())
audio.close()

