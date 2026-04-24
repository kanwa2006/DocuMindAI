import React from "react";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const navigate = useNavigate();
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", textAlign: "center", fontFamily: "Segoe UI, sans-serif" }}>
      <h1 style={{ color: "#1a3a5c" }}>🧠 Welcome to DocuMind AI</h1>
      <p style={{ color: "#555", marginBottom: 32 }}>Your private document intelligence system</p>
      <div style={{ display: "flex", gap: 16, justifyContent: "center" }}>
        <button onClick={() => navigate("/chat")} style={{ background: "#1a3a5c", color: "#fff", border: "none", borderRadius: 8, padding: "12px 28px", fontSize: 15, cursor: "pointer" }}>
          💬 Go to Chat
        </button>
        <button onClick={() => navigate("/documents")} style={{ background: "#27ae60", color: "#fff", border: "none", borderRadius: 8, padding: "12px 28px", fontSize: 15, cursor: "pointer" }}>
          📄 My Documents
        </button>
      </div>
    </div>
  );
}