"use client";
import { useEffect, useState } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { getStore, updateStore, StoreOut, DetectedProduct } from "@/lib/api";
import ProductCard from "@/components/ProductCard";
import EditModal from "@/components/EditModal";

export default function AdminPage() {
  const { storeId } = useParams<{ storeId: string }>();
  const token = useSearchParams().get("token") ?? "";
  const router = useRouter();

  const [store, setStore] = useState<StoreOut | null>(null);
  const [products, setProducts] = useState<DetectedProduct[]>([]);
  const [storeName, setStoreName] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [editing, setEditing] = useState<{ index: number; product: DetectedProduct } | null>(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!token) { router.push("/"); return; }
    getStore(storeId).then((s) => {
      setStore(s);
      setStoreName(s.name);
      setWhatsapp(s.whatsapp ?? "");
      setProducts(s.products.map((p) => ({
        name: p.name, price: p.price, confidence: "high" as const,
      })));
    });
  }, [storeId, token, router]);

  const handleSave = async () => {
    setLoading(true);
    await updateStore(storeId, token, storeName, whatsapp || null,
      products.map((p, i) => ({ name: p.name, price: p.price, position: i }))
    );
    setLoading(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (!store) return null;

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Administrar tienda</h1>
          <a href={`/store/${storeId}`} className="text-indigo-600 text-sm hover:underline">Ver tienda</a>
        </div>

        <div className="space-y-3 mb-6">
          {products.map((p, i) => (
            <ProductCard key={i} product={p} index={i}
              onEdit={(idx, prod) => setEditing({ index: idx, product: prod })}
              onRemove={(idx) => setProducts((prev) => prev.filter((_, j) => j !== idx))} />
          ))}
        </div>

        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-200 mb-4">
          <label className="block text-sm text-gray-600 mb-1">Nombre de la tienda</label>
          <input className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-3"
            value={storeName} onChange={(e) => setStoreName(e.target.value)} />
          <label className="block text-sm text-gray-600 mb-1">WhatsApp</label>
          <input className="w-full border border-gray-300 rounded-lg px-3 py-2"
            value={whatsapp} onChange={(e) => setWhatsapp(e.target.value)} />
        </div>

        <button onClick={handleSave} disabled={loading}
          className="w-full bg-indigo-600 text-white font-semibold py-3 rounded-xl hover:bg-indigo-700 disabled:bg-gray-300">
          {saved ? "Guardado!" : loading ? "Guardando..." : "Guardar cambios"}
        </button>
      </div>

      {editing && (
        <EditModal product={editing.product}
          onSave={(u) => { setProducts((prev) => prev.map((p, i) => i === editing.index ? u : p)); setEditing(null); }}
          onClose={() => setEditing(null)} />
      )}
    </main>
  );
}
