"use client";

import { useCallback, useRef } from "react";
import { streamChat } from "@/lib/http";
import { useChatStore } from "@/lib/stores/chat-store";
import { useSiteStore } from "@/lib/stores/site-store";
import type { SSEEvent } from "@/types";

export function useChat() {
  const abortRef = useRef<AbortController | null>(null);
  const store = useChatStore();
  const siteId = useSiteStore((s) => s.currentSite?.id);

  const send = useCallback(
    async (message: string) => {
      if (!siteId) return;

      const ts = new Date().toISOString();
      store.addMessage({
        id: crypto.randomUUID(),
        role: "user",
        content: message,
        timestamp: ts,
      });
      store.setStreaming(true);

      const assistantId = crypto.randomUUID();
      store.addMessage({
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
      });

      let fullText = "";

      try {
        const stream = streamChat({
          message,
          conversation_id: store.conversationId ?? undefined,
          site_id: siteId,
        });

        for await (const event of stream) {
          const sse = event as SSEEvent;

          switch (sse.type) {
            case "text_delta":
              fullText += sse.content ?? "";
              store.updateLastMessage(sse.content ?? "");
              break;
            case "done":
              if (sse.data && typeof sse.data === "object" && "conversation_id" in sse.data) {
                store.setConversationId(
                  (sse.data as { conversation_id: string }).conversation_id
                );
              }
              break;
          }
        }
      } catch {
        store.updateLastMessage("\n\n[Error: Failed to get response]");
      } finally {
        store.setStreaming(false);
      }
    },
    [siteId, store]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    store.setStreaming(false);
  }, [store]);

  return { send, stop };
}
