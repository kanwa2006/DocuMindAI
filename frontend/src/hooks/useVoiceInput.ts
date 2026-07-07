"use client";

import { useState, useRef, useEffect, useCallback } from "react";

export type VoiceState = "idle" | "listening" | "processing" | "error" | "unsupported";

export function useVoiceInput(onTranscript: (text: string) => void, lang: string = "en-IN") {
  const [state, setState] = useState<VoiceState>("idle");
  const stateRef = useRef<VoiceState>("idle");
  const [interimText, setInterimText] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const recognitionRef = useRef<any>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  const isSupported =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  const setStateSafe = (s: VoiceState) => {
    stateRef.current = s;
    setState(s);
  };

  const startListening = useCallback(() => {
    if (!isSupported) {
      setStateSafe("unsupported");
      return;
    }
    if (stateRef.current === "listening") {
      recognitionRef.current?.stop();
      setStateSafe("idle");
      setInterimText("");
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      return;
    }

    const SpeechRecognitionAPI =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognitionAPI();

    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = lang;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setStateSafe("listening");
      setInterimText("");
      setErrorMessage("");
    };

    recognition.onresult = (event: any) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          final += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }
      setInterimText(interim);
      if (final) {
        setStateSafe("processing");
        setInterimText("");
        onTranscriptRef.current(final.trim());
        recognitionRef.current?.stop();
      }
    };

    recognition.onspeechend = () => {
      timeoutRef.current = setTimeout(() => {
        recognition.stop();
      }, 2000);
    };

    recognition.onerror = (event: any) => {
      const msgs: Record<string, string> = {
        "no-speech": "No speech detected. Tap the mic and try again.",
        "audio-capture": "Microphone not found. Check permissions.",
        "not-allowed": "Microphone access denied. Allow it in browser settings.",
        network: "Network error. Check your connection.",
      };
      setErrorMessage(msgs[event.error] || "Voice input failed. Please type instead.");
      setStateSafe("error");
    };

    recognition.onend = () => {
      if (stateRef.current !== "processing") {
        setStateSafe("idle");
      }
      setInterimText("");
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [isSupported, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setStateSafe("idle");
    setInterimText("");
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
  }, []);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return { state, interimText, errorMessage, isSupported, startListening, stopListening };
}
