"use client";
import React from "react";

interface State { hasError: boolean; error?: Error }

export class ErrorBoundary extends React.Component<React.PropsWithChildren<{}>, State> {
  constructor(props: React.PropsWithChildren<{}>) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "100vh",
            gap: 16,
            padding: 32,
            background: "var(--surface-base, #fafafa)",
          }}
        >
          {/* Amber warning icon circle */}
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: "50%",
              background: "var(--warning-bg, #fffbeb)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 28,
            }}
          >
            ⚠
          </div>

          <h1
            style={{
              fontFamily: "var(--font-display, Georgia, serif)",
              fontSize: 24,
              fontWeight: 400,
              color: "var(--text-primary, #0a0a0b)",
              margin: 0,
            }}
          >
            Something went wrong
          </h1>

          {/* Error code box */}
          <pre
            style={{
              fontFamily: "var(--font-mono, 'Fira Code', monospace)",
              fontSize: 13,
              background: "var(--surface-sunken, #f4f4f5)",
              border: "1px solid var(--border-default, rgba(0,0,0,0.12))",
              borderRadius: 8,
              padding: 12,
              maxWidth: 480,
              overflow: "auto",
              margin: 0,
              color: "var(--text-secondary, #52525b)",
            }}
          >
            {this.state.error?.message || "An unexpected error occurred."}
          </pre>

          {/* Two recovery buttons */}
          <div style={{ display: "flex", gap: 12 }}>
            <button
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "8px 16px",
                borderRadius: 8,
                background: "var(--brand, #0D0D0D)",
                color: "var(--brand-text, #fff)",
                border: "none",
                fontSize: 14,
                fontWeight: 500,
                cursor: "pointer",
              }}
              onClick={() => { this.setState({ hasError: false }); window.location.reload(); }}
            >
              Reload Page
            </button>
            <button
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "8px 16px",
                borderRadius: 8,
                background: "transparent",
                color: "var(--text-secondary, #52525b)",
                border: "none",
                fontSize: 14,
                fontWeight: 500,
                cursor: "pointer",
              }}
              onClick={() => { window.location.href = "/"; }}
            >
              Go to Home
            </button>
          </div>

          <p
            style={{
              fontSize: 12,
              color: "var(--text-tertiary, #71717a)",
              margin: 0,
            }}
          >
            If this keeps happening, please contact support.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
