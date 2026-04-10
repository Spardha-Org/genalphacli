import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50">
      <div className="max-w-2xl text-center px-6">
        <h1 className="text-5xl font-bold tracking-tight font-[family-name:var(--font-geist-mono)]">
          GenAlpha
        </h1>
        <p className="mt-4 text-xl text-zinc-400">
          Paste a repo. See your API. Get a CLI.
        </p>
        <p className="mt-2 text-zinc-500">
          Parse any GitHub repo, visualize API routes, and download generated
          CLI tools and MCP servers.
        </p>
        <Link
          href="/login"
          className="mt-8 inline-block rounded-lg bg-teal-500 px-6 py-3 text-sm font-medium text-zinc-950 hover:bg-teal-400 transition-colors"
        >
          Get Started
        </Link>
      </div>
    </main>
  );
}
