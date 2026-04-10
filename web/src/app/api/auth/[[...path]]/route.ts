import { proxyToCore } from "@/lib/proxy";

export async function GET(req: Request, ctx: { params: Promise<{ path?: string[] }> }) {
  return proxyToCore(req, ctx.params, "/auth");
}

export async function POST(req: Request, ctx: { params: Promise<{ path?: string[] }> }) {
  return proxyToCore(req, ctx.params, "/auth");
}
