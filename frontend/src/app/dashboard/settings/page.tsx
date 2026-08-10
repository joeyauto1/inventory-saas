"use client";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {/* Subscription */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Subscription</h2>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
                Trial
              </span>
              <span className="text-sm text-gray-900 font-medium">InventorySaaS Pro</span>
            </div>
            <p className="text-sm text-gray-500 mt-1">$79/mo per location · 14-day free trial</p>
            <p className="text-xs text-gray-400 mt-0.5">Trial ends in 14 days</p>
          </div>
          <a
            href="#"
            className="px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Manage in Stripe
          </a>
        </div>
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
