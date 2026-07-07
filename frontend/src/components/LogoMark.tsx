"use client";
import React from "react";

interface LogoMarkProps {
  size?: "sm" | "md" | "lg";
}

const sizeMap = {
  sm: { px: 20, radius: 7, fontSize: 12 },
  md: { px: 28, radius: 7, fontSize: 17 },
  lg: { px: 36, radius: 10, fontSize: 22 },
};

export default function LogoMark({ size = "md" }: LogoMarkProps) {
  const { px, radius, fontSize } = sizeMap[size];
  return (
    <span
      aria-hidden="true"
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: px,
        height: px,
        borderRadius: radius,
        background: "var(--brand, #0D0D0D)",
        fontFamily: '"Instrument Serif", Georgia, serif',
        color: "var(--brand-text, #fff)",
        fontSize,
        lineHeight: 1,
        userSelect: "none",
        flexShrink: 0,
      }}
    >
      D
    </span>
  );
}
