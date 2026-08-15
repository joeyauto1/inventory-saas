"use client";

import { useState } from "react";

interface InventoryItem {
  catalog_object_id: string;
  item_name: string;
  variation_name: string;
  quantity: number;
  status: "ok" | "low" | "out";
  location_id: string;
  calculated_at: string;
}

export default function InventoryPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [synced, setSynced] = useState(false);

  const syncInventory = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/inventory", { credentials: "include" });
      const data = await res.json();
      setItems(data.items || []);
      setSynced(true);
    } catch (err) {
      console.error("Failed to sync inventory:", err);
    } finally {
      setLoading(false);
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "out": return "bg-red-100 text-red-700";
      case "low": return "bg-amber-100 text-amber-700";
      case "ok": return "bg-emerald-100 text-emerald-700";
      default: return "bg-gray-100 text-gray-600";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Inventory</h1>
        <button
          onClick={syncInventory}
          disabled={loading}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-300 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {loading ? "Syncing..." : synced ? "Refresh" : "Sync from Square"}
        </button>
      </div>

      {!synced ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <svg className="w-12 h-12 mx-auto text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
          </svg>
          <p className="text-gray-500 mb-2">No inventory data loaded</p>
          <p className="text-sm text-gray-400">Click &ldquo;Sync from Square&rdquo; to pull your current stock levels</p>
        </div>
      ) : items.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <p className="text-gray-500">No inventory-tracked items found in your Square catalog</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left text-xs font-semibold text-gray-500 uppercase px-4 py-3">Item</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase px-4 py-3">Variation</th>
                <th className="text-right text-xs font-semibold text-gray-500 uppercase px-4 py-3">Stock</th>
                <th className="text-right text-xs font-semibold text-gray-500 uppercase px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {items.map((item) => (
                <tr key={item.catalog_object_id} className="hover:bg-gray-50/50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{item.item_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{item.variation_name || "—"}</td>
                  <td className="px-4 py-3 text-sm text-right font-mono text-gray-900">{item.quantity}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(item.status)}`}>
                      {item.status === "out" ? "Out" : item.status === "low" ? "Low" : "OK"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
