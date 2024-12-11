# assistant/utils.py
import openai
import sounddevice as sd
import numpy as np
from scipy.io import wavfile
import tempfile
import pyttsx3
import os
import threading

class VoiceAssistant:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.history = [
            {"role": "system", "content": "You are a helpful assistant. The user is English. Only speak English."}
        ]

    def listen(self, file_path=None):
        if file_path is None:
            # Record audio if no file path is provided
            duration = 3  # Record for 3 seconds
            fs = 44100  # Sample rate

            audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype=np.int16)
            sd.wait()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav_file:
                wavfile.write(temp_wav_file.name, fs, audio)
                file_path = temp_wav_file.name

        with open(file_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file
            )

        return transcript['text']

    def think(self, text):
        self.history.append({"role": "user", "content": text})
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=self.history,
            temperature=0.5
        )
        message = dict(response.choices[0])['message']['content']
        self.history.append({"role": "system", "content": message})
        return message

    def speak(self, text):
        def run_speech():
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()

        # Run the speech in a separate thread
        thread = threading.Thread(target=run_speech)
        thread.start()

