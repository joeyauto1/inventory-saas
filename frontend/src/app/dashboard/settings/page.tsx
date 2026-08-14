"use client";

import { useCallback, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type SubscriptionStatus = "trialing" | "active" | "canceled" | "past_due" | "unknown";

export default function SettingsPage() {
  const [status, setStatus] = useState<SubscriptionStatus>("unknown");
  const [trialEndsAt, setTrialEndsAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/billing/status`, {
        credentials: "include",
      });
      if (res.status === 401) {
        setStatus("unknown");
        setError("Not signed in — connect Square first.");
        return;
      }
      const data = await res.json();
      setStatus(data.status || "unknown");
      setTrialEndsAt(data.trial_ends_at || null);
      setError("");
    } catch {
      setError("Could not reach the server.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const checkout = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/api/billing/checkout`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        setError(`Checkout failed (HTTP ${res.status}).`);
        return;
      }
      const data = await res.json();
      // Subscription state arrives via the webhook — this URL only redirects.
      window.location.href = data.url;
    } catch {
      setError("Could not reach the server.");
    } finally {
      setBusy(false);
    }
  };

  const openPortal = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/api/billing/portal`, {
        credentials: "include",
      });
      if (!res.ok) {
        setError(`Could not open Stripe portal (HTTP ${res.status}).`);
        return;
      }
      const data = await res.json();
      window.location.href = data.url;
    } catch {
      setError("Could not reach the server.");
    } finally {
      setBusy(false);
    }
  };

  const statusLabel: Record<SubscriptionStatus, string> = {
    trialing: "Trial",
    active: "Active",
    canceled: "Canceled",
    past_due: "Past due",
    unknown: "Unknown",
  };

  const statusColor: Record<SubscriptionStatus, string> = {
    trialing: "bg-emerald-100 text-emerald-700",
    active: "bg-emerald-100 text-emerald-700",
    canceled: "bg-gray-100 text-gray-600",
    past_due: "bg-red-100 text-red-700",
    unknown: "bg-gray-100 text-gray-600",
  };

  const trialEndsText = trialEndsAt
    ? new Date(trialEndsAt).toLocaleDateString()
    : null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {/* Subscription */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Subscription</h2>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColor[status]}`}>
                {loading ? "Loading…" : statusLabel[status]}
              </span>
              <span className="text-sm text-gray-900 font-medium">InventorySaaS Pro</span>
            </div>
            <p className="text-sm text-gray-500 mt-1">$79/mo per location · 14-day free trial</p>
            {trialEndsText && (
              <p className="text-xs text-gray-400 mt-0.5">Trial ends {trialEndsText}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {status !== "active" && (
              <button
                onClick={checkout}
                disabled={busy}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-300 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {busy ? "Redirecting…" : status === "canceled" || status === "past_due" ? "Resubscribe" : "Start subscription"}
              </button>
            )}
            {(status === "active" || status === "past_due" || status === "trialing") && (
              <button
                onClick={openPortal}
                disabled={busy}
                className="px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Manage in Stripe
              </button>
            )}
          </div>
        </div>
        {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
      </div>

      {/* Connected Square */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Square Connection</h2>
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 bg-emerald-400 rounded-full" />
          <span className="text-sm text-gray-700">Connected to Square</span>
        </div>
        <div className="mt-3 text-sm text-gray-500">
          <p>Your inventory syncs automatically from your Square catalog.</p>
        </div>
        <button className="mt-3 text-sm text-red-500 hover:text-red-600 font-medium">
          Disconnect Square
        </button>
      </div>

      {/* Locations */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Locations</h2>
        <p className="text-sm text-gray-500">
          Locations are synced from your Square account automatically.
        </p>
      </div>

      {/* Danger zone */}
      <div className="bg-white rounded-lg border border-red-200 p-5">
        <h2 className="text-lg font-semibold text-red-700 mb-2">Danger Zone</h2>
        <p className="text-sm text-gray-500 mb-3">
          Deleting your account will permanently remove all waste logs, recipes, and settings.
        </p>
        <button className="px-4 py-2 bg-red-50 hover:bg-red-100 text-red-600 text-sm font-medium rounded-lg border border-red-200 transition-colors">
          Delete Account
        </button>
      </div>
    </div>
  );
}
