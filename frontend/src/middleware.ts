import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// PHASE 1: NEXT.JS AUTH MIDDLEWARE
// Secures the application globally by protecting sensitive routes at the Edge.
export function middleware(request: NextRequest) {
  const token = request.cookies.get('token')?.value;

  const isAuthPage = request.nextUrl.pathname.startsWith('/login') ||
                     request.nextUrl.pathname.startsWith('/signup');

  const isProtectedRoute = request.nextUrl.pathname.startsWith('/dashboard') ||
                           request.nextUrl.pathname.startsWith('/general') ||
                           request.nextUrl.pathname.startsWith('/exam') ||
                           request.nextUrl.pathname.startsWith('/hr') ||
                           request.nextUrl.pathname.startsWith('/legal') ||
                           request.nextUrl.pathname.startsWith('/finance') ||
                           request.nextUrl.pathname.startsWith('/study') ||
                           request.nextUrl.pathname.startsWith('/research') ||
                           request.nextUrl.pathname.startsWith('/account') ||
                           request.nextUrl.pathname.startsWith('/bookmarks') ||
                           request.nextUrl.pathname.startsWith('/settings') ||
                           request.nextUrl.pathname.startsWith('/admin') ||
                           request.nextUrl.pathname.startsWith('/sessions') ||
 