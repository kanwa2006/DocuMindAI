"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import { useVoiceInput } from "../../hooks/useVoiceInput";

const LANGUAGES = [
  { code: "en-IN", label: "🇮🇳 EN-IN" },
  { code: "hi-IN", label: "🇮🇳 HI" },
  { code: "ta-IN", label: "🇮🇳 TA" },
  { code: "te-IN", label: "🇮🇳 TE" },
  { code: "mr-IN", label: "🇮🇳 MR" },
  { code: "en-GB", label: "🇬🇧 EN-GB" },
  { code: "en-US", label: "🇺🇸 EN-US" },
];

interface VoiceInputButtonProps {
  voiceLang: string;
  onLangChange: (lang: string) => void;
  onTranscript: (text: string) => void;
  onInterimText?: (text: string) => void;
  disabled?: boolean;
}

export default function VoiceInputButton({
  voiceLang,
  onLangChange,
  onTranscript,
  onInterimText,
  disabled,
}: VoiceInputButtonProps) {
  const { state, interimText, errorMessage, isSupported, startListening } =
    useVoiceInput(onTranscript, voiceLang);

  // Mount flag — the <select> below renders the *browser-resolved* voiceLang
  // (parent reads it from localStorage in a useEffect, so the value can differ
  // from the server-rendered HTML). Render the select only after hydration to
  // sidestep "Hydration failed... server rendered HTML didn't match client".
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  const startListeningRef = useRef(startListening);
  startListeningRef.current = startListening;

  // Forward interim text to parent
  useEffect(() => {
    onInterimText?.(interimText);
  }, [interimText]); // eslint-disable-line react-hooks/exhaustive-deps

  // Show toast on error
  useEffect(() => {
    if (state === "error" && errorMessage) {
      toast.error(errorMessage);
    }
  }, [state, errorMessage]);

  // Keyboard shortcut: Ctrl+Shift+V / Cmd+Shift+V
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toUpperCase() === "V") {
        e.preventDefault();
        if (!disabled) startListeningRef.current();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [disabled]);

  if (!isSupported) return null;

  const isListening = state === "listening";
  const isProcessing = state === "processing";

  const prefersReduced =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const btnStyle: React.CSSProperties = {
    width: "36px",
    height: "36px",
    borderRadius: "50%",
    border: isListening ? "2px solid #ef4444" : "1px solid var(--border-default)",
    background: isListening ? "rgba(239, 68, 68, 0.1)" : "var(--surface-sunken)",
    cursor: disabled ? "not-allowed" : "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
    transition: "all 150ms ease",
    animation:
      isListening && !prefersReduced
        ? "pulse-ring 1.5s cubic-bezier(0.215, 0.61, 0.355, 1) infinite"
        : "none",
    opacity: disabled ? 0.5 : 1,
    padding: 0,
  };

  const tooltip = isListening
    ? "Listening… (tap to stop)"
    : isProcessing
    ? "Processing…"
    : "Ask with voice (Ctrl+Shift+V)";

  const selectStyle: React.CSSProperties = {
    height: "28px",
    padding: "0 4px",
    fontSize: "11px",
    fontFamily: "var(--font-body)",
    background: "var(--surface-sunken)",
    border: "1px solid var(--border-default)",
    borderRadius: "6px",
    color: "var(--text-secondary)",
    cursor: "pointer",
    flexShrink: 0,
    maxWidth: "84px",
  };

  return (
    <>
      {/* Language selector — rendered client-only to avoid hydration mismatch
          on the `value` attribute when localStorage overrides the default. */}
      {mounted ? (
        <select
          value={voiceLang}
          onChange={(e) => onLangChange(e.target.value)}
          aria-label="Voice input language"
          title="Voice language"
          style={selectStyle}
        >
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
      ) : (
        <span
          aria-hidden="true"
          style={{ ...selectStyle, display: "inline-block", width: "60px" }}
        />
      )}

      {/* Mic button */}
      <button
        type="button"
        onClick={() => !disabled && startListening()}
        disabled={disabled}
        role="button"
        aria-pressed={isListening}
        aria-label={`Voice input — currently ${state}`}
        title={tooltip}
        style={btnStyle}
      >
        {isProcessing ? (
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--text-secondary)"
            strokeWidth="2"
            strokeLinecap="round"
            style={{ animation: "spin 1s linear infinite" }}
          >
            <circle cx="12" cy="12" r="9" opacity="0.25" />
            <path d="M21 12A9 9 0 003 12" />
          </svg>
        ) : (
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke={isListening ? "#ef4444" : "var(--text-secondary)"}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="22" />
            <line x1="8" y1="22" x2="16" y2="22" />
          </svg>
        )}
      </button>
    </>
  );
}
