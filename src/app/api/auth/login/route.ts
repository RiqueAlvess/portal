// src/app/api/auth/login/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { verifyPassword } from '@/auth/utils/password';
import { generateToken } from '@/auth/utils/jwt';
import { setCookieToken } from '@/auth/utils/cookies';
import { validateCSRFToken } from '@/lib/csrf';
import { prisma } from '@/lib/prisma';

const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(6, 'Senha deve ter no mínimo 6 caracteres'),
});

export async function POST(request: NextRequest) {
  try {
    const isValidCSRF = await validateCSRFToken(request);
    
    if (!isValidCSRF) {
      return NextResponse.json(
        { error: 'Token CSRF inválido' },
        { status: 403 }
      );
    }
    
    const body = await request.json();
    const validation = loginSchema.safeParse(body);
    
    if (!validation.success) {
      return NextResponse.json(
        { error: 'Dados inválidos', details: validation.error.format() },
        { status: 400 }
      );
    }
    
    const { email, password } = validation.data;
    
    const user = await prisma.usuario.findUnique({
      where: { email },
    });
    
    if (!user) {
      return NextResponse.json(
        { error: 'Credenciais inválidas' },
        { status: 401 }
      );
    }
    
    if (!user.active) {
      return NextResponse.json(
        { error: 'Usuário desativado' },
        { status: 403 }
      );
    }
    
    const passwordMatch = await verifyPassword(password, user.senha);
    
    if (!passwordMatch) {
      return NextResponse.json(
        { error: 'Credenciais inválidas' },
        { status: 401 }
      );
    }
    
    // Atualizar último acesso
    await prisma.usuario.update({
      where: { id: user.id },
      data: { dt_last_acess: new Date() },
    });
    
    const token = generateToken({
      userId: user.id,
      email: user.email,
      role: user.type_user,
    });
    
    const response = NextResponse.json(
      { 
        message: 'Login realizado com sucesso',
        user: {
          id: user.id,
          email: user.email,
          name: user.nome,
          role: user.type_user,
        }
      },
      { status: 200 }
    );
    
    setCookieToken(response.cookies, token);
    
    return response;
  } catch (error) {
    console.error('Erro de autenticação:', error);
    return NextResponse.json(
      { error: 'Falha na autenticação' },
      { status: 500 }
    );
  }
}