'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { login } from '@/lib/api';
import toast from 'react-hot-toast';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const searchParams = useSearchParams();

  useEffect(() => {
    if (searchParams.get('expired') === 'true') {
      toast.error('Your session expired. Please sign in again.');
    }
    if (searchParams.get('registered') === 'true') {
      toast.success('Account created — sign in to continue.');
    }
    const prefillEmail = searchParams.get('email');
    if (prefillEmail) {
      setEmail(prefillEmail);
    }
  }, []);


  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      if (!email || !password) {
        setError('Please enter both email and password.');
        return;
      }
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);
      await login(formData);

      // Redirect to saved returnTo path or home
      const returnTo = sessionStorage.getItem('returnTo');
      sessionStorage.removeItem('returnTo');
      window.location.href = returnTo || '/';
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'An error occurred during login.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* LEFT COLUMN — Brand Panel (hidden on mobile) */}
      <div className="hidden lg:flex lg:w-1/2 flex-col items-center justify-center relative overflow-hidden"
           style={{ background: 'linear-gradient(135deg, #1a1a1a 0%, #050505 100%)' }}>
        <div className="max-w-md px-8 text-center">
          <h1 className="text-4xl font-bold text-white mb-2 tracking-tight">
            DocuMind<span className="italic">AI</span>
          </h1>
          <p className="text-lg text-white/90 mb-12" style={{ fontStyle: 'italic' }}>
            Trusted document intelligence. Grounded answers.
          </p>
          <div className="space-y-4 text-left">
            <div className="flex items-start gap-3">
              <span className="text-white/90 mt-0.5">✓</span>
              <span className="text-sm text-white/90">Answers only from your documents — never hallucinated</span>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-white/90 mt-0.5">✓</span>
              <span className="text-sm text-white/90">Every answer cites the exact source page</span>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-white/90 mt-0.5">✓</span>
              <span className="text-sm text-white/90">Works for Legal, Finance, Research, Education</span>
            </div>
          </div>
          {/* Abstract document illustration */}
          <div className="mt-12 opacity-20">
            <svg width="200" height="160" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg" className="mx-auto">
              <rect x="20" y="10" width="100" height="130" rx="4" stroke="white" strokeWidth="2" fill="none"/>
              <rect x="80" y="20" width="100" height="130" rx="4" stroke="white" strokeWidth="2" fill="white" fillOpacity="0.1"/>
              <line x1="95" y1="45" x2="165" y2="45" stroke="white" strokeWidth="1.5" opacity="0.6"/>
              <line x1="95" y1="60" x2="155" y2="60" stroke="white" strokeWidth="1.5" opacity="0.4"/>
              <line x1="95" y1="75" x2="160" y2="75" stroke="white" strokeWidth="1.5" opacity="0.6"/>
              <line x1="95" y1="90" x2="145" y2="90" stroke="white" strokeWidth="1.5" opacity="0.4"/>
              <line x1="95" y1="105" x2="165" y2="105" stroke="white" strokeWidth="1.5" opacity="0.6"/>
              <line x1="95" y1="120" x2="150" y2="120" stroke="white" strokeWidth="1.5" opacity="0.4"/>
            </svg>
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN — Login Form */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 bg-white dark:bg-[#0C0C0E]">
        <div className="w-full max-w-[380px]">
          {/* Mobile-only logo */}
          <div className="lg:hidden text-center mb-8">
            <h1 className="text-2xl font-bold text-black dark:text-white tracking-tight">
              DocuMind<span className="italic">AI</span>
            </h1>
          </div>



          <div className="mb-8">
            <h2 className="text-[28px] font-bold text-black dark:text-white" style={{ fontFamily: 'Georgia, serif' }}>
              Welcome back
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Sign in to your workspace
            </p>
          </div>
          
          <form className="space-y-5" onSubmit={handleLogin}>
            {error && (
              <div className="px-4 py-3 rounded-lg text-[13px] font-medium"
                   style={{ backgroundColor: 'hsl(40, 90%, 95%)', color: 'hsl(40, 80%, 30%)', border: '1px solid hsl(40, 70%, 80%)' }}>
                ⚠ {error}
              </div>
            )}
            
            <div>
              <label className="block text-xs font-medium mb-1.5 tracking-[0.1em] uppercase text-gray-500 dark:text-gray-400" htmlFor="login-email">
                EMAIL ADDRESS
              </label>
              <input
                id="login-email"
                type="email"
                required
                className="block w-full h-[44px] px-3 text-sm bg-transparent border rounded-lg transition-all
                           border-gray-200 dark:border-gray-700
                           focus:outline-none focus:border-[#0D0D0D] focus:shadow-[0_0_0_3px_rgba(13,13,13,0.18)]
                           text-black dark:text-white placeholder-gray-400 dark:placeholder-gray-600"
                placeholder="you@company.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
              />
            </div>
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="block text-xs font-medium tracking-[0.1em] uppercase text-gray-500 dark:text-gray-400" htmlFor="login-password">
                  PASSWORD
                </label>
                <Link href="/forgot-password" className="text-[13px] font-medium" style={{ color: 'var(--brand, #0D0D0D)' }}>
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  required
                  className="block w-full h-[44px] px-3 pr-11 text-sm bg-transparent border rounded-lg transition-all
                             border-gray-200 dark:border-gray-700
                             focus:outline-none focus:border-[#0D0D0D] focus:shadow-[0_0_0_3px_rgba(13,13,13,0.18)]
                             text-black dark:text-white placeholder-gray-400 dark:placeholder-gray-600"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                />
                <button 
                  type="button" 
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 w-9 h-9 m-auto mr-1 flex items-center justify-center rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                >
                  {showPassword ? (
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.29 3.29m0 0a10.05 10.05 0 015.71-1.29c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0l-3.29-3.29" /></svg>
                  ) : (
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full h-[44px] rounded-lg text-[15px] font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ backgroundColor: 'var(--brand, #0D0D0D)', color: 'var(--brand-text, #fff)' }}
              onMouseEnter={e => { if (!loading) (e.target as HTMLButtonElement).style.filter = 'brightness(1.08)'; }}
              onMouseLeave={e => { (e.target as HTMLButtonElement).style.filter = 'none'; }}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" style={{ color: 'var(--brand-text, #fff)' }} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 100 8v4a8 8 0 01-8-8z" />
                  </svg>
                </span>
              ) : 'Sign In'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
            Don&apos;t have an account?{' '}
            <Link href="/register" className="font-medium" style={{ color: 'var(--brand, #0D0D0D)' }}>
              Create one →
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
