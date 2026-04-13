"use client";
import { ProductOut } from "@/lib/api";

export interface CartItem {
  product: ProductOut;
  qty: number;
}

interface Props {
  items: CartItem[];
  whatsapp: string | null;
  onQtyChange: (productId: string, delta: number) => void;
}

export default function Cart({ items, whatsapp, onQtyChange }: Props) {
  const filled = items.filter((i) => i.qty > 0);
  const total = filled.reduce((sum, i) => sum + (i.product.price ?? 0) * i.qty, 0);

  const handleWhatsApp = () => {
    const lines = filled.map((i) => `${i.product.name} x${i.qty}`).join(", ");
    const msg = `Hola! Quiero pedir: ${lines}. Total estimado: $${total.toFixed(0)}`;
    const number = whatsapp ?? "";
    window.open(`https://wa.me/${number}?text=${encodeURIComponent(msg)}`, "_blank");
  };

  if (filled.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 bg-white rounded-2xl shadow-xl border border-gray-200 p-4 w-72 z-40">
      <h3 className="font-semibold text-gray-800 mb-3">Tu pedido</h3>
      <div className="space-y-2 mb-4 max-h-40 overflow-y-auto">
        {filled.map((item) => (
          <div key={item.product.id} className="flex items-center justify-between text-sm">
            <span className="text-gray-700 truncate flex-1">{item.product.name}</span>
            <div className="flex items-center gap-2 ml-2">
              <button onClick={() => onQtyChange(item.product.id, -1)} className="w-6 h-6 bg-gray-100 rounded-full text-gray-600 hover:bg-gray-200 flex items-center justify-center text-xs">-</button>
              <span className="w-4 text-center">{item.qty}</span>
              <button onClick={() => onQtyChange(item.product.id, 1)} className="w-6 h-6 bg-gray-100 rounded-full text-gray-600 hover:bg-gray-200 flex items-center justify-center text-xs">+</button>
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between text-sm font-medium mb-3">
        <span>Total estimado</span>
        <span>${total.toFixed(0)}</span>
      </div>
      <button
        onClick={handleWhatsApp}
        className="w-full bg-green-500 hover:bg-green-600 text-white font-semibold py-2 rounded-xl transition-colors"
      >
        Pedir por WhatsApp
      </button>
    </div>
  );
}
