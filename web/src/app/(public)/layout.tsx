"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

let queryClient: QueryClient | undefined;

function getQueryClient() {
  if (typeof window === "undefined") return new QueryClient();
  if (!queryClient) queryClient = new QueryClient();
  return queryClient;
}

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={getQueryClient()}>
      {children}
    </QueryClientProvider>
  );
}
