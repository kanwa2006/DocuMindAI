'use client'

import { useEffect } from 'react'
import { initAnalytics } from '@/lib/analytics'

export default function AnalyticsProvider() {
  useEffect(() => {
    initAnalytics()
  }, [])
  return null
}
