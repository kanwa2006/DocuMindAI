import React, { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";
import { Login, Register } from "./pages/Login";
import Chat from "./pages/Chat";
import Documents from "./pages/Documents";
import DocumentViewer from "./pages/DocumentViewer";
import Profile from "./pages/Profile";
import Navbar from "./components/Navbar";
import SharedChat from "./pages/SharedChat";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));

  const handleLogin = (newToken, username) => {
    localStorage.setItem("token", newToken);
    localStorage.setItem("username", username);
    setToken(newToken);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    setToken(null);
  };

  return (
    <ThemeProvider>
      <BrowserRouter>
        {token && <Navbar onLogout={handleLogout} />}
        <Routes>
          <Route path="/login"    element={!token ? <Login onLogin={handleLogin} /> : <Navigate to="/chat" />} />
          <Route path="/register" element={!token ? <Register /> : <Navigate to="/chat" />} />
          <Route path="/chat"     element={token ? <Chat /> : <Navigate to="/login" />} />
          <Route path="/documents"        element={token ? <Documents /> : <Navigate to="/login" />} />
          <Route path="/documents/:id"    element={token ? <DocumentViewer /> : <Navigate to="/login" />} />
          <Route path="/profile"  element={token ? <Profile onLogout={handleLogout} /> : <Navigate to="/login" />} />
          <Route path="/shared/:token" element={<SharedChat />} />
          <Route path="/"         element={<Navigate to={token ? "/chat" : "/login"} />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
