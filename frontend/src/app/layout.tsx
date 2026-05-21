import type { Metadata } from 'next'
import { Suspense } from 'react'
import { Instrument_Serif, DM_Sans, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import LayoutWrapper from '@/components/LayoutWrapper'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { SessionExpiredOverlay } from '@/components/SessionExpiredOverlay'
import { Toaster } from 'react-hot-toast'
import PWAInstaller from '@/components/PWAInstaller'
import AnalyticsProvider from '@/components/AnalyticsProvider'

const instrumentSerif = Instrument_Serif({
  weight: '400',
  style: ['normal', 'italic'],
  variable: '--font-display-loaded',
  subsets: ['latin'],
})

const dmSans = DM_Sans({
  weight: ['400', '500', '600', '700'],
  variable: '--font-body-loaded',
  subsets: ['latin'],
})

const jetbrainsMono = JetBrains_Mono({
  weight: ['400', '500'],
  variable: '--font-mono-loaded',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: { default: 'DocuMindAI', template: '%s — DocuMindAI' },
  description: 'Trusted document intelligence with grounded answers.',
  applicationName: 'DocuMindAI',
  icons: { icon: '/favicon.svg', apple: '/apple-touch-icon.png' },
  openGraph: {
    title: 'DocuMindAI',
    description: 'Trusted document intelligence with grounded answers.',
    type: 'website',
  },
  manifest: '/manifest.json',
}

export const viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#FAFAFA' },
    { media: '(prefers-color-scheme: dark)',  color: '#0C0C0E' },
  ],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${instrumentSerif.variable} ${dmSans.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        {/* PWA */}
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#0C0C0E" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="DocuMindAI" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
        {/* FOUC prevention — runs before React hydrates */}
        <script dangerouslySetInnerHTML={{ __html: `
          (function() {
            try {
              var t = localStorage.getItem('theme') || 'system';
              var dark = t === 'dark' || (t === 'system' &&
                window.matchMedia('(prefers-color-scheme: dark)').matches);
              document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
              if (dark) document.documentElement.classList.add('dark');
            } catch(e) {}
          })();
        `}} />
      </head>
      <body>
        <a href="#main" className="skip-link">Skip to content</a>
        <Toaster position="top-center" toastOptions={{ duration: 4000 }} />
        <PWAInstaller />
        <AnalyticsProvider />
        <ErrorBoundary>
          <SessionExpiredOverlay />
          <Suspense fallback={<div style={{ display: "none" }} />}>
            <LayoutWrapper>
              {children}
            </LayoutWrapper>
          </Suspense>
        </ErrorBoundary>
      </body>
    </html>
  )
}
