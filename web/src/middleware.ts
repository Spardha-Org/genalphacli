export { auth as middleware } from "@/auth";

export const config = {
  matcher: ["/dashboard/:path*", "/api/parse/:path*", "/api/generate/:path*", "/api/services/:path*", "/api/keys/:path*", "/api/projects/:path*", "/api/workflows/:path*"],
};
