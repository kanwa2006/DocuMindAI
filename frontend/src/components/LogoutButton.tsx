'use client';

import { logout } from '@/lib/api';

export default function LogoutButton() {
  const handleLogout = async () => {
    try {
      await logout();
      window.location.href = '/login';
    } catch (e) {
      console.error('Logout failed', e);
    }
  };

  return (
    <button onClick={handleLogout} className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-black/50 dark:text-white/50 hover:bg-black/5 dark:hover:bg-white/5 hover:text-black dark:hover:text-white transition-colors w-full group">
      <span className="text-xl group-hover:-translate-x-1 transition-transform">🚪</span>
      <span className="font-medium hidden md:block">Logout</span>
    </button>
  );
}
