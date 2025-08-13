# app.py  (CPU-optimized)
import os
import uuid
import traceback
from pathlib import Path
from typing import Tuple, Optional

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import torch

AUDIO_DIR = "static"
Path(AUDIO_DIR).mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
CORS(app)

DEVICE = "cpu"  # force CPU mode explicitly
print("[init] Running on CPU")

# -------------------------
# Optional libs detection
# -------------------------
try:
    import whisper as openai_whisper
    HAVE_WHISPER = True
    print("[init] openai/whisper available")
except Exception:
    HAVE_WHISPER = False
    print("[init] openai/whisper NOT available - install via 'pip install -U openai-whisper'")

try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    HAVE_TRANSFORMERS = True
    print("[init] transformers available")
except Exception:
    HAVE_TRANSFORMERS = False
    print("[init] transformers NOT available - install via 'pip install transformers sentencepiece'")

try:
    from gtts import gTTS
    HAVE_GTTS = True
    print("[init] gTTS available (will use for TTS)")
except Exception:
    HAVE_GTTS = False
    print("[init] gTTS NOT available - install via 'pip install gTTS'")

# optionally soundfile for saving wavs if you add Coqui later
try:
    import soundfile as sf
    HAVE_SOUNDFILE = True
except Exception:
    HAVE_SOUNDFILE = False

# -------------------------
# Model registry (lazy)
# -------------------------
MODEL_STORE = {
    "asr": None,    # whisper model (openai) - small by default
    "mt": None,     # m2m100 tokenizer+model
}

# choose CPU-friendly sizes
WHISPER_MODEL_NAME = "small"  # change to "medium" if you want slightly better accuracy and have CPU resources
MT_MODEL_NAME = "facebook/m2m100_418M"  # CPU-friendly general multilingual model

# -------------------------
# ASR helpers
# -------------------------
def load_asr():
    if MODEL_STORE["asr"] is not None:
        return MODEL_STORE["asr"]
    if not HAVE_WHISPER:
        raise RuntimeError("Whisper library not installed.")
    print(f"[load_asr] loading Whisper model '{WHISPER_MODEL_NAME}' (CPU). This may take a while...")
    model = openai_whisper.load_model(WHISPER_MODEL_NAME)  # runs on CPU by default when torch.device is CPU
    MODEL_STORE["asr"] = model
    print("[load_asr] loaded whisper model")
    return model

def transcribe_audio(filepath: str) -> Tuple[str, Optional[str]]:
    """
    Returns (transcription_text, detected_language_code)
    """
    model = load_asr()
    # whisper.transcribe will auto-detect language and return 'language'
    result = model.transcribe(filepath)
    text = result.get("text", "").strip()
    detected_lang = result.get("language", None)
    return text, detected_lang

# -------------------------
# MT helpers (M2M100)
# -------------------------
def load_mt():
    if MODEL_STORE["mt"] is not None:
        return MODEL_STORE["mt"]
    if not HAVE_TRANSFORMERS:
        raise RuntimeError("Transformers not installed.")
    print(f"[load_mt] loading MT model '{MT_MODEL_NAME}' (CPU). This will download weights if not cached.")
    tokenizer = AutoTokenizer.from_pretrained(MT_MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MT_MODEL_NAME)
    # keep on CPU
    MODEL_STORE["mt"] = {"tokenizer": tokenizer, "model": model}
    print("[load_mt] loaded MT model")
    return MODEL_STORE["mt"]

def translate_text_m2m100(text: str, source_lang: Optional[str], target_lang: str) -> str:
    """
    Translate using m2m100_418M. source_lang/target_lang are two-letter codes (e.g., 'en', 'hi', 'te').
    If source_lang is None or 'auto', we let the tokenizer/model handle it.
    """
    entry = load_mt()
    tokenizer = entry["tokenizer"]
    model = entry["model"]

    # Set tokenizer src_lang if we know it (tokenizer expects language codes like 'en', 'hi' etc.)
    if source_lang and source_lang != "auto":
        try:
            tokenizer.src_lang = source_lang
        except Exception:
            # some tokenizer versions allow setting this; ignore if not supported
            pass

    # encode and generate (CPU - smaller max_length)
    encoded = tokenizer(text, return_tensors="pt", truncation=True).to("cpu")
    # forced_bos_token_id expects language id. m2m100's tokenizer has method get_lang_id in some versions.
    forced_bos = None
    try:
        forced_bos = tokenizer.get_lang_id(target_lang)
    except Exception:
        # fallback: some transformers versions expect token like "<2en>" etc. Let generate without forced BOS if unavailable.
        forced_bos = None

    with torch.no_grad():
        if forced_bos is not None:
            out = model.generate(**encoded, forced_bos_token_id=forced_bos, max_length=512, num_beams=4)
        else:
            out = model.generate(**encoded, max_length=512, num_beams=4)
    translated = tokenizer.decode(out[0], skip_special_tokens=True)
    return translated

# -------------------------
# TTS helpers (gTTS fallback)
# -------------------------
def synthesize_tts_gtts(text: str, lang_code: str) -> str:
    if not HAVE_GTTS:
        raise RuntimeError("gTTS not installed (TTS unavailable).")
    filename = f"{uuid.uuid4().hex}.mp3"
    out_path = os.path.join(AUDIO_DIR, filename)
    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        tts.save(out_path)
        return out_path
    except Exception as e:
        # ensure no partial file left
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except:
                pass
        raise

# -------------------------
# Routes
# -------------------------
@app.route("/")
def home():
    return jsonify({"message": "CPU Speech-to-Speech Translator (Whisper small + m2m100_418M + gTTS)"}), 200

@app.route("/speech-to-speech", methods=["POST"])
def speech_to_speech():
    """
    multipart/form-data:
      - audio: file
      - target_language: required (e.g., 'hi', 'te', 'en')
      - optional: source_language ('auto' allowed)
    """
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        target_lang = (request.form.get("target_language") or request.args.get("target_language") or request.form.get("targetLanguage"))
        if not target_lang:
            return jsonify({"error": "target_language required (e.g. 'hi' for Hindi)"}), 400
        target_lang = target_lang.strip().lower()

        f = request.files["audio"]
        suffix = Path(f.filename).suffix or ".wav"
        in_name = f"input_{uuid.uuid4().hex}{suffix}"
        in_path = os.path.join(AUDIO_DIR, in_name)
        f.save(in_path)

        # 1) Transcribe (ASR)
        transcription, detected_lang = transcribe_audio(in_path)
        src_lang = (request.form.get("source_language") or request.args.get("source_language") or detected_lang or "auto")
        if src_lang == "auto":
            src_lang = detected_lang or "en"

        # 2) Translate (MT)
        # If source==target, skip translation
        if src_lang and src_lang != "auto" and src_lang == target_lang:
            translated_text = transcription
        else:
            translated_text = translate_text_m2m100(transcription, src_lang, target_lang)

        # 3) TTS (gTTS)
        # gTTS expects language codes like 'hi', 'en', 'te' - for some languages gTTS may not support them.
        try:
            tts_path = synthesize_tts_gtts(translated_text, target_lang)
        except Exception as e:
            # If gTTS fails for this language, fall back to English TTS to avoid complete failure
            try:
                tts_path = synthesize_tts_gtts(translated_text, "en")
            except Exception as e2:
                # cleanup input
                try:
                    os.remove(in_path)
                except:
                    pass
                return jsonify({"error": f"TTS failed: {str(e)} ; fallback failed: {str(e2)}"}), 500

        # remove input file (keep generated audio)
        try:
            os.remove(in_path)
        except:
            pass

        audio_route = f"/audio/{os.path.basename(tts_path)}"
        return jsonify({
            "transcription": transcription,
            "translated_text": translated_text,
            "audio_url": audio_route,
            "detected_source_language": src_lang
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/text-to-speech", methods=["POST"])
def text_to_speech():
    """
    JSON body:
      { "text": "...", "source_language": "en" | "auto", "target_language": "hi" }
    """
    try:
        data = request.get_json(force=True)
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"error": "text is required"}), 400
        target_lang = (data.get("target_language") or "").strip().lower()
        if not target_lang:
            return jsonify({"error": "target_language required (e.g., 'te')"}), 400
        source_lang = (data.get("source_language") or "auto").strip().lower()

        # If translation needed
        if source_lang and source_lang != "auto" and source_lang != target_lang:
            translated_text = translate_text_m2m100(text, source_lang, target_lang)
        elif source_lang == "auto":
            # best-effort: assume text is in English, and translate to target if target != en
            if target_lang != "en":
                translated_text = translate_text_m2m100(text, "en", target_lang)
            else:
                translated_text = text
        else:
            # no translation
            translated_text = text

        # Synthesize
        try:
            tts_path = synthesize_tts_gtts(translated_text, target_lang)
        except Exception as e:
            # fallback to English TTS
            try:
                tts_path = synthesize_tts_gtts(translated_text, "en")
            except Exception as e2:
                return jsonify({"error": f"TTS failed: {str(e)} ; fallback failed: {str(e2)}"}), 500

        audio_route = f"/audio/{os.path.basename(tts_path)}"
        return jsonify({"translated_text": translated_text, "audio_url": audio_route}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename, as_attachment=False)

if __name__ == "__main__":
    # debug True while developing; change to False in production
    app.run(debug=True, host="0.0.0.0", port=5000)
