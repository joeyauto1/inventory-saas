"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MERCHANT_ID = 1;

interface RecipeData {
  id: number;
  name: string;
  description: string;
  selling_price: string;
  portions: number;
  ingredient_count: number;
  total_cost: string;
  cost_per_portion: string;
  margin: string;
  margin_pct: string;
}

interface IngredientData {
  id: number;
  item_name: string;
  quantity: string;
  unit: string;
  cost_per_unit: string;
  line_total: string;
}

interface RecipeDetail {
  id: number;
  name: string;
  description: string;
  selling_price: string;
  portions: number;
  total_cost: string;
  cost_per_portion: string;
  margin: string;
  margin_pct: string;
  ingredients: IngredientData[];
}

export default function RecipesPage() {
  const [recipes, setRecipes] = useState<RecipeData[]>([]);
  const [loaded, setLoaded] = useState(false);
  
  // Create form
  const [name, setName] = useState("");
  const [sellingPrice, setSellingPrice] = useState("");
  const [portions, setPortions] = useState("1");
  const [submitting, setSubmitting] = useState(false);

  // Detail view
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<RecipeDetail | null>(null);

  // Add ingredient form
  const [ingItemName, setIngItemName] = useState("");
  const [ingQty, setIngQty] = useState("");
  const [ingUnit, setIngUnit] = useState("g");
  const [ingCost, setIngCost] = useState("");

  const loadRecipes = async () => {
    const res = await fetch(`${API_URL}/api/recipes?merchant_id=${MERCHANT_ID}`);
    const data = await res.json();
    setRecipes(data.recipes || []);
    setLoaded(true);
  };

  const createRecipe = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    await fetch(`${API_URL}/api/recipes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        merchant_id: MERCHANT_ID,
        name: name,
        selling_price: parseFloat(sellingPrice) || 0,
        portions: parseInt(portions) || 1,
      }),
    });
    setName("");
    setSellingPrice("");
    setPortions("1");
    setSubmitting(false);
    loadRecipes();
  };

  const viewRecipe = async (id: number) => {
    setSelected(id);
    const res = await fetch(`${API_URL}/api/recipes/${id}?merchant_id=${MERCHANT_ID}`);
    const data = await res.json();
    setDetail(data);
  };

  const addIngredient = async () => {
    if (!selected || !ingItemName || !ingQty) return;
    await fetch(
      `${API_URL}/api/recipes/${selected}/ingredients`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          merchant_id: MERCHANT_ID,
          square_catalog_object_id: "manual",
          item_name: ingItemName,
          quantity: parseFloat(ingQty) || 0,
          unit: ingUnit,
          cost_per_unit: parseFloat(ingCost) || 0,
        }),
      }
    );
    setIngItemName("");
    setIngQty("");
    setIngCost("");
    viewRecipe(selected);
  };

  const removeIngredient = async (ingId: number) => {
    if (!selected) return;
    await fetch(`${API_URL}/api/recipes/${selected}/ingredients/${ingId}?merchant_id=${MERCHANT_ID}`, {
      method: "DELETE",
    });
    viewRecipe(selected);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Recipe Costing</h1>

      {/* Create form */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">New Recipe</h2>
        <form onSubmit={createRecipe} className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">Recipe Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="e.g. Chicken Parmigiana"
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <div className="w-28">
            <label className="block text-xs text-gray-500 mb-1">Sell Price ($)</label>
            <input
              type="number"
              step="0.01"
              value={sellingPrice}
              onChange={(e) => setSellingPrice(e.target.value)}
              placeholder="24.00"
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <div className="w-20">
            <label className="block text-xs text-gray-500 mb-1">Portions</label>
            <input
              type="number"
              value={portions}
              onChange={(e) => setPortions(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-300 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Create
          </button>
        </form>
      </div>

      {/* Recipe list */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Your Recipes</h2>
        <button onClick={loadRecipes} className="text-sm text-emerald-600 hover:text-emerald-700 font-medium">
          {loaded ? "Refresh" : "Load"}
        </button>
      </div>

      {!loaded ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <p className="text-gray-500">Click &ldquo;Load&rdquo; to view recipes</p>
        </div>
      ) : recipes.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <p className="text-gray-500">No recipes yet — create your first one above</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {recipes.map((r) => (
            <button
              key={r.id}
              onClick={() => viewRecipe(r.id)}
              className={`text-left bg-white rounded-lg border p-4 hover:border-emerald-300 transition-colors ${
                selected === r.id ? "border-emerald-500 ring-2 ring-emerald-100" : "border-gray-200"
              }`}
            >
              <div className="font-semibold text-gray-900">{r.name}</div>
              <div className="flex gap-4 mt-2 text-sm">
                <span className="text-gray-500">
                  Cost: <span className="font-mono text-gray-900">${parseFloat(r.cost_per_portion).toFixed(2)}/ea</span>
                </span>
                <span className="text-gray-500">
                  Margin: <span className={`font-mono font-medium ${parseFloat(r.margin) >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                    {r.margin_pct}%
                  </span>
                </span>
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {r.ingredient_count} ingredients · {r.portions} portions · sells at ${parseFloat(r.selling_price).toFixed(2)}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Recipe detail */}
      {detail && (
        <div className="bg-white rounded-lg border border-emerald-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">{detail.name}</h2>
            <button onClick={() => setSelected(null)} className="text-sm text-gray-400 hover:text-gray-600">
              Close
            </button>
          </div>

          {/* Cost summary */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[
              { label: "Sell Price", value: `$${parseFloat(detail.selling_price).toFixed(2)}` },
              { label: "Cost/Portion", value: `$${parseFloat(detail.cost_per_portion).toFixed(2)}` },
              { label: "Margin", value: `$${parseFloat(detail.margin).toFixed(2)}` },
              { label: "Margin %", value: `${detail.margin_pct}%` },
            ].map((s) => (
              <div key={s.label} className="bg-gray-50 rounded-lg p-3 text-center">
                <div className="text-xs text-gray-500">{s.label}</div>
                <div className="text-lg font-bold text-gray-900">{s.value}</div>
              </div>
            ))}
          </div>

          {/* Ingredients */}
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Ingredients ({detail.ingredients?.length || 0})
          </h3>
          <div className="space-y-2 mb-4">
            {detail.ingredients?.map((ing: IngredientData) => (
              <div key={ing.id} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <span className="text-sm font-medium text-gray-900">{ing.item_name}</span>
                  <span className="text-sm text-gray-500 ml-2">
                    {ing.quantity} {ing.unit} @ ${parseFloat(ing.cost_per_unit).toFixed(2)}/unit
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-mono text-gray-900">${parseFloat(ing.line_total).toFixed(2)}</span>
                  <button
                    onClick={() => removeIngredient(ing.id)}
                    className="text-xs text-gray-400 hover:text-red-500"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Add ingredient */}
          <div className="flex gap-2 items-end pt-4 border-t border-gray-100">
            <div className="flex-1">
              <input
                type="text"
                placeholder="Ingredient name"
                value={ingItemName}
                onChange={(e) => setIngItemName(e.target.value)}
                className="w-full px-3 py-1.5 border border-gray-200 rounded text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <div className="w-20">
              <input
                type="number"
                step="0.01"
                placeholder="Qty"
                value={ingQty}
                onChange={(e) => setIngQty(e.target.value)}
                className="w-full px-3 py-1.5 border border-gray-200 rounded text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <div className="w-16">
              <select
                value={ingUnit}
                onChange={(e) => setIngUnit(e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-200 rounded text-sm"
              >
                {["g", "kg", "ml", "L", "each", "oz", "lb", "cup"].map((u) => (
                  <option key={u} value={u}>{u}</option>
                ))}
              </select>
            </div>
            <div className="w-24">
              <input
                type="number"
                step="0.01"
                placeholder="$/unit"
                value={ingCost}
                onChange={(e) => setIngCost(e.target.value)}
                className="w-full px-3 py-1.5 border border-gray-200 rounded text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <button
              onClick={addIngredient}
              className="px-4 py-1.5 bg-gray-800 hover:bg-gray-900 text-white text-sm font-medium rounded transition-colors"
            >
              Add
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
