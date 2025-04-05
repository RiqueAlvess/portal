// src/components/ui/Tabs.tsx
'use client';

import { createContext, useContext, useState } from 'react';
import { clsx } from 'clsx';

type TabsContextType = {
  value: string;
  onValueChange: (value: string) => void;
};

const TabsContext = createContext<TabsContextType | undefined>(undefined);

export function Tabs({ 
  children, 
  defaultValue, 
  value, 
  onValueChange 
}: { 
  children: React.ReactNode; 
  defaultValue: string;
  value?: string;
  onValueChange?: (value: string) => void;
}) {
  const [internalValue, setInternalValue] = useState(defaultValue);
  
  const currentValue = value !== undefined ? value : internalValue;
  const handleValueChange = onValueChange || setInternalValue;

  return (
    <TabsContext.Provider value={{ value: currentValue, onValueChange: handleValueChange }}>
      <div className="w-full">{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={clsx("flex", className)}>
      {children}
    </div>
  );
}

export function TabsTrigger({ 
  children, 
  value,
  className 
}: { 
  children: React.ReactNode; 
  value: string;
  className?: string;
}) {
  const context = useContext(TabsContext);
  if (!context) throw new Error('TabsTrigger must be used within Tabs');
  
  const { value: currentValue, onValueChange } = context;
  const isActive = currentValue === value;
  
  return (
    <button
      type="button"
      onClick={() => onValueChange(value)}
      className={clsx(
        "border-b-2 border-transparent text-sm",
        isActive 
          ? "border-primary-light text-primary-dark" 
          : "text-secondary-medium hover:text-primary-dark hover:border-secondary-medium",
        className
      )}
    >
      {children}
    </button>
  );
}

export function TabsContent({ 
  children, 
  value,
  className
}: { 
  children: React.ReactNode; 
  value: string;
  className?: string;
}) {
  const context = useContext(TabsContext);
  if (!context) throw new Error('TabsContent must be used within Tabs');
  
  const { value: currentValue } = context;
  
  if (currentValue !== value) return null;
  
  return (
    <div className={className}>
      {children}
    </div>
  );
}