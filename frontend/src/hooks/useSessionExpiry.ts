"use client"
import { useState, useEffect } from "react"

export function useSessionExpiry() {
  const [sessionExpired, setSessionExpired] = useState(false)

  useEffect(() => {
    const handler = () => setSessionExpired(true)
    window.addEventListener("session:expired", handler)
    return () => window.removeEventListener("session:expired", handler)
  }, [])

  const dismiss = () => {
    setSessionExpired(false)
    if (typeof window !== "undefined") {
      sessionStorage.setItem("returnTo", window.location.pathname)
      window.location.href = "/login?expired=true"
    }
  }

  return { sessionExpired, dismiss }
}
