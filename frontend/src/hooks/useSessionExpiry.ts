"use client"
import { useState, useEffect } from "react"

export function useSessionExpiry() {
  const [sessionExpired, setSessionExpired] = useState(false)

  useEffect(() => {
    const handler = () => {
      // Never show the session-expired overlay on auth/public pages.
      // These pages have no session to expire; unauthenticated API calls
      // (e.g. billing status fetched by LayoutWrapperInner) return 401
      // which would otherwise trigger a false "session expired" modal.
      const pathname = window.location.pathname
      if (
        pathname === "/login" ||
        pathname === "/register" ||
        pathname === "/forgot-password" ||
        pathname === "/"
      ) {
        return
      }
      setSessionExpired(true)
    }
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
