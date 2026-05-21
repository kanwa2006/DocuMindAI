"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

export default function VoiceInput({ onTranscript, disabled }: VoiceInputProps) {
  const [listening, setListening] = useState(false);
  const [success, setSuccess] = useState(false);
  const recognitionRef = useRef<any>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Check browser support
  const SpeechRecognitionAPI =
    typeof window !== "undefined"
      ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      : null;

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  if (!SpeechRecognitionAPI) return null;

  const startListening = () => {
    if (listening || disabled) return;

    const recognition = new SpeechRecognitionAPI();
    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognitionRef.current = recognition;

    recognition.onstart = () => setListening(true);

    recognition.onresult = (e: any) => {
      const transcript = Array.from(e.results)
        .map((r: any) => r[0].transcript)
        .join(" ");
      if (transcript) {
        onTranscript(transcript);
        setSuccess(true);
        setTimeout(() => setSuccess(false), 1500);
      }
    };

    recognition.onerror = (e: any) => {
      if (e.error === "not-allowed" || e.error === "permission-denied") {
        toast.error("Microphone access needed. Please allow in browser settings.");
      }
      setListening(false);
    };

    recognition.onend = () => setListening(false);

    // Auto-stop after 5 s of silence (browser usually does this, but safety net)
    timeoutRef.current = setTimeout(() => {
      recognition.stop();
    }, 5000);

    try {
      recognition.start();
    } catch {
      setListening(false);
    }
  };

  const stopListening = () => {
    recognitionRef.current?.stop();
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setListening(false);
  };

  const handleClick = () => {
    if (listening) stopListening();
    else startListening();
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled}
      role="button"
      aria-label={listening ? "Stop voice input" : "Voice input"}
      title={listening ? "Stop listening" : "Speak your query"}
      style={{
        width: "36px",
        height: "36px",
        borderRadius: "8px",
        border: "1px solid var(--border-default)",
        background: listening ? "rgba(239,68,68,0.1)" : "var(--surface-raised)",
        cursor: disabled ? "not-allowed" : "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "16px",
        flexShrink: 0,
        transition: "border-color 100ms, background 100ms",
        animation: listening ? "pulse 1s ease-in-out infinite" : "none",
        color: listening ? "#ef4444" : success ? "var(--success-text, #16a34a)" : "var(--text-tertiary)",
      }}
    >
      {success ? "✓" : "🎤"}
    </button>
  );
}
