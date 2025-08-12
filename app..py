# app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import torch
import whisper
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from gtts import gTTS   # lightweight, reliable TTS fallback
import tempfile

app = Flask(__name__)
CORS(app)

AUDIO_DIR = "static"
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)

# ------------ Speech-to-text (Whisper) ------------
# Make sure you have ffmpeg installed on your system (whisper uses it).
stt_model = whisper.load_model("small")  # choose small/medium depending on resources

# ------------ Translation model (Hugging Face M2M100) ------------
# This model supports many-to-many translations without English pivot.
translation_model_name = "facebook/m2m100_418M"
translation_tokenizer = AutoTokenizer.from_pretrained(translation_model_name)
translation_model = AutoModelForSeq2SeqLM.from_pretrained(translation_model_name).to(device)

# helper: map some common frontend language codes to M2M100 IDs if necessary
# (M2M100 expects codes like "en", "hi", "fr" etc. get_lang_id will map known codes)
# We'll rely on direct two-letter codes. Add mapping if you use different codes.

# ------------ Helper functions ------------
def transcribe_audio(filepath):
    # whisper returns 'text' and can auto-detect language
    result = stt_model.transcribe(filepath)
    transcription = result.get("text", "")
    detected_lang = result.get("language", None)  # whisper may include language
    return transcription.strip(), detected_lang

def translate_text_m2m100(text, source_lang, target_lang):
    # If source_lang is None or 'auto', we attempt to set tokenizer src_lang when we know it.
    if source_lang and source_lang != "auto":
        translation_tokenizer.src_lang = source_lang
    # encode and generate
    encoded = translation_tokenizer(text, return_tensors="pt").to(device)
    forced_bos = translation_tokenizer.get_lang_id(target_lang)
    generated = translation_model.generate(**encoded, forced_bos_token_id=forced_bos, max_length=2048)
    translated = translation_tokenizer.decode(generated[0], skip_special_tokens=True)
    return translated

def synthesize_tts_gtts(text, lang_code):
    # gTTS supports many languages; lang_code should be e.g. 'hi' for Hindi
    tts = gTTS(text=text, lang=lang_code, slow=False)
    filename = f"{uuid.uuid4().hex}.mp3"
    out_path = os.path.join(AUDIO_DIR, filename)
    tts.save(out_path)
    return out_path

# If you want to use Coqui/ESPnet/other HF TTS: install those packages and replace synthesize_tts_gtts
# Example (commented): use TTS from coqui if available:
# from TTS.api import TTS
# tts_engine = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")  # example
# then tts_engine.tts_to_file(text=text, file_path=out_path)

# ------------ Routes ------------
@app.route("/")
def home():
    return jsonify({"message": "Speech-to-Speech Translator API"}), 200

@app.route("/speech-to-speech", methods=["POST"])
def speech_to_speech():
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        target_lang = request.form.get("target_language") or request.args.get("target_language") or request.form.get("targetLanguage")
        if not target_lang:
            return jsonify({"error": "target_language required (e.g. 'hi' for Hindi)"}), 400

        audio_file = request.files["audio"]
        suffix = os.path.splitext(audio_file.filename)[1] or ".wav"

        # save incoming audio to a temporary file (whisper needs a file path)
        tmp_in = os.path.join(AUDIO_DIR, f"input_{uuid.uuid4().hex}{suffix}")
        audio_file.save(tmp_in)

        # 1) STT
        transcription, detected_lang = transcribe_audio(tmp_in)

        # if whisper didn't detect language, you could run an HF language-id pipeline here
        source_lang = detected_lang if detected_lang else "auto"

        # 2) Translate (M2M100)
        translated_text = translate_text_m2m100(transcription, source_lang, target_lang)

        # 3) TTS -> using gTTS (reliable fallback)
        tts_path = synthesize_tts_gtts(translated_text, target_lang)

        # Return relative audio url path for frontend to play (Flask serve from /audio/<filename>)
        audio_route = f"/audio/{os.path.basename(tts_path)}"

        # cleanup input file
        try:
            os.remove(tmp_in)
        except:
            pass

        return jsonify({
            "transcription": transcription,
            "translated_text": translated_text,
            "audio_url": audio_route,
            "detected_source_language": source_lang
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename, as_attachment=False)

if __name__ == "__main__":
    # If you need network access from other devices, use host='0.0.0.0'
    app.run(debug=True)
