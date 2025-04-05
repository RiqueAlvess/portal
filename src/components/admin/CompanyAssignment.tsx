// src/components/admin/CompanyAssignment.tsx
'use client';

import { useState, useEffect } from 'react';
import { Check, X, Link, Search } from 'lucide-react';

type User = {
  id: string;
  nome: string;
  email: string;
};

type Company = {
  id: string;
  codigo: number;
  nome_abreviado: string;
  razao_social: string;
  ativo: boolean;
  assigned: boolean;
};

export default function CompanyAssignment() {
  const [users, setUsers] = useState<User[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    if (selectedUserId) {
      fetchCompaniesForUser(selectedUserId);
    }
  }, [selectedUserId]);

  async function fetchUsers() {
    try {
      setLoading(true);
      const response = await fetch('/api/admin/users');
      const data = await response.json();
      
      if (response.ok) {
        setUsers(data.users);
      } else {
        console.error('Falha ao carregar usuários:', data.error);
      }
    } catch (error) {
      console.error('Erro ao carregar usuários:', error);
    } finally {
      setLoading(false);
    }
  }

  async function fetchCompaniesForUser(userId: string) {
    try {
      setLoading(true);
      const response = await fetch(`/api/admin/users/${userId}/companies`);
      const data = await response.json();
      
      if (response.ok) {
        setCompanies(data.companies);
      } else {
        console.error('Falha ao carregar empresas:', data.error);
      }
    } catch (error) {
      console.error('Erro ao carregar empresas:', error);
    } finally {
      setLoading(false);
    }
  }

  async function toggleCompanyAssignment(companyId: string, assigned: boolean) {
    if (!selectedUserId) return;
    
    try {
      const response = await fetch(`/api/admin/users/${selectedUserId}/companies/${companyId}`, {
        method: assigned ? 'DELETE' : 'POST',
      });
      
      if (response.ok) {
        // Atualiza o estado local para refletir a mudança
        setCompanies(prevCompanies => 
          prevCompanies.map(company => 
            company.id === companyId 
              ? { ...company, assigned: !assigned } 
              : company
          )
        );
      } else {
        const data = await response.json();
        console.error('Falha ao atualizar empresa:', data.error);
      }
    } catch (error) {
      console.error('Erro ao atualizar empresa:', error);
    }
  }

  const filteredCompanies = companies.filter(company => 
    company.nome_abreviado.toLowerCase().includes(searchTerm.toLowerCase()) || 
    company.razao_social.toLowerCase().includes(searchTerm.toLowerCase()) ||
    company.codigo.toString().includes(searchTerm)
  );

  return (
    <div>
      <div className="mb-6">
        <label htmlFor="selectedUser" className="block text-sm font-medium text-secondary-medium mb-2">
          Selecione um usuário
        </label>
        <select
          id="selectedUser"
          value={selectedUserId}
          onChange={(e) => setSelectedUserId(e.target.value)}
          className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-light focus:outline-none focus:ring-primary-light"
        >
          <option value="">Selecione...</option>
          {users.map(user => (
            <option key={user.id} value={user.id}>
              {user.nome} ({user.email})
            </option>
          ))}
        </select>
      </div>
      
      {selectedUserId && (
        <>
          <div className="flex justify-between items-center mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
              <input
                type="text"
                placeholder="Buscar empresas..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-md"
              />
            </div>
          </div>
          
          {loading ? (
            <div className="text-center py-8">Carregando empresas...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-secondary-light">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-medium uppercase tracking-wider">Código</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-medium uppercase tracking-wider">Nome</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-medium uppercase tracking-wider">Razão Social</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-medium uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-medium uppercase tracking-wider">Atribuída</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredCompanies.length > 0 ? (
                    filteredCompanies.map((company) => (
                      <tr key={company.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{company.codigo}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{company.nome_abreviado}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{company.razao_social}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            company.ativo 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {company.ativo ? 'Ativa' : 'Inativa'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <button
                            onClick={() => toggleCompanyAssignment(company.id, company.assigned)}
                            className={`p-1 rounded-full ${
                              company.assigned
                                ? 'bg-green-100 text-green-800 hover:bg-red-100 hover:text-red-800'
                                : 'bg-gray-100 text-gray-800 hover:bg-green-100 hover:text-green-800'
                            }`}
                            title={company.assigned ? 'Remover atribuição' : 'Atribuir ao usuário'}
                          >
                            {company.assigned ? (
                              <Check className="h-5 w-5" />
                            ) : (
                              <Link className="h-5 w-5" />
                            )}
                          </button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
                        {searchTerm ? 'Nenhuma empresa encontrada' : 'Nenhuma empresa disponível'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}