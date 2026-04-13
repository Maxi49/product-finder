"use client";
import { QRCodeSVG } from "qrcode.react";

interface Props {
  url: string;
  adminUrl?: string;
}

export default function QRDisplay({ url, adminUrl }: Props) {
  const copyUrl = () => navigator.clipboard.writeText(url);

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-green-200 text-center">
      <p className="text-green-700 font-semibold mb-1">Tu tienda esta publicada!</p>
      <p className="text-sm text-gray-500 mb-4">Comparti este QR o el link con tus clientes</p>
      <div className="flex justify-center mb-4">
        <QRCodeSVG value={url} size={160} />
      </div>
      <p className="text-xs text-gray-400 break-all mb-3">{url}</p>
      <button
        onClick={copyUrl}
        className="text-indigo-600 text-sm hover:underline mr-4"
      >
        Copiar link
      </button>
      {adminUrl && (
        <a href={adminUrl} className="text-gray-400 text-xs hover:underline">
          Editar tienda
        </a>
      )}
    </div>
  );
}
