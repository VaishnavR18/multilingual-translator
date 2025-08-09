from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from gtts import gTTS
import os
import uuid
import mediapipe as mp
import cv2
import numpy as np

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Your Google Cloud Translation API Key
API_KEY = 'AIzaSyDzWV9tf1tKCaQGWnScP9UpzGvjJdbE-4M'

# Directory to store the audio file
AUDIO_DIR = 'static'

# Ensure the audio directory exists
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

# Language mapping
LANGUAGE_MAPPING = {
    "af": "Afrikaans",
    "sq": "Albanian",
    "ar": "Arabic",
    "hy": "Armenian",
    "bn": "Bengali",
    "bs": "Bosnian",
    "ca": "Catalan",
    "hr": "Croatian",
    "cs": "Czech",
    "da": "Danish",
    "nl": "Dutch",
    "en": "English",
    "eo": "Esperanto",
    "et": "Estonian",
    "tl": "Filipino",
    "fi": "Finnish",
    "fr": "French",
    "de": "German",
    "el": "Greek",
    "gu": "Gujarati",
    "hi": "Hindi",
    "hu": "Hungarian",
    "is": "Icelandic",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "jw": "Javanese",
    "kn": "Kannada",
    "km": "Khmer",
    "ko": "Korean",
    "la": "Latin",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "ml": "Malayalam",
    "mr": "Marathi",
    "my": "Myanmar (Burmese)",
    "ne": "Nepali",
    "no": "Norwegian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sr": "Serbian",
    "si": "Sinhala",
    "sk": "Slovak",
    "sl": "Slovenian",
    "es": "Spanish",
    "su": "Sundanese",
    "sw": "Swahili",
    "sv": "Swedish",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "cy": "Welsh",
    "xh": "Xhosa",
    "yi": "Yiddish",
    "zu": "Zulu"
}

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Language Translator"}), 200

# 📝 **TEXT TRANSLATION API**
@app.route('/translate', methods=['POST'])
def translate_text():
    try:
        data = request.json
        source_language = data.get('source_language')
        target_language = data.get('target_language')
        text_to_translate = data.get('text')

        if not source_language or not target_language or not text_to_translate:
            return jsonify({"error": "Missing required parameters"}), 400

        url = f"https://translation.googleapis.com/language/translate/v2?key={API_KEY}"
        payload = {
            'q': text_to_translate,
            'source': source_language,
            'target': target_language,
            'format': 'text'
        }

        response = requests.post(url, json=payload)
        result = response.json()

        if 'data' in result:
            print("🔍 Translation Response:", result)
            translated_text = result['data']['translations'][0]['translatedText']

            # Generate TTS audio
            audio_filename = f"translated_audio_{uuid.uuid4().hex}.mp3"
            audio_path = os.path.join(AUDIO_DIR, audio_filename)
            tts = gTTS(translated_text, lang=target_language)
            tts.save(audio_path)

            return jsonify({
                "translated_text": translated_text,
                "audio_url": f"/audio/{audio_filename}"
            })
        else:
            return jsonify({"error": "Translation failed"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔊 **SERVE AUDIO FILES**
@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)


if __name__ == '__main__':
    app.run(debug=True)
