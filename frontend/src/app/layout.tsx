import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "InventorySaaS — Restaurant Inventory & Waste Tracker",
  description: "Simple inventory and waste tracking for independent restaurants. Square integration.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
