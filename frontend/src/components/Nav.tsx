"use client";

import Link from "next/link";
import { getUser, logout } from "@/lib/auth";
import { useEffect, useState } from "react";

export default function Nav() {
  const [user, setUser] = useState<ReturnType<typeof getUser>>(null);

  useEffect(() => {
    setUser(getUser());
  }, []);

  return (
    <nav className="flex items-center gap-4 text-sm">
      <Link href="/" className="text-slate-300 hover:text-white">Situation Room</Link>
      <Link href="/ambassadors" className="text-slate-300 hover:text-white">Ambassadors</Link>
      <Link href="/my-tasks" className="text-slate-300 hover:text-white">My Tasks</Link>
      <Link href="/listen" className="text-slate-300 hover:text-white">Listen</Link>
      <Link href="/ads" className="text-slate-300 hover:text-white">Ads</Link>
      <Link href="/create" className="text-slate-300 hover:text-white">CREATE</Link>
      <Link href="/influence" className="text-slate-300 hover:text-white">Influence</Link>
      <Link href="/reports" className="text-slate-300 hover:text-white">Reports</Link>
      <Link href="/content" className="text-slate-300 hover:text-white">Content</Link>
      {user ? (
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">{user.full_name}</span>
          <button onClick={logout} className="text-xs text-red-400 hover:underline">Logout</button>
        </div>
      ) : (
        <Link href="/login" className="text-emerald-400 hover:underline">Login</Link>
      )}
    </nav>
  );
}
