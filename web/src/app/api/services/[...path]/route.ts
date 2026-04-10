import { proxyToCore } from "@/lib/proxy";

export async function GET(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return proxyToCore(req, ctx.params, "/services");
}

export async function POST(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return proxyToCore(req, ctx.params, "/services");
}

export async function DELETE(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return proxyToCore(req, ctx.params, "/services");
}
