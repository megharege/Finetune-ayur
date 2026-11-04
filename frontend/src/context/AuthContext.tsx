import React, { createContext, useContext, useState, ReactNode } from 'react';
import { User } from '../types';

interface AuthContextType {
  user: User;
  token: string | null;
  role: 'patient' | 'doctor' | 'admin';
  setRole: (role: 'patient' | 'doctor' | 'admin') => void;
  login: (userData: User, token: string) => void;
  logout: () => void;
}

const DEFAULT_USER: User = {
  id: 1,
  full_name: 'Ananya Sharma',
  email: 'patient@ayurllm.org',
  phone: '+91 9876543210',
  role: 'patient'
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User>(DEFAULT_USER);
  const [token, setToken] = useState<string | null>('demo-token-123');
  const [role, setRoleState] = useState<'patient' | 'doctor' | 'admin'>('patient');

  const setRole = (newRole: 'patient' | 'doctor' | 'admin') => {
    setRoleState(newRole);
    if (newRole === 'doctor') {
      setUser({
        id: 1,
        full_name: 'Dr. Vaidya Hitanshu Choraria',
        email: 'hitanshu@ayurllm.org',
        phone: '+91 9876543210',
        role: 'doctor'
      });
    } else if (newRole === 'admin') {
      setUser({
        id: 99,
        full_name: 'Central Hospital Registrar',
        email: 'admin@ayurllm.org',
        role: 'admin'
      });
    } else {
      setUser(DEFAULT_USER);
    }
  };

  const login = (userData: User, authToken: string) => {
    setUser(userData);
    setToken(authToken);
    setRoleState(userData.role);
  };

  const logout = () => {
    setUser(DEFAULT_USER);
    setToken(null);
    setRoleState('patient');
  };

  return (
    <AuthContext.Provider value={{ user, token, role, setRole, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
