import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// PHASE 1: NEXT.JS AUTH MIDDLEWARE
// Secures the application globally by protecting sensitive routes at the Edge.
export function middleware(request: NextRequest) {
  const token = request.cookies.get('token')?.value;
  
  const isAuthPage = request.nextUrl.pathname.startsWith('/login') || 
                     request.nextUrl.pathname.startsWith('/signup');
                     
  const isProtectedRoute = request.nextUrl.pathname.startsWith('/dashboard') ||
                           request.nextUrl.pathname.startsWith('/hr') ||
                           request.nextUrl.pathname.startsWith('/legal') ||
                           request.nextUrl.pathname.startsWith('/finance') ||
                           request.nextUrl.pathname.startsWith('/study') ||
                           request.nextUrl.pathname.startsWith('/research');

  // 1. Redirect unauthenticated users to login
  if (isProtectedRoute && !token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('from', request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  // 2. Redirect authenticated users away from login/signup pages
  if (isAuthPage && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
