/**
 * Shared proxy helper — forwards requests from Next.js to Core (:8000).
 *
 * Security: Uses header ALLOWLIST (not pass-through).
 * Never forwards X-Workspace-ID or Host to prevent injection attacks.
 */

const CORE_URL = process.env.CORE_API_URL || "http://localhost:8000";

interface ProxyParams {
  path: string[];
}

export async function proxyToCore(
  request: Request,
  params: Promise<ProxyParams>,
  basePath: string,
): Promise<Response> {
  const { path } = await params;
  const pathString = path.join("/");

  // Build target URL preserving query params
  const requestUrl = new URL(request.url);
  const targetUrl = new URL(`${basePath}/${pathString}`, CORE_URL);
  targetUrl.search = requestUrl.search;

  // Header ALLOWLIST — only forward safe headers
  const safeHeaders = new Headers();
  const cookie = request.headers.get("cookie");
  if (cookie) safeHeaders.set("cookie", cookie);
  const contentType = request.headers.get("content-type");
  if (contentType) safeHeaders.set("content-type", contentType);
  safeHeaders.set("accept", "application/json");

  // Forward the request
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const response = await fetch(targetUrl.toString(), {
    method: request.method,
    headers: safeHeaders,
    body: hasBody ? await request.text() : undefined,
  });

  // Filter response headers — only forward Set-Cookie and Content-Type
  const responseHeaders = new Headers();
  const respContentType = response.headers.get("content-type");
  if (respContentType) responseHeaders.set("content-type", respContentType);
  const setCookie = response.headers.get("set-cookie");
  if (setCookie) responseHeaders.set("set-cookie", setCookie);

  return new Response(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}
