import type { Metadata } from 'next'
import { Instrument_Serif, DM_Sans, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import LayoutWrapper from '@/components/LayoutWrapper'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { SessionExpiredOverlay } from '@/components/SessionExpiredOverlay'
import { Toaster } from 'react-hot-toast'

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
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#FAFAFA' },
    { media: '(prefers-color-scheme: dark)',  color: '#0C0C0E' },
  ],
  icons: { icon: '/favicon.svg', apple: '/apple-touch-icon.png' },
  openGraph: {
    title: 'DocuMindAI',
    description: 'Trusted document intelligence with grounded answers.',
    type: 'website',
  },
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
        <Toaster position="top-center" toastOptions={{ duration: 4000 }} />
        <ErrorBoundary>
          <SessionExpiredOverlay />
          <LayoutWrapper>
            {children}
          </LayoutWrapper>
        </ErrorBoundary>
      </body>
    </html>
  )
}
