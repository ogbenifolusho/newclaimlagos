"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { fetchOverview } from "@/lib/api";
import { getToken, authHeaders } from "@/lib/auth";
import Nav from "@/components/Nav";

const LagosMap = dynamic(() => import("@/components/map/LagosMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[380px] items-center justify-center text-slate-500">Loading map…</div>
  ),
});

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface KPI {
  key: string;
  label: string;
  value: number | string;
  delta?: number;
  status: string;
}

interface AlertItem {
  id: string;
  title: string;
  severity: string;
  geo_name?: string;
  created_at: string;
}

interface RecommendationItem {
  id: string;
  title: string;
  action_type?: string;
  confidence?: number;
  status: string;
}

interface CalEvent {
  id: string;
  title: string;
  event_date: string;
  event_type: string;
  geo_name?: string;
}

export default function SituationRoomPage() {
  const [kpis, setKpis] = useState<KPI[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [recs, setRecs] = useState<RecommendationItem[]>([]);
  const [health, setHealth] = useState<Record<string, string>>({});
  const [countdown, setCountdown] = useState<number | null>(null);
  const [calendar, setCalendar] = useState<CalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState("");
  const [reviewMsg, setReviewMsg] = useState("");
  const [wsStatus, setWsStatus] = useState("offline");
  const [assignModal, setAssignModal] = useState<RecommendationItem | null>(null);
  const [ambassadors, setAmbassadors] = useState<any[]>([]);
  const [selectedAmbs, setSelectedAmbs] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [data, cfg, cal] = await Promise.all([
          fetchOverview(),
          fetch(`${API}/api/v1/campaign/config`).then((r) => r.json()).catch(() => null),
          fetch(`${API}/api/v1/campaign/calendar`).then((r) => r.json()).catch(() => []),
        ]);
        if (cancelled) return;
        setKpis(data.kpis || []);
        setAlerts(data.alerts || []);
        setRecs(data.recommendations || []);
        setHealth(data.system_health || {});
        setLastUpdated(data.last_updated || new Date().toISOString());
        if (cfg) setCountdown(cfg.countdown_days);
        setCalendar(cal || []);
        setError(null);
      } catch {
        if (!cancelled) setError("API unavailable – offline mode");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // WebSocket live feed
  useEffect(() => {
    const wsUrl = (API.replace("http", "ws") + "/ws/situation-room").replace("localhost:8000", "localhost:8000");
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl);
      ws.onopen = () => setWsStatus("live");
      ws.onclose = () => setWsStatus("offline");
      ws.onerror = () => setWsStatus("error");
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "alert" && msg.payload) {
            setAlerts((prev) => [
              {
                id: `ws-${Date.now()}`,
                title: msg.payload.title,
                severity: msg.payload.severity || "medium",
                geo_name: msg.payload.geo_name,
                created_at: msg.payload.created_at || new Date().toISOString(),
              },
              ...prev,
            ]);
          }
        } catch {}
      };
    } catch {
      setWsStatus("offline");
    }
    return () => {
      ws?.close();
    };
  }, []);

  async function openAssign(rec: RecommendationItem) {
    setAssignModal(rec);
    setSelectedAmbs([]);
    if (getToken()) {
      const res = await fetch(`${API}/api/v1/ambassadors/?status=active`, {
        headers: authHeaders(),
      });
      if (res.ok) setAmbassadors(await res.json());
    }
  }

  async function reviewRecommendation(id: string, action: "accept" | "reject") {
    const token = getToken();
    if (!token) {
      setReviewMsg("Login required");
      return;
    }
    if (id.startsWith("00000000")) {
      setReviewMsg("Seed demo recommendations first: POST /api/v1/recommendations/seed-demo");
      return;
    }
    const body: any = { action };
    if (action === "accept" && selectedAmbs.length) {
      body.ambassador_ids = selectedAmbs;
      body.task_title = assignModal?.title;
    }
    try {
      const res = await fetch(`${API}/api/v1/recommendations/${id}/review`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setReviewMsg(
          action === "accept"
            ? `Accepted${data.task_id ? ` – task ${data.task_id.slice(0, 8)}… created` : ""}`
            : "Rejected"
        );
        setRecs((prev) => prev.filter((r) => r.id !== id));
        setAssignModal(null);
      } else {
        setReviewMsg(data.detail || "Review failed");
      }
    } catch {
      setReviewMsg("Network error");
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-400">
        Loading Situation Room…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 bg-slate-900/80 px-4 py-2">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-emerald-600 text-sm font-bold">
            CL
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">CLAIM LAGOS</h1>
            <p className="text-xs text-slate-400">Situation Room · APC Lagos · PBAT-KOH 2027</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {countdown !== null && (
            <div className="rounded bg-slate-800 px-3 py-1 text-center">
              <div className="text-lg font-bold text-emerald-400">{countdown}</div>
              <div className="text-[10px] text-slate-400">days to election</div>
            </div>
          )}
          <div className="text-xs text-slate-400">
            WS:{" "}
            <span className={wsStatus === "live" ? "text-emerald-400" : "text-amber-400"}>
              {wsStatus}
            </span>
          </div>
          <Nav />
        </div>
      </header>

      <section className="grid grid-cols-2 gap-3 border-b border-slate-800 bg-slate-900/50 p-3 md:grid-cols-5">
        {kpis.map((kpi) => (
          <div key={kpi.key} className="rounded-lg border border-slate-800 bg-slate-900 p-3">
            <div className="text-xs text-slate-400">{kpi.label}</div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold">{kpi.value}</span>
              {kpi.delta !== undefined && (
                <span className={`text-xs ${kpi.delta >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {kpi.delta >= 0 ? "+" : ""}
                  {kpi.delta}
                </span>
              )}
            </div>
          </div>
        ))}
      </section>

      <main className="grid grid-cols-1 gap-3 p-3 lg:grid-cols-12">
        <div className="min-h-[420px] rounded-lg border border-slate-800 bg-slate-900 p-4 lg:col-span-7">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="font-semibold">Lagos Geo Intelligence</h2>
            <span className="text-xs text-amber-400">PLACEHOLDER · Public boundaries</span>
          </div>
          <div className="h-[380px] overflow-hidden rounded">
            <LagosMap />
          </div>
        </div>

        <div className="flex flex-col gap-3 lg:col-span-5">
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <h2 className="mb-3 font-semibold">Live Alerts</h2>
            <ul className="max-h-40 space-y-2 overflow-y-auto">
              {alerts.map((a) => (
                <li key={a.id} className="rounded border border-slate-800 bg-slate-950 p-3 text-sm">
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-2 w-2 rounded-full ${
                        a.severity === "high" || a.severity === "critical" ? "bg-red-500" : "bg-amber-400"
                      }`}
                    />
                    <span className="font-medium">{a.title}</span>
                  </div>
                  <div className="mt-1 text-xs text-slate-400">
                    {a.geo_name} · {new Date(a.created_at).toLocaleTimeString()}
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <h2 className="mb-3 font-semibold">Recommended Actions</h2>
            <p className="mb-2 text-xs text-slate-400">
              AI-generated · Human approval required · No auto-publish
            </p>
            {reviewMsg && <p className="mb-2 text-xs text-amber-300">{reviewMsg}</p>}
            <ul className="space-y-2">
              {recs.map((r) => (
                <li key={r.id} className="rounded border border-slate-800 bg-slate-950 p-3 text-sm">
                  <div className="font-medium">{r.title}</div>
                  <div className="mt-2 flex items-center justify-between text-xs">
                    <span className="text-slate-400">
                      {r.confidence != null ? `${(r.confidence * 100).toFixed(0)}%` : ""} ·{" "}
                      {r.action_type}
                    </span>
                    <div className="flex gap-1">
                      <button
                        onClick={() => openAssign(r)}
                        className="rounded bg-emerald-700 px-2 py-1 text-xs font-medium hover:bg-emerald-600"
                      >
                        Review & Assign
                      </button>
                      <button
                        onClick={() => reviewRecommendation(r.id, "reject")}
                        className="rounded bg-slate-700 px-2 py-1 text-xs hover:bg-slate-600"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <h2 className="mb-2 font-semibold">Campaign Calendar</h2>
            <ul className="space-y-1 text-sm">
              {calendar.map((e) => (
                <li key={e.id} className="flex justify-between text-slate-300">
                  <span>{e.title}</span>
                  <span className="text-xs text-slate-500">{e.event_date}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </main>

      {/* Review & Assign Modal */}
      {assignModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-6">
            <h3 className="mb-2 text-lg font-semibold">Review & Assign</h3>
            <p className="mb-4 text-sm text-slate-300">{assignModal.title}</p>
            <p className="mb-2 text-xs text-slate-400">
              Select ambassadors to assign (optional). Creates internal tasks only.
            </p>
            <div className="mb-4 max-h-48 overflow-y-auto rounded border border-slate-800">
              {ambassadors.length === 0 && (
                <p className="p-3 text-sm text-slate-500">No active ambassadors (or login required)</p>
              )}
              {ambassadors.map((a) => (
                <label
                  key={a.id}
                  className="flex cursor-pointer items-center gap-2 border-b border-slate-800 px-3 py-2 text-sm hover:bg-slate-800"
                >
                  <input
                    type="checkbox"
                    checked={selectedAmbs.includes(a.id)}
                    onChange={(e) => {
                      if (e.target.checked) setSelectedAmbs((p) => [...p, a.id]);
                      else setSelectedAmbs((p) => p.filter((id) => id !== a.id));
                    }}
                  />
                  <span>
                    {a.full_name}{" "}
                    <span className="text-xs text-slate-500">{a.ward_name || ""}</span>
                  </span>
                </label>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setAssignModal(null)}
                className="rounded bg-slate-700 px-3 py-1.5 text-sm"
              >
                Cancel
              </button>
              <button
                onClick={() => reviewRecommendation(assignModal.id, "accept")}
                className="rounded bg-emerald-600 px-3 py-1.5 text-sm font-medium"
              >
                Accept{selectedAmbs.length ? ` & Assign (${selectedAmbs.length})` : ""}
              </button>
            </div>
          </div>
        </div>
      )}

      <footer className="border-t border-slate-800 px-4 py-2 text-center text-xs text-slate-500">
        CLAIM LAGOS · New Media Directorate · All AI outputs require human approval
        {lastUpdated && (
          <span className="ml-2">· Updated {new Date(lastUpdated).toLocaleTimeString()}</span>
        )}
        {error && <span className="ml-2 text-amber-400">{error}</span>}
      </footer>
    </div>
  );
}
