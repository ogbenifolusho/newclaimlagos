"use client";

import { useEffect, useState } from "react";
import { authHeaders, getToken } from "@/lib/auth";
import Nav from "@/components/Nav";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function CreatePage() {
  const [events, setEvents] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [topic, setTopic] = useState("");
  const [tone, setTone] = useState("hopeful");
  const [eventForm, setEventForm] = useState({ title: "", event_date: "", event_type: "content" });

  async function load() {
    const res = await fetch(`${API}/api/v1/create/calendar`);
    if (res.ok) setEvents(await res.json());
  }

  useEffect(() => {
    load();
  }, []);

  async function addEvent(e: React.FormEvent) {
    e.preventDefault();
    if (!getToken()) return setMsg("Login required");
    const res = await fetch(`${API}/api/v1/create/calendar`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(eventForm),
    });
    if (res.ok) {
      setMsg("Event added");
      setEventForm({ title: "", event_date: "", event_type: "content" });
      load();
    }
  }

  async function aiDraft(e: React.FormEvent) {
    e.preventDefault();
    if (!getToken()) return setMsg("Login required");
    const res = await fetch(`${API}/api/v1/create/ai-draft`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ topic, tone, platform: "x" }),
    });
    const data = await res.json();
    if (res.ok) {
      setMsg(`AI draft saved as content ${data.content_id?.slice(0, 8)}… – review in Content`);
      setTopic("");
    } else setMsg(data.detail || "Failed");
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">CREATE</h1>
          <p className="text-sm text-slate-400">Calendar · AI-assisted drafts · Approval workflow only</p>
        </div>
        <Nav />
      </header>
      {msg && <p className="mb-4 text-sm text-amber-300">{msg}</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h2 className="mb-3 font-semibold">Campaign calendar</h2>
          <form onSubmit={addEvent} className="mb-4 space-y-2">
            <input className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm" placeholder="Event title" value={eventForm.title} onChange={(e) => setEventForm({ ...eventForm, title: e.target.value })} required />
            <input type="date" className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm" value={eventForm.event_date} onChange={(e) => setEventForm({ ...eventForm, event_date: e.target.value })} required />
            <select className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm" value={eventForm.event_type} onChange={(e) => setEventForm({ ...eventForm, event_type: e.target.value })}>
              {["content", "media", "rally", "training", "deadline", "ads", "other"].map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <button type="submit" className="rounded bg-emerald-700 px-3 py-2 text-sm">Add event</button>
          </form>
          <ul className="space-y-2 text-sm">
            {events.map((ev) => (
              <li key={ev.id} className="flex justify-between border-b border-slate-800 py-2">
                <span>{ev.title} <span className="text-xs text-slate-500">({ev.event_type})</span></span>
                <span className="text-xs text-slate-400">{ev.event_date}</span>
              </li>
            ))}
            {events.length === 0 && <li className="text-slate-500">No events yet</li>}
          </ul>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h2 className="mb-3 font-semibold">AI-assisted draft</h2>
          <p className="mb-3 text-xs text-slate-400">Generates a draft for human review in Content. Never auto-published.</p>
          <form onSubmit={aiDraft} className="space-y-2">
            <input className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm" placeholder="Topic e.g. new road projects in Ikeja" value={topic} onChange={(e) => setTopic(e.target.value)} required />
            <select className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm" value={tone} onChange={(e) => setTone(e.target.value)}>
              <option value="hopeful">Hopeful</option>
              <option value="factual">Factual</option>
              <option value="empathetic">Empathetic</option>
            </select>
            <button type="submit" className="rounded bg-emerald-700 px-3 py-2 text-sm font-medium">Generate draft for review</button>
          </form>
        </div>
      </div>
    </div>
  );
}
