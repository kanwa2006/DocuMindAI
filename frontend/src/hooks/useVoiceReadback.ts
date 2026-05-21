"use client";

import { useState, useCallback, useRef } from "react";

export function useVoiceReadback() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const isSupported =
    typeof window !== "undefined" && "speechSynthesis" in window;

  const speak = useCallback(
    (text: string, lang: string = "en-IN") => {
      if (!isSupported) return;
      window.speechSynthesis.cancel();

      const cleanText = text
        .replace(/\[Source:.*?\]/g, "")
        .replace(/Page \d+/g, "")
        .replace(/#{1,3} /g, "")
        .replace(/\*\*/g, "")
        .trim()
        .slice(0, 800);

      if (!cleanText) return;

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = lang;
      utterance.rate = 0.95;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      // Prefer a local voice matching the lang; fall back to any en voice
      const voices = window.speechSynthesis.getVoices();
      const preferredVoice =
        voices.find((v) => v.lang.startsWith(lang) && !v.name.includes("Google")) ||
        voices.find((v) => v.lang.startsWith(lang)) ||
        voices.find((v) => v.lang.startsWith("en")) ||
        null;
      if (preferredVoice) utterance.voice = preferredVoice;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [isSupported]
  );

  const stop = useCallback(() => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, []);

  return { speak, stop, isSpeaking, isSupported };
}
