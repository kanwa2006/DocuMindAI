"use client";

import React from "react";

// Reusable skeleton block
function Sk({ width, height, className = "", style = {} }: { width: number | string; height: number | string; className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width, height, borderRadius: "var(--radius-sm)", flexShrink: 0, ...style }}
    />
  );
}

/**
 * SidebarSkeleton — 8 rows of [circle 16px] [rect 140px h-4] [rect 36px h-4]
 */
export function SidebarSkeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", padding: "8px" }}>
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: "8px", height: "36px" }}>
          <Sk width={16} height={16} style={{ borderRadius: "50%", flexShrink: 0 }} />
          <Sk width={140} height={16} />
          <Sk width={36} height={16} style={{ marginLeft: "auto" }} />
        </div>
      ))}
    </div>
  );
}

/**
 * ChatMessageSkeleton — 3 user+AI message pairs
 */
export function ChatMessageSkeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", padding: "24px 32px" }}>
      {Array.from({ length: 3 }).map((_, i) => (
        <React.Fragment key={i}>
          {/* User message */}
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <Sk width={200} height={40} style={{ borderRadius: "12px" }} />
          </div>
          {/* AI message */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <Sk width={320} height={16} />
            <Sk width={260} height={16} />
            <Sk width={180} height={16} />
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}

/**
 * DocumentBarSkeleton — 3 horizontal card chips
 */
export function DocumentBarSkeleton() {
  return (
    <div style={{ display: "flex", gap: "8px", padding: "8px 16px", alignItems: "center" }}>
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="skeleton"
          style={{ width: 160, height: 40, borderRadius: "var(--radius-lg)", flexShrink: 0 }}
        />
      ))}
    </div>
  );
}

/**
 * WorkspaceHeroSkeleton — centered column: circle, title, subtitle, 3 buttons
 */
export function WorkspaceHeroSkeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px", paddingTop: "64px" }}>
      <Sk width={56} height={56} style={{ borderRadius: "50%" }} />
      <Sk width={200} height={24} style={{ borderRadius: "var(--radius-sm)" }} />
      <Sk width={280} height={16} style={{ borderRadius: "var(--radius-sm)" }} />
      <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
        <Sk width={140} height={40} style={{ borderRadius: "var(--radius-md)" }} />
        <Sk width={140} height={40} style={{ borderRadius: "var(--radius-md)" }} />
        <Sk width={140} height={40} style={{ borderRadius: "var(--radius-md)" }} />
      </div>
    </div>
  );
}
