// src/components/ui/Sidebar.tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Home, Users, Building, Clipboard, FileText, Settings, HelpCircle 
} from 'lucide-react';
import { clsx } from 'clsx';

interface SidebarProps {
  isOpen: boolean;
}

export default function Sidebar({ isOpen }: SidebarProps) {
  const pathname = usePathname();

  const navItems = [
    { label: 'Dashboard', href: '/dashboard', icon: Home },
    { label: 'Funcionários', href: '/funcionarios', icon: Users },
    { label: 'Empresas', href: '/empresas', icon: Building },
    { label: 'Exames', href: '/exames', icon: Clipboard },
    { label: 'Atestados', href: '/atestados', icon: FileText },
    { label: 'Configurações', href: '/configuracoes', icon: Settings },
    { label: 'Ajuda', href: '/ajuda', icon: HelpCircle },
  ];

  return (
    <div 
      className={clsx(
        "fixed left-0 top-16 bottom-0 w-64 bg-white shadow-md transform transition-transform duration-200 ease-in-out z-10",
        isOpen ? "translate-x-0" : "-translate-x-full",
        "md:translate-x-0"
      )}
    >
      <div className="h-full overflow-y-auto py-4">
        <nav className="px-4 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex items-center px-4 py-3 text-sm font-medium rounded-md",
                  isActive 
                    ? "bg-primary-light text-white" 
                    : "text-secondary-medium hover:bg-secondary-light"
                )}
              >
                <Icon className={clsx("mr-3 h-5 w-5", isActive ? "text-white" : "text-secondary-medium")} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}