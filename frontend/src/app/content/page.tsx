"use client";

import { useEffect, useState } from "react";
import { authHeaders, getToken } from "@/lib/auth";
import Nav from "@/components/Nav";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ContentItem {
  id: string;
  title: string;
  body?: string;
  asset_type?: string;
  status: string;
  ai_generated: boolean;
  created_at: string;
}

export default function ContentPage() {
  const [items, setItems] = useState<ContentItem[]>([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    const res = await fetch(`${API}/api/v1/content/`);
    if (res.ok) setItems(await res.json());
  }

  useEffect(() => {
    load();
  }, []);

  async function createDraft() {
    if (!getToken()) {
      setMsg("Login required");
      return;
    }
    const res = await fetch(`${API}/api/v1/content/`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ title, body, asset_type: "post" }),
    });
    if (res.ok) {
      setTitle("");
      setBody("");
      setMsg("Draft created – submit for approval");
      load();
    } else setMsg("Failed to create");
  }

  async function approve(id: string, action: string) {
    const res = await fetch(`${API}/api/v1/content/${id}/approve`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    if (res.ok) {
      setMsg(`Content ${action}d`);
      load();
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Content Packs</h1>
          <p className="text-sm text-slate-400">Create → Approve → Distribute (never auto-publish)</p>
        </div>
        <Nav />
      </header>

      {msg && <p className="mb-4 text-sm text-amber-300">{msg}</p>}

      <div className="mb-6 rounded-lg border border-slate-800 bg-slate-900 p-4">
        <h2 className="mb-3 font-semibold">New Draft</h2>
        <input
          className="mb-2 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          className="mb-2 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          rows={3}
          placeholder="Body / caption"
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
        <button
          onClick={createDraft}
          className="rounded bg-emerald-700 px-4 py-2 text-sm font-medium hover:bg-emerald-600"
        >
          Create Draft
        </button>
      </div>

      <ul className="space-y-3">
        {items.map((c) => (
          <li key={c.id} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold">{c.title}</h3>
                <p className="mt-1 text-sm text-slate-400 line-clamp-2">{c.body}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {c.status} · {c.ai_generated ? "AI draft" : "Manual"} ·{" "}
                  {new Date(c.created_at).toLocaleString()}
                </p>
              </div>
              <div className="flex gap-2">
                {c.status !== "approved" && c.status !== "rejected" && (
                  <>
                    <button
                      onClick={() => approve(c.id, "approve")}
                      className="rounded bg-emerald-700 px-2 py-1 text-xs"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => approve(c.id, "reject")}
                      className="rounded bg-slate-700 px-2 py-1 text-xs"
                    >
                      Reject
                    </button>
                  </>
                )}
                {c.status === "approved" && (
                  <span className="text-xs text-emerald-400">Ready to distribute via API</span>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
