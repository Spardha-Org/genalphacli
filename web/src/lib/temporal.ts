import { Client, Connection } from "@temporalio/client";

let client: Client | null = null;

export async function getTemporalClient(): Promise<Client> {
  if (!client) {
    const connection = await Connection.connect({
      address: process.env.TEMPORAL_ADDRESS || "localhost:7233",
    });
    client = new Client({ connection, namespace: "default" });
  }
  return client;
}

export const TASK_QUEUES = {
  PARSE: "genalpha-parse",
  GENERATE: "genalpha-generate",
} as const;
