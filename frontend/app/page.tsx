"use client";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { processImages } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files)
      .filter((f) => f.type.startsWith("image/"))
      .slice(0, 3);
    setFiles((prev) => [...prev, ...dropped].slice(0, 3));
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []).slice(0, 3);
    setFiles(selected);
  };

  const handleSubmit = async () => {
    if (files.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const products = await processImages(files);
      sessionStorage.setItem("detected_products", JSON.stringify(products));
      router.push("/setup/new");
    } catch {
      setError("No pudimos procesar las imagenes. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-indigo-50 to-white flex flex-col items-center justify-center p-8">
      <div className="max-w-xl w-full">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Shelf to Store</h1>
        <p className="text-gray-500 mb-8 text-lg">
          Saca fotos de tus estantes y publica tu tienda online en minutos.
        </p>

        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="border-2 border-dashed border-indigo-300 rounded-2xl p-10 text-center cursor-pointer hover:border-indigo-500 transition-colors"
          onClick={() => document.getElementById("file-input")?.click()}
        >
          <p className="text-gray-400 mb-2">Arrastra hasta 3 fotos aca</p>
          <p className="text-sm text-gray-300">o hace clic para seleccionar</p>
          <input
            id="file-input"
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={handleFileInput}
          />
        </div>

        {files.length > 0 && (
          <div className="flex gap-3 mt-4">
            {files.map((f, i) => (
              <div key={i} className="relative">
                <img
                  src={URL.createObjectURL(f)}
                  alt={f.name}
                  className="w-24 h-24 object-cover rounded-xl"
                />
                <button
                  onClick={(e) => { e.stopPropagation(); setFiles((prev) => prev.filter((_, j) => j !== i)); }}
                  className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center"
                >x</button>
              </div>
            ))}
          </div>
        )}

        {error && <p className="text-red-500 mt-3 text-sm">{error}</p>}

        <button
          onClick={handleSubmit}
          disabled={files.length === 0 || loading}
          className="mt-6 w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-semibold py-3 rounded-xl transition-colors"
        >
          {loading ? "Analizando fotos con IA..." : "Analizar fotos"}
        </button>
      </div>
    </main>
  );
}
