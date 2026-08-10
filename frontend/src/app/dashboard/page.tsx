export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "Inventory Items", value: "—", sub: "Synced from Square" },
          { label: "Waste This Month", value: "—", sub: "No data yet" },
          { label: "Recipes Tracked", value: "—", sub: "Add your first recipe" },
        ].map((card) => (
          <div key={card.label} className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="text-sm text-gray-500">{card.label}</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">{card.value}</div>
            <div className="text-xs text-gray-400 mt-1">{card.sub}</div>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Setup</h2>
        <div className="space-y-3">
          {[
            { step: 1, text: "Sync your inventory from Square", href: "/dashboard/inventory", done: false },
            { step: 2, text: "Log your first waste event", href: "/dashboard/waste", done: false },
            { step: 3, text: "Build a recipe with costs", href: "/dashboard/recipes", done: false },
          ].map((item) => (
            <a
              key={item.step}
              href={item.href}
              className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 hover:border-emerald-200 hover:bg-emerald-50/50 transition-colors"
            >
              <span className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-500">
                {item.step}
              </span>
              <span className="text-sm text-gray-700">{item.text}</span>
              <svg className="w-4 h-4 ml-auto text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
