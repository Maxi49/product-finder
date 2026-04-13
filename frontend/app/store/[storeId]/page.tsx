"use client";
import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { getStore, StoreOut } from "@/lib/api";
import Cart, { CartItem } from "@/components/Cart";
import QRDisplay from "@/components/QRDisplay";

export default function StorePage() {
  const { storeId } = useParams<{ storeId: string }>();
  const searchParams = useSearchParams();
  const isNew = searchParams.get("new") === "1";
  const adminToken = searchParams.get("token");

  const [store, setStore] = useState<StoreOut | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    getStore(storeId)
      .then((s) => {
        setStore(s);
        setCart(s.products.map((p) => ({ product: p, qty: 0 })));
      })
      .catch(() => setError(true));
  }, [storeId]);

  const handleQtyChange = (productId: string, delta: number) => {
    setCart((prev) =>
      prev.map((item) =>
        item.product.id === productId
          ? { ...item, qty: Math.max(0, item.qty + delta) }
          : item
      )
    );
  };

  const addToCart = (productId: string) => handleQtyChange(productId, 1);

  if (error) return <main className="min-h-screen flex items-center justify-center"><p className="text-gray-500">Tienda no encontrada.</p></main>;
  if (!store) return <main className="min-h-screen flex items-center justify-center"><p className="text-gray-400">Cargando...</p></main>;

  const publicUrl = typeof window !== "undefined" ? `${window.location.origin}/store/${storeId}` : "";
  const adminUrl = adminToken ? `${typeof window !== "undefined" ? window.location.origin : ""}/admin/${storeId}?token=${adminToken}` : undefined;

  return (
    <main className="min-h-screen bg-gray-50 pb-32">
      <div className="bg-white border-b border-gray-200 px-6 py-5">
        <h1 className="text-2xl font-bold text-gray-900">{store.name}</h1>
        <p className="text-sm text-gray-400">{store.products.length} productos</p>
      </div>

      <div className="max-w-2xl mx-auto p-6">
        {isNew && (
          <div className="mb-6">
            <QRDisplay url={publicUrl} adminUrl={adminUrl} />
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          {store.products.map((product) => {
            const qty = cart.find((i) => i.product.id === product.id)?.qty ?? 0;
            return (
              <div key={product.id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
                <div className="h-24 bg-gray-100 rounded-lg mb-3 flex items-center justify-center text-gray-300 text-3xl">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>
                </div>
                <p className="font-medium text-gray-900 text-sm mb-1 line-clamp-2">{product.name}</p>
                <p className="text-indigo-600 font-semibold mb-3">
                  {product.price != null ? `$${product.price}` : "Consultar precio"}
                </p>
                {qty === 0 ? (
                  <button
                    onClick={() => addToCart(product.id)}
                    className="w-full bg-indigo-600 text-white text-sm py-1.5 rounded-lg hover:bg-indigo-700"
                  >
                    Agregar
                  </button>
                ) : (
                  <div className="flex items-center justify-between">
                    <button onClick={() => handleQtyChange(product.id, -1)} className="w-8 h-8 bg-gray-100 rounded-full hover:bg-gray-200 flex items-center justify-center">-</button>
                    <span className="font-semibold">{qty}</span>
                    <button onClick={() => handleQtyChange(product.id, 1)} className="w-8 h-8 bg-indigo-100 text-indigo-700 rounded-full hover:bg-indigo-200 flex items-center justify-center">+</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <Cart items={cart} whatsapp={store.whatsapp} onQtyChange={handleQtyChange} />
    </main>
  );
}
