import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Shelf to Store",
  description: "Crea tu tienda online en minutos",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body className="antialiased">{children}</body>
    </html>
  );
}
