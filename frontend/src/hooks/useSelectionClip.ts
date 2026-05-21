"use client";

import { useEffect, useRef, useCallback } from "react";

interface UseSelectionClipOptions {
  onSelection: (text: string, rect: DOMRect) => void;
  delayMs?: number;
}

export function useSelectionClip({ onSelection, delayMs = 500 }: UseSelectionClipOptions) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseUp = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) return;

      const text = selection.toString().trim();
      if (text.length <= 20) return;

      const anchorNode = selection.anchorNode;
      if (!anchorNode) return;

      const element =
        anchorNode.nodeType === Node.ELEMENT_NODE
          ? (anchorNode as Element)
          : anchorNode.parentElement;

      if (!element) return;

      // Ignore selections inside inputs, textareas, and no-clip-zone containers
      if (
        element.closest("input") ||
        element.closest("textarea") ||
        element.closest(".no-clip-zone")
      ) return;

      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      onSelection(text, rect);
    }, delayMs);
  }, [onSelection, delayMs]);

  useEffect(() => {
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mouseup", handleMouseUp);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [handleMouseUp]);
}
