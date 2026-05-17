"use client";

import { useState, useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import Sidebar from "./Sidebar";

export default function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Check system preference or localStorage
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setIsDarkMode(isDark);
    if (isDark) {
      document.documentElement.classList.add('dark');
    }
    
    // Restore last workspace if landing on root without chat
    if (pathname === '/' && !searchParams.get('chat')) {
      const lastWorkspace = localStorage.getItem("lastActiveWorkspace");
      if (lastWorkspace && lastWorkspace !== '/') {
        router.replace(lastWorkspace);
      }
    }
  }, []);

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
    document.documentElement.classList.toggle('dark');
  };

  const isAuthPage = pathname === '/login' || pathname === '/register' || pathname === '/forgot-password';

  if (isAuthPage) {
    return <div className={`${isDarkMode ? 'dark' : ''} h-[100dvh] bg-white dark:bg-[#0C0C0E]`}>{children}</div>;
  }

  return (
    <div className={`flex h-[100dvh] overflow-hidden ${isDarkMode ? 'dark' : ''} bg-white dark:bg-black text-black dark:text-white font-sans transition-colors`}>
      <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />
      
      <main className="flex-1 flex flex-col h-[100dvh] overflow-hidden relative">
        {/* Top Bar */}
        <header className="h-14 border-b border-black/5 dark:border-white/5 flex items-center justify-between px-6 z-10 bg-white/80 dark:bg-black/80 backdrop-blur-md">
          <div className="flex items-center gap-4">
            {!isSidebarOpen && (
              <button onClick={() => setIsSidebarOpen(true)} className="p-1 hover:bg-black/5 dark:hover:bg-white/5 rounded-md">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
              </button>
            )}
            <h1 className="font-semibold text-sm tracking-wide">Workspaces ▾</h1>
          </div>
          
          <div className="flex items-center gap-4">
            <button className="flex items-center gap-2 text-sm font-medium hover:text-black/70 dark:hover:text-white/70 transition-colors">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
              Share
            </button>
            <button onClick={toggleTheme} className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
              {isDarkMode ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>
              )}
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
