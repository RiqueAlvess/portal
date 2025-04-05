// src/components/admin/UserManagement.tsx
'use client';

import { useState, useEffect } from 'react';
import { PlusCircle, Pencil, Trash, Search } from 'lucide-react';
import UserForm from './UserForm';
import DeleteConfirmation from './DeleteConfirmation';

type User = {
  id: string;
  nome: string;
  email: string;
  type_user: string;
  active: boolean;
};

export default function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, []);

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

  const filteredUsers = users.filter(user => 
    user.nome.toLowerCase().includes(searchTerm.toLowerCase()) || 
    user.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  function handleAddUser() {
    setCurrentUser(null);
    setShowForm(true);
  }

  function handleEditUser(user: User) {
    setCurrentUser(user);
    setShowForm(true);
  }

  function handleDeleteUser(user: User) {
    setCurrentUser(user);
    setShowDeleteConfirmation(true);
  }

  async function confirmDelete() {
    if (!currentUser) return;
    
    try {
      const response = await fetch(`/api/admin/users/${currentUser.id}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        setUsers(users.filter(user => user.id !== currentUser.id));
        setShowDeleteConfirmation(false);
        setCurrentUser(null);
      } else {
        const data = await response.json();
        console.error('Falha ao excluir usuário:', data.error);
      }
    } catch (error) {
      console.error('Erro ao excluir usuário:', error);
    }
  }

  async function onFormSubmit(userData: Partial<User>) {
    try {
      const isEditing = !!currentUser;
      const url = isEditing 
        ? `/api/admin/users/${currentUser.id}` 
        : '/api/admin/users';
        
      const response = await fetch(url, {
        method: isEditing ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });
      
      if (response.ok) {
        fetchUsers();
        setShowForm(false);
      } else {
        const data = await response.json();
        console.error('Falha ao salvar usuário:', data.error);
      }
    } catch (error) {
      console.error('Erro ao salvar usuário:', error);
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
          <input
            type="text"
            placeholder="Buscar usuários..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 pr-4 py-2 border border-gray-300 rounded-md"
          />
        </div>
        
        <button
          onClick={handleAddUser}
          className="flex items-center space-x-1 bg-primary-dark text-white px-4 py-2 rounded-md hover:bg-primary-light"
        >
          <PlusCircle size={18} />
          <span>Novo Usuário</span>
        </button>
      </div>
      
      {loading ? (
        <div className="text-center py-8">Carregando usuários...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-secondary-light">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-medium uppercase tracking-wider">Nome</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-medium uppercase tracking-wider">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-medium uppercase tracking-wider">Perfil</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-medium uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-medium uppercase tracking-wider">Ações</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredUsers.length > 0 ? (
                filteredUsers.map((user) => (
                  <tr key={user.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.nome}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{user.email}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.type_user === 'superadmin' ? 'Super Admin' : 
                       user.type_user === 'admin' ? 'Administrador' : 'Usuário'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        user.active 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {user.active ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleEditUser(user)}
                          className="text-primary-light hover:text-primary-dark"
                        >
                          <Pencil size={18} />
                        </button>
                        <button
                          onClick={() => handleDeleteUser(user)}
                          className="text-accent hover:text-red-800"
                        >
                          <Trash size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
                    {searchTerm ? 'Nenhum usuário encontrado' : 'Nenhum usuário cadastrado'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      
      {showForm && (
        <UserForm
          user={currentUser}
          onClose={() => setShowForm(false)}
          onSubmit={onFormSubmit}
        />
      )}
      
      {showDeleteConfirmation && currentUser && (
        <DeleteConfirmation
          title="Excluir Usuário"
          message={`Tem certeza que deseja excluir o usuário ${currentUser.nome}?`}
          onCancel={() => setShowDeleteConfirmation(false)}
          onConfirm={confirmDelete}
        />
      )}
    </div>
  );
}