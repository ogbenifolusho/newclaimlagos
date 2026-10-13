"use client";

import { useEffect, useState } from "react";
import { authHeaders, getToken } from "@/lib/auth";
import Nav from "@/components/Nav";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Ambassador {
  id: string;
  full_name: string;
  email: string;
  ward_name?: string;
  status: string;
  performance_score: number;
  completed_tasks: number;
  total_tasks: number;
}

export default function AmbassadorsPage() {
  const [list, setList] = useState<Ambassador[]>([]);
  const [leaders, setLeaders] = useState<any[]>([]);
  const [wards, setWards] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    password: "",
    phone: "",
    ward_id: "",
  });

  async function load() {
    const headers = authHeaders();
    const [ambRes, leadRes, wardRes] = await Promise.all([
      fetch(`${API}/api/v1/ambassadors/`, { headers }),
      fetch(`${API}/api/v1/ambassadors/leaderboard`),
      fetch(`${API}/api/v1/geo/hierarchy?level=ward&limit=100`),
    ]);
    if (ambRes.ok) setList(await ambRes.json());
    if (leadRes.ok) {
      const d = await leadRes.json();
      setLeaders(d.leaders || []);
    }
    if (wardRes.ok) setWards(await wardRes.json());
  }

  useEffect(() => {
    load();
  }, []);

  async function createAmbassador(e: React.FormEvent) {
    e.preventDefault();
    if (!getToken()) {
      setMsg("Login required");
      return;
    }
    const res = await fetch(`${API}/api/v1/ambassadors/`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        ward_id: form.ward_id || null,
      }),
    });
    if (res.ok) {
      setMsg("Ambassador created (pending verification)");
      setForm({ email: "", full_name: "", password: "", phone: "", ward_id: "" });
      load();
    } else {
      const d = await res.json().catch(() => ({}));
      setMsg(d.detail || "Failed to create");
    }
  }

  async function verify(id: string, status: string) {
    const res = await fetch(`${API}/api/v1/ambassadors/${id}/verify`, {
      method: "PATCH",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (res.ok) {
      setMsg(`Status → ${status}`);
      load();
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Digital Ambassadors</h1>
          <p className="text-sm text-slate-400">Register · Verify · Ward allocate · Leaderboard</p>
        </div>
        <Nav />
      </header>

      {msg && <p className="mb-4 text-sm text-amber-300">{msg}</p>}

      <form
        onSubmit={createAmbassador}
        className="mb-6 grid gap-2 rounded-lg border border-slate-800 bg-slate-900 p-4 md:grid-cols-3"
      >
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Full name"
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          required
        />
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Email"
          type="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          required
        />
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Password"
          type="password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          required
        />
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Phone"
          value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })}
        />
        <select
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          value={form.ward_id}
          onChange={(e) => setForm({ ...form, ward_id: e.target.value })}
        >
          <option value="">Select ward (optional)</option>
          {wards.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
        <button type="submit" className="rounded bg-emerald-700 px-4 py-2 text-sm font-medium hover:bg-emerald-600">
          Register Ambassador
        </button>
      </form>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900 lg:col-span-2">
          <div className="border-b border-slate-800 px-4 py-3 font-semibold">All Ambassadors</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-950 text-slate-400">
                <tr>
                  <th className="px-4 py-2 text-left">Name</th>
                  <th className="px-4 py-2 text-left">Ward</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-right">Score</th>
                  <th className="px-4 py-2 text-right">Tasks</th>
                  <th className="px-4 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {list.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                      No ambassadors yet
                    </td>
                  </tr>
                )}
                {list.map((a) => (
                  <tr key={a.id} className="border-t border-slate-800">
                    <td className="px-4 py-2">{a.full_name}</td>
                    <td className="px-4 py-2 text-slate-400">{a.ward_name || "—"}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-xs ${
                          a.status === "active"
                            ? "bg-emerald-900 text-emerald-300"
                            : a.status === "pending"
                            ? "bg-amber-900 text-amber-300"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {a.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right">{a.performance_score}</td>
                    <td className="px-4 py-2 text-right">
                      {a.completed_tasks}/{a.total_tasks}
                    </td>
                    <td className="px-4 py-2">
                      {a.status === "pending" && (
                        <button
                          onClick={() => verify(a.id, "active")}
                          className="text-xs text-emerald-400 hover:underline"
                        >
                          Verify
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 px-4 py-3 font-semibold">Leaderboard</div>
          <ul className="space-y-3 p-4">
            {leaders.length === 0 && <li className="text-sm text-slate-500">No scores yet</li>}
            {leaders.map((l) => (
              <li key={l.rank} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-3">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-800 text-xs font-bold">
                    {l.rank}
                  </span>
                  <span>{l.name}</span>
                </div>
                <span className="font-mono text-emerald-400">{l.score}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
