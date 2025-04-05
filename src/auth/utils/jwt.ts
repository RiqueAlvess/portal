import jwt from 'jsonwebtoken';
import CryptoJS from 'crypto-js';

const JWT_SECRET = process.env.JWT_SECRET || 'fallback-secret-key-for-development';
const AES_SECRET = process.env.AES_SECRET || 'fallback-aes-key-for-development';

export function generateToken(payload: object): string {
  const encryptedPayload = CryptoJS.AES.encrypt(
    JSON.stringify(payload),
    AES_SECRET
  ).toString();
  
  return jwt.sign({ data: encryptedPayload }, JWT_SECRET, {
    expiresIn: '1d'
  });
}

export function verifyToken(token: string): any {
  try {
    const decoded = jwt.verify(token, JWT_SECRET) as { data: string };
    const decryptedBytes = CryptoJS.AES.decrypt(decoded.data, AES_SECRET);
    const decryptedPayload = JSON.parse(decryptedBytes.toString(CryptoJS.enc.Utf8));
    
    return { valid: true, payload: decryptedPayload };
  } catch (error) {
    return { valid: false, error };
  }
}