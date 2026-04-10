"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { requestMagicLink } from "@/lib/api";

type Stage = "form" | "sending" | "sent" | "error";

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [stage, setStage] = useState<Stage>("form");
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email) return;
    setStage("sending");
    try {
      await requestMagicLink(email);
      setStage("sent");
    } catch {
      setErrorMsg("Something went wrong — please try again.");
      setStage("error");
    }
  }

  return (
    <main className="min-h-screen bg-zinc-950 text-white flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <Link
          href="/"
          className="block text-center text-lg font-bold tracking-tight mb-8"
        >
          Whats-What
        </Link>

        {stage === "sent" ? (
          <div className="text-center space-y-3">
            <div className="text-3xl">📬</div>
            <h2 className="font-semibold text-white">Check your inbox</h2>
            <p className="text-sm text-zinc-400">
              We sent a sign-in link to{" "}
              <span className="text-white">{email}</span>. It expires in 15
              minutes.
            </p>
            <button
              onClick={() => setStage("form")}
              className="mt-4 text-xs text-zinc-500 underline"
            >
              Use a different email
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-zinc-300 mb-1.5"
              >
                Email address
              </label>
              <input
                id="email"
                type="email"
                required
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-500 transition-colors"
              />
            </div>

            {stage === "error" && (
              <p className="text-xs text-rose-400">{errorMsg}</p>
            )}

            <button
              type="submit"
              disabled={stage === "sending"}
              className="w-full bg-white text-zinc-950 font-semibold text-sm py-2.5 rounded-lg hover:bg-zinc-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {stage === "sending" ? "Sending…" : "Send sign-in link"}
            </button>

            <p className="text-center text-xs text-zinc-600">
              No password needed — we&apos;ll email you a link.
            </p>
          </form>
        )}
      </div>
    </main>
  );
}
