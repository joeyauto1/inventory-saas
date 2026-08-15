"use client";

import { useState } from "react";

const LOCATION_ID = 1;

const REASONS = [
  { value: "spoilage", label: "Spoilage" },
  { value: "overprep", label: "Over-prepped" },
  { value: "dropped", label: "Dropped" },
  { value: "expired", label: "Expired" },
  { value: "trim", label: "Trim waste" },
  { value: "other", label: "Other" },
];

interface WasteEvent {
  id: number;
  item_name: string;
  variation_name: string;
  quantity: string;
  unit: string;
  reason: string;
  total_cost: string;
  notes: string;
  recorded_at: string;
}

export default function WastePage() {
  const [events, setEvents] = useState<WasteEvent[]>([]);
  const [loaded, setLoaded] = useState(false);
  
  // Form state
  const [itemName, setItemName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [reason, setReason] = useState("spoilage");
  const [costPerUnit, setCostPerUnit] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  const loadEvents = async () => {
    try {
      const res = await fetch("/api/waste?days=30", { credentials: "include" });
      const data = await res.json();
      setEvents(data.events || []);
      setLoaded(true);
    } catch {
      console.error("Failed to load waste events");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage("");

    try {
      const res = await fetch("/api/waste", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          location_id: LOCATION_ID,
          square_catalog_object_id: "manual",
          item_name: itemName,
          quantity: parseFloat(quantity) || 0,
          reason: reason,
          cost_per_unit: parseFloat(costPerUnit) || 0,
          notes: notes,
        }),
      });
      const data = await res.json();

      if (data.status === "ok") {
        setMessage(`Logged: $${data.event.total_cost} waste`);
        setItemName("");
        setQuantity("");
        setCostPerUnit("");
        setNotes("");
        loadEvents();
      } else {
        setMessage("Error logging waste");
      }
    } catch {
      setMessage("Network error");
    } finally {
      setSubmitting(false);
    }
  };

  const deleteEvent = async (id: number) => {
    await fetch(`/api/waste/${id}`, { method: "DELETE", credentials: "include" });
    loadEvents();
  };

  const totalCost = events.reduce((sum, e) => sum + parseFloat(e.total_cost || "0"), 0);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Waste Tracking</h1>

      {/* Log form */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Log Waste</h2>
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input
            type="text"
            placeholder="Item name"
            value={itemName}
            onChange={(e) => setItemName(e.target.value)}
            required
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
          <input
            type="number"
            step="0.01"
            placeholder="Quantity"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            required
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
          <select
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          >
            {REASONS.map((r) => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
          <input
            type="number"
            step="0.01"
            placeholder="Cost per unit ($)"
            value={costPerUnit}
            onChange={(e) => setCostPerUnit(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
          <div className="md:col-span-4 flex gap-3">
            <input
              type="text"
              placeholder="Notes (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-300 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {submitting ? "Saving..." : "Log Waste"}
            </button>
          </div>
        </form>
        {message && (
          <p className={`mt-3 text-sm ${message.startsWith("Logged") ? "text-emerald-600" : "text-red-500"}`}>
            {message}
          </p>
        )}
      </div>

      {/* Waste log */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Waste Log
          {totalCost > 0 && (
            <span className="ml-2 text-sm font-normal text-gray-500">
              — ${totalCost.toFixed(2)} total this month
            </span>
          )}
        </h2>
        <button
          onClick={loadEvents}
          className="text-sm text-emerald-600 hover:text-emerald-700 font-medium"
        >
          {loaded ? "Refresh" : "Load"}
        </button>
      </div>

      {!loaded ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <p className="text-gray-500">Click &ldquo;Load&rdquo; to view waste log</p>
        </div>
      ) : events.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <p className="text-gray-500">No waste events recorded yet</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left text-xs font-semibold text-gray-500 uppercase px-4 py-3">Date</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase px-4 py-3">Item</th>
                <th className="text-right text-xs font-semibold text-gray-500 uppercase px-4 py-3">Qty</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase px-4 py-3">Reason</th>
                <th className="text-right text-xs font-semibold text-gray-500 uppercase px-4 py-3">Cost</th>
                <th className="text-right text-xs font-semibold text-gray-500 uppercase px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {events.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50/50">
                  <td className="px-4 py-2.5 text-sm text-gray-500">
                    {new Date(e.recorded_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-900">
                    {e.item_name}
                    {e.variation_name && <span className="text-gray-400 ml-1">({e.variation_name})</span>}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-900">
                    {e.quantity} {e.unit}
                  </td>
                  <td className="px-4 py-2.5 text-sm">
                    <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 capitalize">
                      {e.reason}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-900">
                    ${parseFloat(e.total_cost).toFixed(2)}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      onClick={() => deleteEvent(e.id)}
                      className="text-xs text-gray-400 hover:text-red-500 transition-colors"
                    >
                      Delete
                    </button>
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
