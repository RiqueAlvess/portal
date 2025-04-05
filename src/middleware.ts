// src/middleware.ts
import { NextRequest, NextResponse } from 'next/server';
import { verifyToken } from '@/auth/utils/jwt';

const PUBLIC_ROUTES = [
  '/',
  '/login',
  '/register',
  '/api/auth/login',
  '/api/auth/logout',
];

const isPublicRoute = (path: string): boolean => {
  return PUBLIC_ROUTES.some(publicPath => 
    path === publicPath || 
    path.startsWith('/api/public') ||
    path.startsWith('/_next') ||
    path.startsWith('/static')
  );
};

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  
  if (isPublicRoute(path)) {
    return NextResponse.next();
  }
  
  const token = request.cookies.get('token')?.value;
  
  if (!token) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    url.searchParams.set('callbackUrl', request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }
  
  const { valid, payload } = verifyToken(token);
  
  if (!valid) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    url.searchParams.set('callbackUrl', request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }
  
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-user-id', payload.userId);
  requestHeaders.set('x-user-role', payload.role);
  
  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};