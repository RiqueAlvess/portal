// src/auth/utils/cookies.ts
import { cookies } from 'next/headers';
import { ResponseCookies } from 'next/dist/compiled/@edge-runtime/cookies';
import CryptoJS from 'crypto-js';

const AES_SECRET = process.env.AES_SECRET || 'fallback-aes-key-for-development';
const TOKEN_COOKIE_NAME = 'token';
const COMPANY_COOKIE_NAME = 'selected_company';

export function setCookieToken(
  cookieStore: ResponseCookies,
  token: string
): void {
  cookieStore.set(TOKEN_COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    path: '/',
    maxAge: 60 * 60 * 24,
  });
}

export function clearCookieToken(cookieStore: ResponseCookies): void {
  cookieStore.set(TOKEN_COOKIE_NAME, '', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    path: '/',
    maxAge: 0,
  });
}

export function getTokenFromCookies(): string | undefined {
  const cookieStore = cookies();
  return cookieStore.get(TOKEN_COOKIE_NAME)?.value;
}

export function setSelectedCompanyCookie(
  cookieStore: ResponseCookies,
  companyId: string
): void {
  const encryptedCompanyId = CryptoJS.AES.encrypt(
    companyId,
    AES_SECRET
  ).toString();
  
  cookieStore.set(COMPANY_COOKIE_NAME, encryptedCompanyId, {
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    path: '/',
    maxAge: 60 * 60 * 24 * 30,
  });
}

export function getSelectedCompanyFromCookies(): string | null {
  try {
    const cookieStore = cookies();
    const encryptedCompanyId = cookieStore.get(COMPANY_COOKIE_NAME)?.value;
    
    if (!encryptedCompanyId) return null;
    
    const decryptedBytes = CryptoJS.AES.decrypt(encryptedCompanyId, AES_SECRET);
    return decryptedBytes.toString(CryptoJS.enc.Utf8);
  } catch (error) {
    return null;
  }
}

export function clearSelectedCompanyCookie(cookieStore: ResponseCookies): void {
  cookieStore.set(COMPANY_COOKIE_NAME, '', {
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    path: '/',
    maxAge: 0,
  });
}