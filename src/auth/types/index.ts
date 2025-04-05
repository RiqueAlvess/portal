// src/auth/types/index.ts
export interface User {
    id: string;
    email: string;
    name: string;
    role: string;
  }
  
  export interface AuthPayload {
    userId: string;
    email: string;
    role: string;
  }
  
  export interface Company {
    id: string;
    name: string;
    domain: string;
  }