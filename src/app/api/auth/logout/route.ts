// src/app/api/auth/logout/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { clearCookieToken, clearSelectedCompanyCookie } from '@/auth/utils/cookies';

export async function POST(request: NextRequest) {
  const response = NextResponse.json(
    { message: 'Logout successful' },
    { status: 200 }
  );
  
  clearCookieToken(response.cookies);
  clearSelectedCompanyCookie(response.cookies);
  
  return response;
}