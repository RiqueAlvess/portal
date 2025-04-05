import { NextRequest } from 'next/server';
import { csrf } from 'edge-csrf';

const csrfProtection = csrf({
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    name: 'csrf',
    sameSite: 'strict',
    path: '/',
    httpOnly: true,
  },
});

export async function createCSRFToken(request: NextRequest) {
  const response = await csrfProtection(request);
  return response.token;
}

export async function validateCSRFToken(request: NextRequest) {
  const response = await csrfProtection(request);
  return response.valid;
}