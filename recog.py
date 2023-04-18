import speech_recognition as sr
import subprocess

fileNumber = input("Masukkan nomor file: ")

audionameMp3 = "track"+fileNumber+".mp3"
audionameWav = "track"+fileNumber+".wav"
subprocess.call(['ffmpeg', '-i', audionameMp3, audionameWav])
#subprocess.call(['ffmpeg', '-i', "track11.mp3", "track11.mav"])

txtname = "track"+fileNumber+".txt"

r = sr.Recognizer()
with sr.AudioFile(audionameWav) as source:
    audio_data = r.record(source)
    text = r.recognize_google(audio_data,language='id-ID')
    print(text)

with open(txtname, 'w') as f:
    f.write(text)