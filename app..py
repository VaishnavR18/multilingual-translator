# app.py  -- CPU-friendly, uses faster-whisper (if available) for ASR
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

DEVICE = "cpu"
print("[init] Running on CPU (DEVICE =", DEVICE, ")")

# -------------------------
# Optional libs detection
# -------------------------
# Prefer faster-whisper for speed on CPU (with int8 quant)
HAVE_FASTER_WHISPER = False
HAVE_WHISPER = False
try:
    from faster_whisper import WhisperModel
    HAVE_FASTER_WHISPER = True
    print("[init] faster-whisper available (preferred for CPU ASR)")
except Exception:
    print("[init] faster-whisper NOT available (install via 'pip install faster-whisper')")

try:
    import whisper as openai_whisper
    HAVE_WHISPER = True
    print("[init] openai/whisper available (fallback ASR)")
except Exception:
    print("[init] openai/whisper NOT available - install via 'pip install -U openai-whisper'")

try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    HAVE_TRANSFORMERS = True
    print("[init] transformers available (MT)")
except Exception:
    HAVE_TRANSFORMERS = False
    print("[init] transformers NOT available - install via 'pip install transformers sentencepiece'")

try:
    from gtts import gTTS
    HAVE_GTTS = True
    print("[init] gTTS available (TTS fallback)")
except Exception:
    HAVE_GTTS = False
    print("[init] gTTS NOT available - install via 'pip install gTTS'")

try:
    import soundfile as sf
    HAVE_SOUNDFILE = True
except Exception:
    HAVE_SOUNDFILE = False

# -------------------------
# Model registry (lazy)
# -------------------------
MODEL_STORE = {
    "asr": None,    # WhisperModel (faster-whisper) or openai whisper model
    "mt": None,
}

# CPU-friendly choices (you can change)
# For faster-whisper, available model names: "small", "medium", etc. The 'small' family runs faster.
WHISPER_FAST_MODEL = "small"  # faster-whisper model name (small/medium)
# For openai-whisper fallback use "small" as well
WHISPER_OPENAI_NAME = "small"

MT_MODEL_NAME = "facebook/m2m100_418M"  # existing multilingual model (keeps compatibility)

# -------------------------
# ASR helpers (faster-whisper preferred)
# -------------------------
def load_asr():
    """Load either faster-whisper WhisperModel or openai whisper model (lazy)."""
    if MODEL_STORE["asr"] is not None:
        return MODEL_STORE["asr"]

    if HAVE_FASTER_WHISPER:
        print(f"[load_asr] loading faster-whisper model '{WHISPER_FAST_MODEL}' (cpu, int8).")
        # compute_type int8 quantized model for CPU
        model = WhisperModel(WHISPER_FAST_MODEL, device="cpu", compute_type="int8")
        MODEL_STORE["asr"] = ("faster", model)
        print("[load_asr] loaded faster-whisper model")
        return MODEL_STORE["asr"]

    if HAVE_WHISPER:
        print(f"[load_asr] loading openai whisper model '{WHISPER_OPENAI_NAME}' (CPU).")
        model = openai_whisper.load_model(WHISPER_OPENAI_NAME)
        MODEL_STORE["asr"] = ("openai", model)
        print("[load_asr] loaded openai whisper model")
        return MODEL_STORE["asr"]

    raise RuntimeError("No ASR backend available. Install faster-whisper or openai-whisper.")

def transcribe_audio(filepath: str) -> Tuple[str, Optional[str]]:
    """
    Returns (transcription_text, detected_language_code)
    Uses faster-whisper if available, otherwise openai whisper.
    """
    backend, model = load_asr()
    if backend == "faster":
        # faster-whisper returns segments and info
        # We will join segments into text and return info.language if present
        segments, info = model.transcribe(filepath, beam_size=5)
        full_text = "".join([segment.text for segment in segments]).strip()
        detected_lang = getattr(info, "language", None)
        # faster-whisper language codes are typically like 'en' etc.
        return full_text, detected_lang
    else:
        # openai whisper fallback
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
    print(f"[load_mt] loading MT model '{MT_MODEL_NAME}' (CPU). This may download weights if not cached.")
    tokenizer = AutoTokenizer.from_pretrained(MT_MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MT_MODEL_NAME)
    MODEL_STORE["mt"] = {"tokenizer": tokenizer, "model": model}
    print("[load_mt] loaded MT model")
    return MODEL_STORE["mt"]

def translate_text_m2m100(text: str, source_lang: Optional[str], target_lang: str) -> str:
    """
    Translate using m2m100_418M.
    source_lang/target_lang are two-letter codes (e.g., 'en','hi'). For best results, pass known codes.
    """
    entry = load_mt()
    tokenizer = entry["tokenizer"]
    model = entry["model"]

    # set src_lang if given
    if source_lang and source_lang != "auto":
        try:
            tokenizer.src_lang = source_lang
        except Exception:
            pass

    encoded = tokenizer(text, return_tensors="pt", truncation=True).to("cpu")
    forced_bos = None
    try:
        forced_bos = tokenizer.get_lang_id(target_lang)
    except Exception:
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
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except:
                pass
        raise

# NOTE: if you want to use Coqui TTS offline, you can implement a synthesize_tts_coqui(text, lang)
# using the TTS package (pip install TTS) and choose a small multilingual model.
# I left gTTS as default because it's lightweight and reliable.

# -------------------------
# Routes (same contract as before)
# -------------------------
@app.route("/")
def home():
    return jsonify({"message": "CPU Speech-to-Speech Translator (faster-whisper + m2m100_418M + gTTS)"}), 200

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
        if src_lang and src_lang != "auto" and src_lang == target_lang:
            translated_text = transcription
        else:
            translated_text = translate_text_m2m100(transcription, src_lang, target_lang)

        # 3) TTS (gTTS)
        try:
            tts_path = synthesize_tts_gtts(translated_text, target_lang)
        except Exception as e:
            # fallback to English TTS
            try:
                tts_path = synthesize_tts_gtts(translated_text, "en")
            except Exception as e2:
                try:
                    os.remove(in_path)
                except:
                    pass
                return jsonify({"error": f"TTS failed: {str(e)} ; fallback failed: {str(e2)}"}), 500

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
            translated_text = text

        # Synthesize
        try:
            tts_path = synthesize_tts_gtts(translated_text, target_lang)
        except Exception as e:
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
