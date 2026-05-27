import { createClient } from "@supabase/supabase-js";
import NodeWebSocket from "ws";

export function createNodeSupabaseClient(url: string, key: string) {
  return createClient(url, key, {
    auth: { autoRefreshToken: false, persistSession: false },
    realtime: {
      transport: NodeWebSocket as unknown as any,
    },
  });
}