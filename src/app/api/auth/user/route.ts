// src/app/api/auth/user/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/auth/utils/cookies';
import { verifyToken } from '@/auth/utils/jwt';

export async function GET(request: NextRequest) {
  const token = getTokenFromCookies();
  
  if (!token) {
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    );
  }
  
  const { valid, payload } = verifyToken(token);
  
  if (!valid) {
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    );
  }
  
  return NextResponse.json({
    user: {
      id: payload.userId,
      email: payload.email,
      name: 'User Name',
      role: payload.role,
    }
  });
}