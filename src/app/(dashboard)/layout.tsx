// src/app/(dashboard)/layout.tsx
'use client';

import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import Navbar from '@/components/ui/Navbar';
import Sidebar from '@/components/ui/Sidebar';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();

  // Fechar sidebar quando o caminho mudar (útil em móvel)
  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  return (
    <div className="h-screen flex flex-col bg-secondary-light">
      <Navbar toggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
      
      <div className="flex flex-1 overflow-hidden">
        <Sidebar isOpen={sidebarOpen} />
        
        <main className="flex-1 overflow-y-auto p-4 md:p-6 md:ml-64">
          {children}
        </main>
      </div>
    </div>
  );
}