"use client";

import { useEffect, useState } from "react";
import { authHeaders, getToken } from "@/lib/auth";
import Nav from "@/components/Nav";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ReportsPage() {
  const [exec, setExec] = useState<any>(null);
  const [narratives, setNarratives] = useState<any>(null);
  const [geo, setGeo] = useState<any>(null);
  const [msg, setMsg] = useState("");

  async function load() {
    const [e, n, g] = await Promise.all([
      fetch(`${API}/api/v1/reports/executive`).then((r) => r.json()).catch(() => null),
      fetch(`${API}/api/v1/intelligence/narratives`).then((r) => r.json()).catch(() => null),
      fetch(`${API}/api/v1/intelligence/geo-density`).then((r) => r.json()).catch(() => null),
    ]);
    setExec(e);
    setNarratives(n);
    setGeo(g);
  }

  useEffect(() => {
    load();
  }, []);

  async function genRecs() {
    if (!getToken()) return setMsg("Login required");
    const res = await fetch(`${API}/api/v1/intelligence/generate-recommendations`, {
      method: "POST",
      headers: authHeaders(),
    });
    const data = await res.json();
    if (res.ok) setMsg(`Created ${data.created} recommendations for review`);
    else setMsg(data.detail || "Failed");
  }

  function download(path: string, filename: string) {
    const token = getToken();
    fetch(`${API}${path}`, { headers: authHeaders() })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
      });
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Reports & Intelligence</h1>
          <p className="text-sm text-slate-400">Executive summary · Narratives · Exports · Geo density</p>
        </div>
        <Nav />
      </header>
      {msg && <p className="mb-4 text-sm text-amber-300">{msg}</p>}

      <div className="mb-4 flex flex-wrap gap-2">
        <button onClick={genRecs} className="rounded bg-emerald-700 px-3 py-2 text-sm font-medium">
          Generate recommendations from narratives
        </button>
        <button
          onClick={() => download("/api/v1/reports/export/ambassadors.csv", "ambassadors.csv")}
          className="rounded bg-slate-700 px-3 py-2 text-sm"
        >
          Export Ambassadors CSV
        </button>
        <button
          onClick={() => download("/api/v1/reports/export/posts.csv", "posts.csv")}
          className="rounded bg-slate-700 px-3 py-2 text-sm"
        >
          Export Posts CSV
        </button>
        <button
          onClick={() => download("/api/v1/reports/export/executive.json", "executive.json")}
          className="rounded bg-slate-700 px-3 py-2 text-sm"
        >
          Export Executive JSON
        </button>
      </div>

      {exec && (
        <div className="mb-6 rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h2 className="mb-2 font-semibold">Executive summary</h2>
          <p className="mb-4 text-sm text-slate-300">{exec.ai_summary}</p>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 text-sm">
            {Object.entries(exec.kpis || {}).map(([k, v]) => (
              <div key={k} className="rounded border border-slate-800 bg-slate-950 p-2">
                <div className="text-xs text-slate-500">{k}</div>
                <div className="font-mono">
                  {typeof v === "object" ? JSON.stringify(v) : String(v)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h2 className="mb-3 font-semibold">Narrative detection</h2>
          {narratives ? (
            <>
              <p className="mb-2 text-sm">
                Misinfo risk:{" "}
                <span
                  className={
                    narratives.misinfo_risk === "high"
                      ? "text-red-400"
                      : narratives.misinfo_risk === "medium"
                      ? "text-amber-400"
                      : "text-emerald-400"
                  }
                >
                  {narratives.misinfo_risk}
                </span>{" "}
                (confidence {narratives.misinfo_confidence}) · samples {narratives.sample_size}
              </p>
              <ul className="space-y-2 text-sm">
                {(narratives.narratives || []).map((n: any, i: number) => (
                  <li key={i} className="rounded border border-slate-800 bg-slate-950 p-3">
                    <div className="font-medium">{n.label}</div>
                    <div className="text-xs text-slate-400">
                      {n.type} · strength {(n.strength * 100).toFixed(0)}%
                    </div>
                    {n.suggested_response && (
                      <div className="mt-1 text-xs text-slate-500">
                        → {n.suggested_response.action}: {n.suggested_response.draft_hint}
                      </div>
                    )}
                  </li>
                ))}
                {(narratives.narratives || []).length === 0 && (
                  <li className="text-slate-500">No strong narratives – run Listen ingest first</li>
                )}
              </ul>
            </>
          ) : (
            <p className="text-slate-500 text-sm">Loading…</p>
          )}
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h2 className="mb-3 font-semibold">Geo density (LGA layer)</h2>
          <p className="mb-2 text-xs text-slate-400">
            {geo?.note || "Ambassador ward counts + sentiment mix"}
          </p>
          {geo?.sentiment_mix && (
            <div className="mb-3 text-xs">
              Sentiment: {Object.entries(geo.sentiment_mix).map(([k, v]) => `${k}=${v}`).join(" · ")}
            </div>
          )}
          <ul className="max-h-64 overflow-y-auto text-sm space-y-1">
            {(geo?.lga_layers || []).map((g: any) => (
              <li key={g.geo_id} className="flex justify-between border-b border-slate-800 py-1">
                <span>{g.name}</span>
                <span className="text-xs text-slate-500">{g.is_placeholder ? "placeholder" : "official"}</span>
              </li>
            ))}
          </ul>
          {geo?.ward_ambassador_counts && (
            <p className="mt-2 text-xs text-slate-400">
              Wards with ambassadors: {Object.keys(geo.ward_ambassador_counts).length}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
