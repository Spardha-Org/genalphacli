"use client";

import { useEffect, useState, useCallback } from "react";

export interface ServiceStatus {
  status: string;
  errorMessage?: string | null;
  framework?: string | null;
  metadata?: Record<string, unknown> | null;
}

export function useServiceStatus(serviceId: string | null) {
  const [status, setStatus] = useState<ServiceStatus | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!serviceId) return;

    const evtSource = new EventSource(`/api/services/${serviceId}/status`);

    evtSource.onopen = () => setConnected(true);

    evtSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ServiceStatus;
        setStatus(data);

        // Close on terminal states
        if (["parsed", "complete", "failed", "timed_out", "deleted"].includes(data.status)) {
          evtSource.close();
          setConnected(false);
        }
      } catch {
        // Ignore parse errors
      }
    };

    evtSource.onerror = () => {
      evtSource.close();
      setConnected(false);
    };

    return () => {
      evtSource.close();
      setConnected(false);
    };
  }, [serviceId]);

  return { status, connected };
}
