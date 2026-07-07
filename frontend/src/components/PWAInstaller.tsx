"use client";

import { useEffect } from "react";

export default function PWAInstaller() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/sw.js")
        .then(() => {/* SW registered */})
        .catch(() => {/* SW registration failed — non-fatal */});
    }
  }, []);
  return null;
}
