"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [loading, setLoading] = useState(false);

  const handleConnect = () => {
    setLoading(true);
    window.location.href = `${API_URL}/auth/login`;
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="max-w-md w-full text-center space-y-8">
        {/* Logo / Icon */}
        <div className="mx-auto w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center">
          <svg className="w-8 h-8 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>

        <div className="space-y-3">
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">
            InventorySaaS
          </h1>
          <p className="text-lg text-gray-500">
            Inventory and waste tracking for independent restaurants.
            Built for Square.
          </p>
        </div>

        {/* Features */}
        <div className="grid grid-cols-2 gap-3 text-left">
          {[
            { title: "Live Inventory", desc: "Synced from your Square POS" },
            { title: "Waste Tracking", desc: "Log what you throw away" },
            { title: "Recipe Costing", desc: "Know your plate costs" },
            { title: "Reports", desc: "Where your money is going" },
          ].map((f) => (
            <div key={f.title} className="bg-white rounded-lg p-3 border border-gray-200">
              <div className="font-semibold text-sm text-gray-900">{f.title}</div>
              <div className="text-xs text-gray-500 mt-0.5">{f.desc}</div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="space-y-3">
          <button
            onClick={handleConnect}
            disabled={loading}
            className="w-full py-3 px-6 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-400 text-white font-semibold rounded-lg transition-colors"
          >
            {loading ? "Redirecting..." : "Connect Your Square Account"}
          </button>
          <p className="text-xs text-gray-400">
            Free 14-day trial · $79/mo after · Cancel anytime
          </p>
        </div>

        {/* Trust badges */}
        <div className="flex items-center justify-center gap-4 text-xs text-gray-400">
          <span>Square App Marketplace</span>
          <span>·</span>
          <span>No revenue share</span>
          <span>·</span>
          <span>AES-256 encrypted</span>
        </div>
      </div>
    </div>
  );
}
