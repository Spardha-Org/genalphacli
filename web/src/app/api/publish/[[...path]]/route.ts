import { proxyToCore } from "@/lib/proxy";

export async function POST(req: Request, ctx: { params: Promise<{ path?: string[] }> }) {
  return proxyToCore(req, ctx.params, "/publish");
}
