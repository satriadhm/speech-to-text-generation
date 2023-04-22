import speech_recognition as sr
import subprocess

fileNumber = input("Masukkan nomor file: ")

audionameMp3 = "Track "+fileNumber+".mp3"
audionameWav = "Track "+fileNumber+".wav"
subprocess.call(['ffmpeg', '-i', audionameMp3, audionameWav])

txtname = "track"+fileNumber+".txt"

r = sr.Recognizer()
r.dynamic_energy_threshold = True
with sr.AudioFile(audionameWav) as source:
    audio_data = r.record(source)
    text = r.recognize_google(audio_data, language='id-ID')
    print(text)

with open(txtname, 'w') as f:
    f.write(text)
