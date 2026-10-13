"use client";

import { useEffect, useState } from "react";
import { authHeaders, getToken } from "@/lib/auth";
import Nav from "@/components/Nav";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AdsPage() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState({ name: "", platform: "meta", budget: "", objective: "awareness" });

  async function load() {
    const [c, s] = await Promise.all([
      fetch(`${API}/api/v1/ads/campaigns`).then((r) => r.json()).catch(() => []),
      fetch(`${API}/api/v1/ads/summary`).then((r) => r.json()).catch(() => null),
    ]);
    setCampaigns(c);
    setSummary(s);
  }

  useEffect(() => {
    load();
  }, []);

  async function seed() {
    if (!getToken()) return setMsg("Login required");
    await fetch(`${API}/api/v1/ads/seed-demo`, { method: "POST", headers: authHeaders() });
    setMsg("Demo campaigns seeded");
    load();
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!getToken()) return setMsg("Login required");
    const res = await fetch(`${API}/api/v1/ads/campaigns`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({
        name: form.name,
        platform: form.platform,
        budget: form.budget ? Number(form.budget) : null,
        objective: form.objective,
        status: "draft",
      }),
    });
    if (res.ok) {
      setMsg("Campaign created");
      setForm({ name: "", platform: "meta", budget: "", objective: "awareness" });
      load();
    }
  }

  async function syncMetrics(id: string) {
    if (!getToken()) return;
    const res = await fetch(`${API}/api/v1/ads/campaigns/${id}/sync-metrics`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (res.ok) {
      setMsg("Metrics synced (synthetic if no Ads API keys)");
      load();
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Digital Advertising</h1>
          <p className="text-sm text-slate-400">Meta · Google · X · TikTok · YouTube — placeholders until credentials</p>
        </div>
        <Nav />
      </header>
      {msg && <p className="mb-4 text-sm text-amber-300">{msg}</p>}

      {summary && (
        <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
            <div className="text-xs text-slate-400">Campaigns</div>
            <div className="text-2xl font-bold">{summary.total_campaigns}</div>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
            <div className="text-xs text-slate-400">Active</div>
            <div className="text-2xl font-bold text-emerald-400">{summary.active}</div>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
            <div className="text-xs text-slate-400">Total spend</div>
            <div className="text-2xl font-bold">₦{Number(summary.total_spend).toLocaleString()}</div>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-3 text-xs">
            {Object.entries(summary.by_platform || {}).map(([k, v]) => (
              <div key={k}>{k}: {v as number}</div>
            ))}
          </div>
        </div>
      )}

      <div className="mb-4 flex gap-2">
        <button onClick={seed} className="rounded bg-slate-700 px-3 py-2 text-sm">Seed demo</button>
      </div>

      <form onSubmit={create} className="mb-6 grid gap-2 rounded-lg border border-slate-800 bg-slate-900 p-4 md:grid-cols-5">
        <input className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm" placeholder="Campaign name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <select className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm" value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })}>
          {["meta", "google", "x", "tiktok", "youtube"].map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <input className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm" placeholder="Budget (₦)" value={form.budget} onChange={(e) => setForm({ ...form, budget: e.target.value })} />
        <input className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm" placeholder="Objective" value={form.objective} onChange={(e) => setForm({ ...form, objective: e.target.value })} />
        <button type="submit" className="rounded bg-emerald-700 px-3 py-2 text-sm font-medium">Create</button>
      </form>

      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-4 py-2 text-left">Name</th>
              <th className="px-4 py-2 text-left">Platform</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-right">Budget</th>
              <th className="px-4 py-2 text-right">Spend</th>
              <th className="px-4 py-2 text-right">CTR</th>
              <th className="px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr key={c.id} className="border-t border-slate-800">
                <td className="px-4 py-2">{c.name}</td>
                <td className="px-4 py-2 uppercase text-xs">{c.platform}</td>
                <td className="px-4 py-2">{c.status}</td>
                <td className="px-4 py-2 text-right">{c.budget ? `₦${Number(c.budget).toLocaleString()}` : "—"}</td>
                <td className="px-4 py-2 text-right">₦{Number(c.spend).toLocaleString()}</td>
                <td className="px-4 py-2 text-right">{c.metrics?.ctr ?? "—"}%</td>
                <td className="px-4 py-2">
                  <button onClick={() => syncMetrics(c.id)} className="text-xs text-emerald-400 hover:underline">Sync metrics</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
