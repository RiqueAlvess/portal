// src/components/admin/UserForm.tsx
'use client';

import { useState, useEffect } from 'react';
import Modal from '@/components/ui/Modal';
import { Eye, EyeOff } from 'lucide-react';

type User = {
  id: string;
  nome: string;
  email: string;
  type_user: string;
  active: boolean;
};

type UserFormProps = {
  user: User | null;
  onClose: () => void;
  onSubmit: (userData: any) => void;
};

export default function UserForm({ user, onClose, onSubmit }: UserFormProps) {
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    senha: '',
    type_user: 'user',
    active: true,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const isEditing = !!user;

  useEffect(() => {
    if (user) {
      setFormData({
        nome: user.nome,
        email: user.email,
        senha: '',
        type_user: user.type_user,
        active: user.active,
      });
    }
  }, [user]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData(prev => ({ ...prev, [name]: checked }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.nome.trim()) {
      newErrors.nome = 'Nome é obrigatório';
    }
    
    if (!formData.email.trim()) {
      newErrors.email = 'Email é obrigatório';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Email inválido';
    }
    
    if (!isEditing && !formData.senha.trim()) {
      newErrors.senha = 'Senha é obrigatória para novos usuários';
    } else if (!isEditing && formData.senha.length < 6) {
      newErrors.senha = 'Senha deve ter no mínimo 6 caracteres';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validate()) return;
    
    // Se estiver editando e a senha estiver vazia, remove do objeto
    const submitData = { ...formData };
    if (isEditing && !submitData.senha) {
      delete submitData.senha;
    }
    
    onSubmit(submitData);
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={isEditing ? "Editar Usuário" : "Novo Usuário"}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="nome" className="block text-sm font-medium text-secondary-medium">
            Nome
          </label>
          <input
            type="text"
            id="nome"
            name="nome"
            value={formData.nome}
            onChange={handleChange}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-light focus:outline-none focus:ring-primary-light"
          />
          {errors.nome && (
            <p className="mt-1 text-sm text-accent">{errors.nome}</p>
          )}
        </div>
        
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-secondary-medium">
            Email
          </label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-light focus:outline-none focus:ring-primary-light"
          />
          {errors.email && (
            <p className="mt-1 text-sm text-accent">{errors.email}</p>
          )}
        </div>
        
        <div>
          <label htmlFor="senha" className="block text-sm font-medium text-secondary-medium">
            {isEditing ? "Nova Senha (deixe em branco para manter a atual)" : "Senha"}
          </label>
          <div className="mt-1 relative">
            <input
              type={showPassword ? "text" : "password"}
              id="senha"
              name="senha"
              value={formData.senha}
              onChange={handleChange}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-light focus:outline-none focus:ring-primary-light"
            />
            <button
              type="button"
              className="absolute inset-y-0 right-0 pr-3 flex items-center"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? (
                <EyeOff className="h-5 w-5 text-gray-400" />
              ) : (
                <Eye className="h-5 w-5 text-gray-400" />
              )}
            </button>
          </div>
          {errors.senha && (
            <p className="mt-1 text-sm text-accent">{errors.senha}</p>
          )}
        </div>
        
        <div>
          <label htmlFor="type_user" className="block text-sm font-medium text-secondary-medium">
            Perfil
          </label>
          <select
            id="type_user"
            name="type_user"
            value={formData.type_user}
            onChange={handleChange}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-light focus:outline-none focus:ring-primary-light"
          >
            <option value="user">Usuário</option>
            <option value="admin">Administrador</option>
            <option value="superadmin">Super Admin</option>
          </select>
        </div>
        
        <div className="flex items-center">
          <input
            type="checkbox"
            id="active"
            name="active"
            checked={formData.active}
            onChange={handleChange}
            className="h-4 w-4 text-primary-light border-gray-300 rounded focus:ring-primary-light"
          />
          <label htmlFor="active" className="ml-2 block text-sm text-secondary-medium">
            Ativo
          </label>
        </div>
        
        <div className="mt-6 flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-secondary-medium bg-white hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            type="submit"
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-dark hover:bg-primary-light"
          >
            {isEditing ? "Atualizar" : "Cadastrar"}
          </button>
        </div>
      </form>
    </Modal>
  );
}