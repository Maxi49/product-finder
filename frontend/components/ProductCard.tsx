import { DetectedProduct } from "@/lib/api";

interface Props {
  product: DetectedProduct;
  index: number;
  onEdit: (index: number, product: DetectedProduct) => void;
  onRemove: (index: number) => void;
}

const CONFIDENCE_BADGE: Record<string, string> = {
  high: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-red-100 text-red-700",
};

export default function ProductCard({ product, index, onEdit, onRemove }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 flex items-center gap-4 shadow-sm">
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">{product.name}</p>
        <p className="text-sm text-gray-500">
          {product.price != null ? `$${product.price}` : "Precio no detectado"}
        </p>
      </div>
      <span className={`text-xs px-2 py-1 rounded-full font-medium ${CONFIDENCE_BADGE[product.confidence]}`}>
        {product.confidence}
      </span>
      <button
        onClick={() => onEdit(index, product)}
        className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
      >
        Editar
      </button>
      <button
        onClick={() => onRemove(index)}
        className="text-red-400 hover:text-red-600 text-sm"
      >
        x
      </button>
    </div>
  );
}
