import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import LayoutWrapper from '@/components/LayoutWrapper'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { SessionExpiredOverlay } from '@/components/SessionExpiredOverlay'
import { Toaster } from 'react-hot-toast'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'DocuMindAI OS',
  description: 'Enterprise AI Operating System',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
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
