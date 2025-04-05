// src/app/api/csrf/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { createCSRFToken } from '@/lib/csrf';

export async function GET(request: NextRequest) {
  const csrfToken = await createCSRFToken(request);
  
  return NextResponse.json({ csrfToken });
}