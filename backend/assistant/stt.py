"""Speech to text with Whisper on Groq (the same API key as the chat)."""
from groq import Groq


def transcribe(audio, names):
    result = Groq().audio.transcriptions.create(
        file=(audio.name, audio.read()),
        model="whisper-large-v3-turbo",
        language="en",
        prompt=f"Names: {', '.join(names)}.",  # helps Whisper spell the group's names ("Ankit", not "Unket")
    )
    return result.text.strip()
