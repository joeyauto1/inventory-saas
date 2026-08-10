"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MERCHANT_ID = 1;

interface ReasonBreakdown {
  reason: string;
  total: string;
  count: number;
}

interface TopItem {
  item_name: string;
  total_cost: string;
  total_quantity: string;
}

export default function ReportsPage() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadReport = async () => {
    setLoading(true);
    const res = await fetch(`${API_URL}/api/reports/waste?merchant_id=${MERCHANT_ID}&days=${days}`);
    const json = await res.json();
    setData(json);
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <div className="flex items-center gap-3">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
          <button
            onClick={loadReport}
            disabled={loading}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-300 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {loading ? "Loading..." : "Run Report"}
          </button>
        </div>
      </div>

      {!data ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <svg className="w-12 h-12 mx-auto text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-gray-500">Select a period and run the report</p>
        </div>
      ) : (
        <>
          {/* Big number */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="text-sm text-gray-500">Total Waste Cost</div>
            <div className="text-3xl font-bold text-gray-900 mt-1">
              ${parseFloat(data.total_waste_cost).toFixed(2)}
            </div>
            <div className="text-xs text-gray-400 mt-1">Over the last {days} days</div>
          </div>

          {/* Breakdown by reason */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">By Reason</h2>
            {data.by_reason?.length === 0 ? (
              <p className="text-sm text-gray-400">No waste data</p>
            ) : (
              <div className="space-y-3">
                {data.by_reason?.map((r: ReasonBreakdown) => {
                  const total = parseFloat(r.total);
                  const grandTotal = parseFloat(data.total_waste_cost) || 1;
                  const pct = ((total / grandTotal) * 100).toFixed(0);
                  return (
                    <div key={r.reason}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="text-gray-700 capitalize">{r.reason}</span>
                        <span className="text-gray-500">
                          ${total.toFixed(2)} · {r.count} events · {pct}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div
                          className="bg-emerald-500 rounded-full h-2 transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Top wasted items */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Top Wasted Items</h2>
            {data.top_items?.length === 0 ? (
              <p className="text-sm text-gray-400">No waste data</p>
            ) : (
              <div className="space-y-2">
                {data.top_items?.map((item: TopItem, i: number) => (
                  <div key={item.item_name} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-bold text-gray-400 w-5">{i + 1}</span>
                      <span className="text-sm font-medium text-gray-900">{item.item_name}</span>
                    </div>
                    <div className="text-sm text-gray-500">
                      <span className="font-mono text-gray-900">${parseFloat(item.total_cost).toFixed(2)}</span>
                      <span className="ml-2">· {item.total_quantity} units</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
