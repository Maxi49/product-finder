"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DetectedProduct, createStore } from "@/lib/api";
import ProductCard from "@/components/ProductCard";
import EditModal from "@/components/EditModal";

export default function SetupPage() {
  const router = useRouter();
  const [products, setProducts] = useState<DetectedProduct[]>([]);
  const [storeName, setStoreName] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [editing, setEditing] = useState<{ index: number; product: DetectedProduct } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem("detected_products");
    if (!raw) { router.push("/"); return; }
    setProducts(JSON.parse(raw));
  }, [router]);

  const handleEdit = (index: number, product: DetectedProduct) => {
    setEditing({ index, product });
  };

  const handleSaveEdit = (updated: DetectedProduct) => {
    setProducts((prev) => prev.map((p, i) => (i === editing!.index ? updated : p)));
    setEditing(null);
  };

  const handleRemove = (index: number) => {
    setProducts((prev) => prev.filter((_, i) => i !== index));
  };

  const handlePublish = async () => {
    if (!storeName.trim() || products.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const result = await createStore(
        storeName.trim(),
        whatsapp || null,
        products.map((p, i) => ({ name: p.name, price: p.price, position: i }))
      );
      router.push(`/store/${result.store_id}?new=1&token=${result.admin_token}`);
    } catch {
      setError("Error al publicar. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  if (products.length === 0) return null;

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Revisa tus productos</h1>
        <p className="text-gray-500 mb-6 text-sm">
          Claude detecto {products.length} productos. Edita lo que sea necesario.
        </p>

        <div className="space-y-3 mb-8">
          {products.map((p, i) => (
            <ProductCard key={i} product={p} index={i} onEdit={handleEdit} onRemove={handleRemove} />
          ))}
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200">
          <h2 className="font-semibold text-gray-900 mb-4">Datos de tu tienda</h2>
          <label className="block text-sm text-gray-600 mb-1">Nombre de la tienda *</label>
          <input
            className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            value={storeName}
            onChange={(e) => setStoreName(e.target.value)}
            placeholder="Ej: Almacen Don Juan"
          />
          <label className="block text-sm text-gray-600 mb-1">
            WhatsApp (opcional, para recibir pedidos)
          </label>
          <input
            className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-6"
            value={whatsapp}
            onChange={(e) => setWhatsapp(e.target.value)}
            placeholder="5491112345678"
          />
          {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
          <button
            onClick={handlePublish}
            disabled={!storeName.trim() || products.length === 0 || loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-semibold py-3 rounded-xl transition-colors"
          >
            {loading ? "Publicando..." : "Publicar tienda"}
          </button>
        </div>
      </div>

      {editing && (
        <EditModal
          product={editing.product}
          onSave={handleSaveEdit}
          onClose={() => setEditing(null)}
        />
      )}
    </main>
  );
}
