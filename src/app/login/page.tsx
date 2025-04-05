// src/app/login/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, LogIn } from 'lucide-react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      // Implementação temporária para teste
      if (email === 'admin@example.com' && password === 'admin123') {
        // Simular login bem-sucedido
        setTimeout(() => {
          router.push('/dashboard');
        }, 500);
      } else {
        throw new Error('Credenciais inválidas');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao fazer login');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Coluna Lateral - Imagem/Destaque */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#00325A] text-white">
        <div className="flex flex-col justify-center px-12 py-12">
          <h1 className="text-4xl font-bold mb-4">Portal GRS</h1>
          <p className="text-xl mb-6">Gestão de Relatórios de Saúde</p>
          <p className="text-gray-300">
            Acesse informações sobre exames, atestados e funcionários em uma plataforma unificada.
          </p>
        </div>
      </div>
      
      {/* Formulário de Login */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="mb-10 text-center lg:hidden">
            <h1 className="text-3xl font-bold text-[#00325A]">Portal GRS</h1>
            <p className="text-gray-600 mt-2">Gestão de Relatórios de Saúde</p>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
            <h2 className="text-2xl font-semibold text-gray-800 mb-6">Login</h2>
            
            {error && (
              <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm">
                {error}
              </div>
            )}
            
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-[#0072BC] focus:border-transparent"
                  placeholder="seu@email.com"
                  required
                />
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                    Senha
                  </label>
                  <a href="#" className="text-xs text-[#0072BC] hover:text-[#00325A]">
                    Esqueceu a senha?
                  </a>
                </div>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-[#0072BC] focus:border-transparent"
                    placeholder="••••••••"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>
              
              <div className="flex items-center">
                <input
                  id="remember"
                  type="checkbox"
                  className="h-4 w-4 text-[#0072BC] border-gray-300 rounded focus:ring-[#0072BC]"
                />
                <label htmlFor="remember" className="ml-2 text-sm text-gray-600">
                  Manter conectado
                </label>
              </div>
              
              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center py-3 px-4 bg-[#00325A] text-white rounded-lg hover:bg-[#0072BC] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#00325A] transition-colors"
              >
                {loading ? (
                  "Entrando..."
                ) : (
                  <>
                    <LogIn className="w-5 h-5 mr-2" />
                    <span>Entrar</span>
                  </>
                )}
              </button>
            </form>
          </div>
          
          <p className="mt-8 text-center text-sm text-gray-500">
            © {new Date().getFullYear()} Portal GRS. Todos os direitos reservados.
          </p>
        </div>
      </div>
    </div>
  );
}