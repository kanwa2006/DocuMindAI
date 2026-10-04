'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function MarketingNav() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    // Check if the user already has a token in localStorage
    const token = localStorage.getItem('token');
    setIsLoggedIn(!!token);
  }, []);

  return (
    <nav
      className="marketing-nav"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        background: 'var(--surface-overlay)',
        borderBottom: '1px solid var(--border-subtle)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '64px',
        padding: '0 max(24px, calc((100% - 1200px) / 2))',
      }}
    >
      <Link
        href="/"
        style={{
          fontFamily: 'var(--font-display)',
          fontSize: '1.4rem',
          color: 'var(--text-primary)',
          textDecoration: 'none',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <span style={{ fontSize: '1.5rem' }}>🧠</span>
        <span style={{ color: 'var(--brand)', fontWeight: 'var(--weight-bold)' }}>DocuMind</span>
        <span>AI</span>
      </Link>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Link
          href="/pricing"
          className="nav-pricing"
          style={{
            fontFamily: 'var(--font-body)',
            fontSize: 'var(--text-sm)',
            color: 'var(--text-secondary)',
            textDecoration: 'none',
            padding: '8px 16px',
            borderRadius: 'var(--radius-md)',
          }}
        >
          Pricing
        </Link>

        {isLoggedIn ? (
          <Link
            href="/general"
            style={{
              fontFamily: 'var(--font-body)',
              fontSize: 'var(--text-sm)',
              color: 'var(--brand-text)',
              background: 'var(--brand)',
              textDecoration: 'none',
              padding: '8px 20px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 'var(--weight-semibold)',
            }}
          >
            Go to App →
          </Link>
        ) : (
          <>
            <Link
              href="/login"
              style={{
                fontFamily: 'var(--font-body)',
                fontSize: 'var(--text-sm)',
                color: 'var(--text-secondary)',
                textDecoration: 'none',
                padding: '8px 16px',
                borderRadius: 'var(--radius-md)',
              }}
            >
              Log In
            </Link>
            <Link
              href="/register"
              style={{
                fontFamily: 'var(--font-body)',
                fontSize: 'var(--text-sm)',
                color: 'var(--brand-text)',
                background: 'var(--brand)',
                textDecoration: 'none',
                padding: '8px 20px',
                borderRadius: 'var(--radius-md)',
                fontWeight: 'var(--weight-semibold)',
              }}
            >
              Start Free
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
