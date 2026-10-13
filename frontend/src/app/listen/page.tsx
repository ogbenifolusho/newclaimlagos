"use client";

import { useEffect, useState } from "react";
import { authHeaders, getToken } from "@/lib/auth";
import Nav from "@/components/Nav";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ListenPage() {
  const [stats, setStats] = useState<any>(null);
  const [posts, setPosts] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [keywords, setKeywords] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [ingesting, setIngesting] = useState(false);

  async function load() {
    const [s, p, a, k] = await Promise.all([
      fetch(`${API}/api/v1/listen/stats`).then((r) => r.json()).catch(() => null),
      fetch(`${API}/api/v1/listen/posts?limit=30`).then((r) => r.json()).catch(() => []),
      fetch(`${API}/api/v1/listen/alerts`).then((r) => r.json()).catch(() => []),
      fetch(`${API}/api/v1/listen/keywords`).then((r) => r.json()).catch(() => []),
    ]);
    setStats(s);
    setPosts(p);
    setAlerts(a);
    setKeywords(k);
  }

  useEffect(() => {
    load();
  }, []);

  async function seedKeywords() {
    if (!getToken()) {
      setMsg("Login required");
      return;
    }
    const res = await fetch(`${API}/api/v1/listen/keywords/seed-demo`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (res.ok) {
      setMsg("Demo keyword rules seeded");
      load();
    }
  }

  async function runIngest() {
    if (!getToken()) {
      setMsg("Login required");
      return;
    }
    setIngesting(true);
    const res = await fetch(`${API}/api/v1/listen/ingest?limit=10`, {
      method: "POST",
      headers: authHeaders(),
    });
    const data = await res.json();
    setIngesting(false);
    if (res.ok) {
      setMsg(`Ingested ${data.ingested} posts · ${data.alerts_created} alerts`);
      load();
    } else setMsg(data.detail || "Ingest failed");
  }

  function sentimentColor(s?: string) {
    if (s === "positive") return "text-emerald-400";
    if (s === "negative") return "text-red-400";
    if (s === "mixed") return "text-amber-400";
    return "text-slate-400";
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Listen</h1>
          <p className="text-sm text-slate-400">
            Social intelligence · Keywords · Alerts · X / Meta / YouTube / TikTok / Google placeholders
          </p>
        </div>
        <Nav />
      </header>

      {msg && <p className="mb-4 text-sm text-amber-300">{msg}</p>}

      <div className="mb-4 flex flex-wrap gap-2">
        <button
          onClick={seedKeywords}
          className="rounded bg-slate-700 px-3 py-2 text-sm hover:bg-slate-600"
        >
          Seed keyword rules
        </button>
        <button
          onClick={runIngest}
          disabled={ingesting}
          className="rounded bg-emerald-700 px-3 py-2 text-sm font-medium hover:bg-emerald-600 disabled:opacity-50"
        >
          {ingesting ? "Ingesting…" : "Run ingest (synthetic if no API keys)"}
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
            <div className="text-xs text-slate-400">Total posts</div>
            <div className="text-2xl font-bold">{stats.total_posts}</div>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
            <div className="text-xs text-slate-400">Open alerts</div>
            <div className="text-2xl font-bold text-amber-400">{stats.open_alerts}</div>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
            <div className="text-xs text-slate-400">By sentiment</div>
            <div className="text-xs mt-1 space-y-0.5">
              {Object.entries(stats.by_sentiment || {}).map(([k, v]) => (
                <div key={k} className={sentimentColor(k)}>
                  {k}: {v as number}
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
            <div className="text-xs text-slate-400">API credentials</div>
            <div className="text-xs mt-1 space-y-0.5">
              {Object.entries(stats.credentials || {}).map(([k, v]) => (
                <div key={k} className={v ? "text-emerald-400" : "text-slate-500"}>
                  {k}: {v ? "configured" : "placeholder"}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Posts */}
        <div className="lg:col-span-2 rounded-lg border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 px-4 py-3 font-semibold">Recent posts</div>
          <ul className="max-h-[480px] overflow-y-auto divide-y divide-slate-800">
            {posts.length === 0 && (
              <li className="p-6 text-center text-slate-500 text-sm">
                No posts yet – seed keywords and run ingest
              </li>
            )}
            {posts.map((p) => (
              <li key={p.id} className="px-4 py-3 text-sm">
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span className="uppercase">{p.platform}</span>
                  <span>@{p.author_handle}</span>
                  <span className={sentimentColor(p.sentiment)}>{p.sentiment}</span>
                  {p.is_bot_suspect && <span className="text-red-400">bot?</span>}
                </div>
                <p className="mt-1 text-slate-200">{p.content}</p>
                {p.topics?.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {p.topics.map((t: string) => (
                      <span key={t} className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                {p.matched_keywords?.length > 0 && (
                  <div className="mt-1 text-xs text-amber-400">
                    Matched: {p.matched_keywords.join(", ")}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-4">
          {/* Keywords */}
          <div className="rounded-lg border border-slate-800 bg-slate-900">
            <div className="border-b border-slate-800 px-4 py-3 font-semibold">Keyword rules</div>
            <ul className="p-3 space-y-2 text-sm">
              {keywords.length === 0 && (
                <li className="text-slate-500">None – click Seed keyword rules</li>
              )}
              {keywords.map((k) => (
                <li key={k.id} className="rounded border border-slate-800 bg-slate-950 p-2">
                  <div className="font-medium">{k.name}</div>
                  <div className="text-xs text-slate-400">{k.keywords?.join(", ")}</div>
                  <div className="text-[10px] text-slate-500">{k.severity} · {k.is_active ? "active" : "off"}</div>
                </li>
              ))}
            </ul>
          </div>

          {/* Alerts */}
          <div className="rounded-lg border border-slate-800 bg-slate-900">
            <div className="border-b border-slate-800 px-4 py-3 font-semibold">Open alerts</div>
            <ul className="max-h-64 overflow-y-auto p-3 space-y-2 text-sm">
              {alerts.length === 0 && <li className="text-slate-500">No open alerts</li>}
              {alerts.map((a) => (
                <li key={a.id} className="rounded border border-slate-800 bg-slate-950 p-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-2 w-2 rounded-full ${
                        a.severity === "high" ? "bg-red-500" : "bg-amber-400"
                      }`}
                    />
                    <span className="font-medium text-xs">{a.title}</span>
                  </div>
                  <div className="mt-1 text-[10px] text-slate-500">
                    {a.source} · {new Date(a.created_at).toLocaleString()}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
