import logging
import pyttsx3
from gtts import gTTS
log = logging.getLogger("BMH")

def speak_text(text):
    """Initializes TTS engine and speaks the provided text."""
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.say(text)
    engine.runAndWait()

def play_station_message(filename, station_id_module):
    """Helper to fetch and speak a station message."""
    message = station_id_module.get_station_text(filename)
    if not message.startswith("Error"):
        speak_text(message)
    else:
        print(message)

def produce_wav_file(text, output_filename):
    """Generates an audio file from text."""
    tts = gTTS(text=text, lang='en')
    tts.save(output_filename)
