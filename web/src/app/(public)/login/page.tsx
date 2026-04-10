"use client";

import { useState, useEffect } from "react";
import { useLogin } from "@/data/hooks";
import Link from "next/link";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const login = useLogin();

  // Resend cooldown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => setCooldown((c) => c - 1), 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;

    login.mutate(email, {
      onSuccess: () => {
        setSubmitted(true);
        setCooldown(30);
      },
    });
  }

  function handleResend() {
    if (cooldown > 0) return;
    login.mutate(email, {
      onSuccess: () => setCooldown(30),
    });
  }

  // "Check your email" state
  if (submitted) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50">
        <div className="max-w-md text-center px-6">
          <div className="text-4xl mb-4">📬</div>
          <h1 className="text-2xl font-bold font-[family-name:var(--font-geist-mono)]">
            Check your email
          </h1>
          <p className="mt-3 text-zinc-400">
            We sent a magic link to{" "}
            <span className="text-zinc-200 font-[family-name:var(--font-geist-mono)]">
              {email}
            </span>
          </p>
          <p className="mt-1 text-sm text-zinc-600">
            Click the link in your email to sign in. It expires in 15 minutes.
          </p>

          <div className="mt-6 space-y-3">
            <button
              onClick={handleResend}
              disabled={cooldown > 0 || login.isPending}
              className="text-sm text-teal-400 hover:text-teal-300 disabled:text-zinc-600 disabled:cursor-not-allowed transition-colors"
            >
              {cooldown > 0
                ? `Resend in ${cooldown}s`
                : login.isPending
                  ? "Sending..."
                  : "Resend magic link"}
            </button>
            <div>
              <button
                onClick={() => {
                  setSubmitted(false);
                  setEmail("");
                }}
                className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
              >
                Not you? Try a different email
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // Email input state
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50">
      <div className="max-w-md w-full px-6">
        <div className="text-center mb-8">
          <Link
            href="/"
            className="text-2xl font-bold font-[family-name:var(--font-geist-mono)] hover:text-teal-400 transition-colors"
          >
            GenAlpha
          </Link>
          <p className="mt-2 text-zinc-500">Sign in with your email</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
            autoFocus
            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 text-sm font-[family-name:var(--font-geist-mono)] text-zinc-50 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500"
          />
          <button
            type="submit"
            disabled={login.isPending || !email.trim()}
            className="w-full rounded-lg bg-teal-500 px-4 py-3 text-sm font-medium text-zinc-950 hover:bg-teal-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {login.isPending ? "Sending..." : "Send magic link"}
          </button>
        </form>

        {login.isError && (
          <p className="mt-3 text-sm text-rose-400 text-center">
            {login.error?.message || "Something went wrong. Try again."}
          </p>
        )}
      </div>
    </main>
  );
}
