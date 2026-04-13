"use client";
import { useState } from "react";
import { DetectedProduct } from "@/lib/api";

interface Props {
  product: DetectedProduct;
  onSave: (updated: DetectedProduct) => void;
  onClose: () => void;
}

export default function EditModal({ product, onSave, onClose }: Props) {
  const [name, setName] = useState(product.name);
  const [price, setPrice] = useState(product.price?.toString() ?? "");

  const handleSave = () => {
    onSave({
      ...product,
      name: name.trim(),
      price: price ? parseFloat(price) : null,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
        <h2 className="text-lg font-semibold mb-4">Editar producto</h2>
        <label className="block text-sm text-gray-600 mb-1">Nombre</label>
        <input
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <label className="block text-sm text-gray-600 mb-1">Precio ($)</label>
        <input
          type="number"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-6 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          placeholder="Dejar vacio si no tiene precio"
        />
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border border-gray-300 text-gray-600 py-2 rounded-xl hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim()}
            className="flex-1 bg-indigo-600 text-white py-2 rounded-xl hover:bg-indigo-700 disabled:bg-gray-300"
          >
            Guardar
          </button>
        </div>
      </div>
    </div>
  );
}
