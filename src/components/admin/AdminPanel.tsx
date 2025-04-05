// src/components/admin/AdminPanel.tsx
'use client';

import { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import UserManagement from './UserManagement';
import CompanyAssignment from './CompanyAssignment';

export default function AdminPanel() {
  const [activeTab, setActiveTab] = useState('users');

  return (
    <div className="bg-white rounded-lg shadow-md">
      <Tabs defaultValue="users" onValueChange={setActiveTab} value={activeTab}>
        <TabsList className="border-b border-gray-200 px-4">
          <TabsTrigger value="users" className="py-3 px-4 font-medium">
            Gerenciamento de Usuários
          </TabsTrigger>
          <TabsTrigger value="companies" className="py-3 px-4 font-medium">
            Atribuição de Empresas
          </TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="p-4">
          <UserManagement />
        </TabsContent>

        <TabsContent value="companies" className="p-4">
          <CompanyAssignment />
        </TabsContent>
      </Tabs>
    </div>
  );
}