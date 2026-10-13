"use client";

import { useEffect, useState } from "react";
import { authHeaders, getToken } from "@/lib/auth";
import Nav from "@/components/Nav";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function InfluencePage() {
  const [influencers, setInfluencers] = useState<any[]>([]);
  const [rapid, setRapid] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [title, setTitle] = useState("");

  async function load() {
    const [i, r] = await Promise.all([
      fetch(`${API}/api/v1/influence/influencers`).then((x) => x.json()).catch(() => []),
      fetch(`${API}/api/v1/influence/rapid-response`).then((x) => x.json()).catch(() => []),
    ]);
    setInfluencers(i);
    setRapid(r);
  }

  useEffect(() => {
    load();
  }, []);

  async function seedInf() {
    if (!getToken()) return setMsg("Login required");
    await fetch(`${API}/api/v1/influence/influencers/seed-demo`, { method: "POST", headers: authHeaders() });
    setMsg("Demo influencers seeded");
    load();
  }

  async function createRapid(e: React.FormEvent) {
    e.preventDefault();
    if (!getToken()) return setMsg("Login required");
    const res = await fetch(`${API}/api/v1/influence/rapid-response`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ title, auto_draft: true, narrative_type: "counter_narrative" }),
    });
    if (res.ok) {
      setMsg("Counter-narrative draft queued for review");
      setTitle("");
      load();
    }
  }

  async function review(id: string, action: string) {
    if (!getToken()) return;
    const res = await fetch(`${API}/api/v1/influence/rapid-response/${id}/review`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    if (res.ok) {
      setMsg(`Rapid response ${action}d`);
      load();
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Amplify & Influence</h1>
          <p className="text-sm text-slate-400">Influencers · Rapid response · Counter-narratives (human approval only)</p>
        </div>
        <Nav />
      </header>
      {msg && <p className="mb-4 text-sm text-amber-300">{msg}</p>}

      <div className="mb-4">
        <button onClick={seedInf} className="rounded bg-slate-700 px-3 py-2 text-sm">Seed influencers</button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 px-4 py-3 font-semibold">Influencer intelligence</div>
          <ul className="max-h-80 overflow-y-auto divide-y divide-slate-800">
            {influencers.map((i) => (
              <li key={i.id} className="px-4 py-3 text-sm">
                <div className="flex justify-between">
                  <span className="font-medium">{i.display_name || i.handle}</span>
                  <span className="text-emerald-400 font-mono">{i.influence_score}</span>
                </div>
                <div className="text-xs text-slate-400">
                  {i.platform} · {i.category} · reach {i.reach.toLocaleString()} · eng {i.engagement_rate}%
                </div>
              </li>
            ))}
            {influencers.length === 0 && <li className="p-4 text-slate-500 text-sm">No influencers – seed demo</li>}
          </ul>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 px-4 py-3 font-semibold">Rapid response queue</div>
          <form onSubmit={createRapid} className="flex gap-2 border-b border-slate-800 p-3">
            <input
              className="flex-1 rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              placeholder="Issue / narrative to counter…"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
            <button type="submit" className="rounded bg-emerald-700 px-3 py-2 text-sm">Queue draft</button>
          </form>
          <ul className="max-h-80 overflow-y-auto divide-y divide-slate-800">
            {rapid.map((r) => (
              <li key={r.id} className="px-4 py-3 text-sm">
                <div className="font-medium">{r.title}</div>
                <div className="text-xs text-slate-400">{r.status} · {r.priority} · {r.ai_generated ? "AI draft" : "manual"}</div>
                {r.draft_body && (
                  <pre className="mt-2 max-h-24 overflow-y-auto whitespace-pre-wrap rounded bg-slate-950 p-2 text-[11px] text-slate-400">
                    {r.draft_body.slice(0, 400)}
                  </pre>
                )}
                {(r.status === "queued" || r.status === "in_review") && (
                  <div className="mt-2 flex gap-2">
                    <button onClick={() => review(r.id, "approve")} className="rounded bg-emerald-700 px-2 py-1 text-xs">Approve</button>
                    <button onClick={() => review(r.id, "reject")} className="rounded bg-slate-700 px-2 py-1 text-xs">Reject</button>
                  </div>
                )}
              </li>
            ))}
            {rapid.length === 0 && <li className="p-4 text-slate-500 text-sm">Queue empty</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}
