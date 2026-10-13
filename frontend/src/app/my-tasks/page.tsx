"use client";

import { useEffect, useState } from "react";
import Nav from "@/components/Nav";
import { getToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Assignment {
  id: string;
  task_id: string;
  task_title: string;
  status: string;
  assigned_at: string;
  completed_at?: string;
  report_text?: string;
}

export default function MyTasksPage() {
  const [tasks, setTasks] = useState<Assignment[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);
  const [reportText, setReportText] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    setToken(getToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    fetch(`${API_BASE}/api/v1/tasks/my`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then(setTasks)
      .catch(() => setMsg("Could not load tasks – login required"));
  }, [token]);

  async function submitReport(assignmentId: string) {
    if (!token || !reportText.trim()) return;
    const res = await fetch(`${API_BASE}/api/v1/tasks/assignments/${assignmentId}/report`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ report_text: reportText }),
    });
    if (res.ok) {
      setMsg("Report submitted");
      setReportId(null);
      setReportText("");
      // refresh
      const updated = await fetch(`${API_BASE}/api/v1/tasks/my`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then((r) => r.json());
      setTasks(updated);
    } else {
      setMsg("Failed to submit report");
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Tasks</h1>
          <p className="text-sm text-slate-400">Digital Ambassador task inbox & daily reporting</p>
        </div>
        <Nav />
      </header>

      {msg && <div className="mb-4 text-sm text-amber-300">{msg}</div>}

      {!token && (
        <div className="rounded border border-slate-800 bg-slate-900 p-6 text-center text-slate-400">
          Login required. Use API <code className="text-emerald-400">/api/v1/auth/login</code> and store token in localStorage as <code>claim_token</code>.
        </div>
      )}

      <ul className="space-y-3">
        {tasks.map((t) => (
          <li key={t.id} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold">{t.task_title}</h3>
                <p className="mt-1 text-xs text-slate-400">
                  Assigned {new Date(t.assigned_at).toLocaleString()} · Status:{" "}
                  <span className={t.status === "completed" ? "text-emerald-400" : "text-amber-400"}>
                    {t.status}
                  </span>
                </p>
                {t.report_text && (
                  <p className="mt-2 text-sm text-slate-300">Report: {t.report_text}</p>
                )}
              </div>
              {t.status !== "completed" && (
                <button
                  onClick={() => setReportId(t.id)}
                  className="rounded bg-emerald-700 px-3 py-1.5 text-xs font-medium hover:bg-emerald-600"
                >
                  Submit Report
                </button>
              )}
            </div>
            {reportId === t.id && (
              <div className="mt-3 border-t border-slate-800 pt-3">
                <textarea
                  className="w-full rounded border border-slate-700 bg-slate-950 p-2 text-sm"
                  rows={3}
                  placeholder="Describe what you did / observations…"
                  value={reportText}
                  onChange={(e) => setReportText(e.target.value)}
                />
                <div className="mt-2 flex gap-2">
                  <button
                    onClick={() => submitReport(t.id)}
                    className="rounded bg-emerald-600 px-3 py-1 text-xs font-medium"
                  >
                    Send Report
                  </button>
                  <button
                    onClick={() => setReportId(null)}
                    className="rounded bg-slate-700 px-3 py-1 text-xs"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}
        {token && tasks.length === 0 && (
          <li className="text-center text-slate-500 py-8">No tasks assigned yet</li>
        )}
      </ul>
    </div>
  );
}
