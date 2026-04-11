import { NextRequest, NextResponse } from "next/server";

const CORE_URL = process.env.CORE_API_URL || "http://localhost:8000";

/**
 * Proxy OAuth callback to Core.
 * GitHub redirects here → we forward to Core → Core processes and redirects back to frontend.
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const params = searchParams.toString();

  // Forward the entire query string (code, state, error) to Core
  const coreUrl = `${CORE_URL}/oauth/callback?${params}`;

  const response = await fetch(coreUrl, { redirect: "manual" });

  // Core responds with a 302 redirect — pass it through to the browser
  const location = response.headers.get("location");
  if (location) {
    return NextResponse.redirect(location);
  }

  // Fallback if Core didn't redirect
  return NextResponse.redirect(new URL("/integrations?error=oauth_failed", request.url));
}
