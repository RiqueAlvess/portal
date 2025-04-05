// src/components/admin/DeleteConfirmation.tsx
'use client';

import Modal from '@/components/ui/Modal';
import { AlertTriangle } from 'lucide-react';

type DeleteConfirmationProps = {
  title: string;
  message: string;
  onCancel: () => void;
  onConfirm: () => void;
};

export default function DeleteConfirmation({
  title,
  message,
  onCancel,
  onConfirm,
}: DeleteConfirmationProps) {
  return (
    <Modal
      isOpen={true}
      onClose={onCancel}
      title={title}
      size="sm"
    >
      <div className="flex items-start">
        <div className="flex-shrink-0 mr-3">
          <AlertTriangle className="h-6 w-6 text-accent" />
        </div>
        <div>
          <p className="text-sm text-secondary-medium">{message}</p>
          <p className="mt-2 text-sm text-secondary-medium">
            Esta ação não pode ser desfeita.
          </p>
        </div>
      </div>
      
      <div className="mt-6 flex justify-end space-x-3">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-secondary-medium bg-white hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-accent hover:bg-red-700"
        >
          Excluir
        </button>
      </div>
    </Modal>
  );
}