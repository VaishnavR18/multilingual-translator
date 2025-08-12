import React, { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { FaMicrophone, FaVolumeUp, FaTrash, FaUpload, FaStop } from "react-icons/fa";
import "./TranslatorPage.css";

const TranslatorPage = () => {
  const [text, setText] = useState("");
  const [translatedText, setTranslatedText] = useState("");
  const [displayedText, setDisplayedText] = useState(""); 
  const [sourceLanguage, setSourceLanguage] = useState("auto");
  const [targetLanguage, setTargetLanguage] = useState("hi");
  const [isTranslating, setIsTranslating] = useState(false);
  const [error, setError] = useState("");

  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const cardRef = useRef(null);
  const canvasRef = useRef(null);
  const animationIdRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const sourceRef = useRef(null);

  const languages = {
    auto: "Auto Detect",
    en: "English",
    hi: "Hindi",
    es: "Spanish",
    fr: "French",
    de: "German",
    ar: "Arabic",
    zh: "Chinese",
    ru: "Russian",
    ja: "Japanese",
    ta: "Tamil",
    te: "Telugu",
    ur: "Urdu",
    bn: "Bengali",
    kn: "Kannada",
    ml: "Malayalam",
  };

  const handleMouseMove = (e) => {
    const card = cardRef.current;
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const rotateX = ((y - centerY) / centerY) * 10;
    const rotateY = ((x - centerX) / centerX) * 10;
    card.style.transform = `perspective(600px) rotateX(${-rotateX}deg) rotateY(${rotateY}deg)`;
  };

  const handleMouseLeave = () => {
    const card = cardRef.current;
    if (!card) return;
    card.style.transform = `perspective(600px) rotateX(0deg) rotateY(0deg)`;
  };

  const startRecording = async () => {
    setError("");
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert("Audio recording not supported in this browser.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      mediaRecorderRef.current.onstop = handleRecordingStop;
      mediaRecorderRef.current.start();
      setRecording(true);
    } catch (err) {
      setError("Microphone access denied or error: " + err.message);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      setRecording(false);
    }
  };

  const handleRecordingStop = async () => {
    const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");

    try {
      setError("");
      setIsTranslating(true);
      setTranslatedText("");
      setDisplayedText("");
      const response = await fetch("http://localhost:5000/speech-to-speech", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (response.ok && data.audio_url) {
        setTranslatedText(data.transcription || "");
        const audio = new Audio(data.audio_url);
        audio.play();
      } else {
        setError(data.error || "Failed to process speech.");
      }
    } catch (err) {
      setError("Connection error.");
    }
    setIsTranslating(false);
  };

  useEffect(() => {
    if (!translatedText) {
      setDisplayedText("");
      return;
    }
    let index = 0;
    setDisplayedText("");
    const interval = setInterval(() => {
      setDisplayedText((prev) => prev + translatedText.charAt(index));
      index++;
      if (index >= translatedText.length) clearInterval(interval);
    }, 30);
    return () => clearInterval(interval);
  }, [translatedText]);

  const handleTranslate = async () => {
    if (!text.trim()) {
      setError("Please enter or record some text to translate.");
      return;
    }
    setError("");
    setIsTranslating(true);
    setTranslatedText("");
    setDisplayedText("");
    try {
      const response = await fetch("http://localhost:5000/text-to-speech", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_language: sourceLanguage,
          target_language: targetLanguage,
          text,
        }),
      });
      const data = await response.json();
      if (response.ok && data.audio_url) {
        setTranslatedText(data.translated_text || "");
        const audio = new Audio(data.audio_url);
        audio.play();
      } else {
        setError(data.error || "Translation failed.");
      }
    } catch (err) {
      setError("Connection error.");
    }
    setIsTranslating(false);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("audio", file);
    fetch("http://localhost:5000/speech-to-speech", {
      method: "POST",
      body: formData,
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.audio_url) {
          setTranslatedText(data.transcription || "");
          new Audio(data.audio_url).play();
        } else {
          setError(data.error || "Failed to process audio file.");
        }
      })
      .catch(() => setError("Connection error."));
  };

  useEffect(() => {
    if (!recording) {
      if (animationIdRef.current) cancelAnimationFrame(animationIdRef.current);
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
        analyserRef.current = null;
        sourceRef.current = null;
      }
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    canvas.width = canvas.clientWidth * window.devicePixelRatio;
    canvas.height = 80 * window.devicePixelRatio;

    audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then((stream) => {
        sourceRef.current = audioContextRef.current.createMediaStreamSource(stream);
        analyserRef.current = audioContextRef.current.createAnalyser();
        analyserRef.current.fftSize = 256;
        sourceRef.current.connect(analyserRef.current);
        const bufferLength = analyserRef.current.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        function drawWaveform() {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          analyserRef.current.getByteTimeDomainData(dataArray);
          ctx.lineWidth = 2;
          ctx.strokeStyle = "#00ff99";
          ctx.beginPath();
          const sliceWidth = canvas.width / bufferLength;
          let x = 0;
          for (let i = 0; i < bufferLength; i++) {
            const v = dataArray[i] / 128.0;
            const y = (v * canvas.height) / 2;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
            x += sliceWidth;
          }
          ctx.lineTo(canvas.width, canvas.height / 2);
          ctx.stroke();
          animationIdRef.current = requestAnimationFrame(drawWaveform);
        }
        drawWaveform();
      })
      .catch((err) => {
        setError("Mic access denied or error: " + err.message);
        setRecording(false);
      });

    return () => {
      if (animationIdRef.current) cancelAnimationFrame(animationIdRef.current);
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
        analyserRef.current = null;
        sourceRef.current = null;
      }
    };
  }, [recording]);

  // --- ADD THIS FUNCTION ---
  const playAudio = () => {
    if (!translatedText) return;
    // For TTS playback from translatedText string
    const utterance = new SpeechSynthesisUtterance(translatedText);
    // Set language for speech synthesis if possible
    utterance.lang = targetLanguage;
    window.speechSynthesis.speak(utterance);
  };
  // --- END ---

  return (
    <div className="translator-3d-wrapper">
      {Object.values(languages).map((lang, i) => (
        <span key={i} className="float-bubble" style={{ "--i": i }}>
          {lang}
        </span>
      ))}

      <motion.div
        className="translator-3d-card"
        ref={cardRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.6 }}
      >
        <motion.h1 initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.3 }}>
          🌐 3D Speech-to-Speech Translator
        </motion.h1>

        <div className="selectors">
          <select value={sourceLanguage} onChange={(e) => setSourceLanguage(e.target.value)}>
            {Object.entries(languages).map(([code, name]) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </select>
          <select value={targetLanguage} onChange={(e) => setTargetLanguage(e.target.value)}>
            {Object.entries(languages).map(([code, name]) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </select>
        </div>

        <motion.textarea
          placeholder="Type or speak text..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
        />

        <canvas
          ref={canvasRef}
          className="waveform-canvas"
          style={{ width: "100%", height: "80px", marginBottom: "20px", borderRadius: "12px", background: "rgba(0,0,0,0.1)" }}
        />

        <div className="btn-row">
          <motion.button className="glow-btn" onClick={handleTranslate} whileHover={{ scale: 1.05 }}>
            {isTranslating ? "Translating..." : "🔁 Translate & Speak"}
          </motion.button>

          <label className="icon-btn upload">
            <FaUpload />
            <input type="file" accept=".mp3, .wav, .webm" onChange={handleFileUpload} hidden />
          </label>

          <button className="icon-btn" onClick={() => setText("")}>
            <FaTrash />
          </button>

          {!recording ? (
            <button className="icon-btn" onClick={startRecording} title="Start Recording">
              <FaMicrophone />
            </button>
          ) : (
            <button className="icon-btn" onClick={stopRecording} title="Stop Recording">
              <FaStop />
            </button>
          )}
        </div>

        {error && <p className="error-msg">{error}</p>}

        <motion.div className="output-box" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          {displayedText || "Your translated text will appear here."}
        </motion.div>

        {translatedText && (
          <motion.button className="speak-btn" onClick={playAudio} whileHover={{ scale: 1.1 }}>
            <FaVolumeUp /> Speak Again
          </motion.button>
        )}
      </motion.div>
    </div>
  );
};

export default TranslatorPage;
