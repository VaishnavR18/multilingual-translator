from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import torch
import whisper
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForSequenceClassification, pipeline
from TTS.api import TTS  # Coqui TTS

app = Flask(__name__)
CORS(app)

AUDIO_DIR = 'static'
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Language Detection Model
lang_detect_model_name = "papluca/xlm-roberta-base-language-detection"
lang_detect_tokenizer = AutoTokenizer.from_pretrained(lang_detect_model_name)
lang_detect_model = AutoModelForSequenceClassification.from_pretrained(lang_detect_model_name).to(device)
lang_detect_pipeline = pipeline("text-classification", model=lang_detect_model, tokenizer=lang_detect_tokenizer, device=0 if device.type == 'cuda' else -1)

# Translation Model
translation_model_name = "facebook/m2m100_418M"
translation_tokenizer = AutoTokenizer.from_pretrained(translation_model_name)
translation_model = AutoModelForSeq2SeqLM.from_pretrained(translation_model_name).to(device)

# Speech to Text Model (Whisper)
stt_model = whisper.load_model("small")

# Text to Speech Model (Coqui TTS)
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

# Helper Functions

def detect_language(text):
    preds = lang_detect_pipeline(text)
    if preds and len(preds) > 0:
        return preds[0]['label']
    return None

def translate_text(text, source_lang, target_lang):
    # m2m100 expects lowercase language codes like 'en', 'hi', etc.
    translation_tokenizer.src_lang = source_lang
    encoded = translation_tokenizer(text, return_tensors="pt").to(device)
    generated_tokens = translation_model.generate(
        **encoded, forced_bos_token_id=translation_tokenizer.get_lang_id(target_lang)
    )
    return translation_tokenizer.decode(generated_tokens[0], skip_special_tokens=True)

def text_to_speech(text):
    audio_path = os.path.join(AUDIO_DIR, f"{uuid.uuid4().hex}.wav")
    tts.tts_to_file(text=text, file_path=audio_path)
    return audio_path

# Flask Routes

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the AI-Powered Language Translator"}), 200

@app.route('/translate', methods=['POST'])
def translate():
    try:
        data = request.json
        source_language = data.get('source_language')
        target_language = data.get('target_language')
        text = data.get('text')

        if not target_language or not text:
            return jsonify({"error": "Missing required parameters"}), 400

        # Auto detect source language if missing or "auto"
        if not source_language or source_language == "auto":
            source_language = detect_language(text)
            if not source_language:
                return jsonify({"error": "Could not detect source language"}), 400

        # Translate text
        translated_text = translate_text(text, source_language, target_language)

        # Generate TTS audio file
        audio_path = text_to_speech(translated_text)
        audio_filename = os.path.basename(audio_path)

        return jsonify({
            "translated_text": translated_text,
            "audio_url": f"/audio/{audio_filename}",
            "detected_source_language": source_language
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/speech-to-text', methods=['POST'])
def speech_to_text():
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files['audio']
        temp_audio_path = os.path.join(AUDIO_DIR, f"input_{uuid.uuid4().hex}.wav")
        audio_file.save(temp_audio_path)

        # Use whisper to transcribe
        result = stt_model.transcribe(temp_audio_path)
        transcription = result['text']

        # Clean up temp audio file
        os.remove(temp_audio_path)

        return jsonify({"transcription": transcription})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True)
