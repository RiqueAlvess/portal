// src/components/ui/Card.tsx
import { ReactNode } from 'react';
import { clsx } from 'clsx';

interface CardProps {
  title?: string;
  children: ReactNode;
  className?: string;
  footer?: ReactNode;
}

export default function Card({ title, children, className, footer }: CardProps) {
  return (
    <div className={clsx("bg-white rounded-lg shadow-md overflow-hidden", className)}>
      {title && (
        <div className="border-b border-gray-200 px-6 py-4">
          <h3 className="text-lg font-medium text-gray-900">{title}</h3>
        </div>
      )}
      <div className="px-6 py-4">{children}</div>
      {footer && (
        <div className="bg-secondary-light px-6 py-3 border-t border-gray-200">
          {footer}
        </div>
      )}
    </div>
  );
}