// src/app/dashboard/page.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/auth/hooks/useAuth';
import AdminPanel from '@/components/admin/AdminPanel';

export default function Dashboard() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      if (user.role !== 'admin' && user.role !== 'superadmin') {
        router.push('/acesso-negado');
      }
    } else if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  if (loading) return <div className="p-8 text-center">Carregando...</div>;
  if (!user) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-primary-dark">Administração do Sistema</h1>
      <AdminPanel />
    </div>
  );
}