// src/components/ui/Navbar.tsx
'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Menu, Bell, User, ChevronDown } from 'lucide-react';
import { useAuth } from '@/auth/hooks/useAuth';

export default function Navbar({ toggleSidebar }: { toggleSidebar: () => void }) {
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  return (
    <nav className="bg-primary-dark text-white shadow-md">
      <div className="max-w-full mx-auto px-4">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <button 
              onClick={toggleSidebar}
              className="p-2 rounded-md text-white hover:bg-primary-light"
            >
              <Menu className="h-6 w-6" />
            </button>
            <div className="ml-4 font-semibold text-xl">Portal GRS</div>
          </div>

          <div className="flex items-center">
            <button className="p-2 rounded-md text-white hover:bg-primary-light">
              <Bell className="h-5 w-5" />
            </button>
            
            <div className="relative ml-3">
              <button 
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 text-sm p-2 rounded-md hover:bg-primary-light"
              >
                <User className="h-5 w-5" />
                <span>{user?.name || 'Usuário'}</span>
                <ChevronDown className="h-4 w-4" />
              </button>
              
              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-10">
                  <Link href="/perfil" className="block px-4 py-2 text-sm text-gray-700 hover:bg-secondary-light">
                    Meu Perfil
                  </Link>
                  <Link href="/configuracoes" className="block px-4 py-2 text-sm text-gray-700 hover:bg-secondary-light">
                    Configurações
                  </Link>
                  <button 
                    onClick={logout}
                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-secondary-light"
                  >
                    Sair
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}