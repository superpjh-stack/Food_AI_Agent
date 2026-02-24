"use client";

import { useState, useRef, useEffect } from "react";
import { useChatStore } from "@/lib/stores/chat-store";
import { useChat } from "@/lib/hooks/use-chat";
import { ChatMessage } from "./chat-message";
import { ChatInput } from "./chat-input";
import { usePathname } from "next/navigation";

const PAGE_CONTEXT: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/menu-studio": "Menu Studio",
  "/recipes": "Recipe Library",
  "/kitchen": "Kitchen Mode",
  "/haccp": "HACCP Management",
};

export function ChatPanel() {
  const [expanded, setExpanded] = useState(false);
  const { messages, isStreaming, clearMessages } = useChatStore();
  const { send } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();

  // Auto scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Get current page context
  const currentContext = Object.entries(PAGE_CONTEXT).find(([path]) =>
    pathname.startsWith(path)
  )?.[1] ?? "General";

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="fixed bottom-4 right-4 z-40 flex items-center gap-2 rounded-full bg-primary px-4 py-3 text-sm font-medium text-primary-foreground shadow-lg hover:bg-primary/90 print:hidden"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        AI Assistant
        {messages.length > 0 && (
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/20 text-xs">
            {messages.length}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="fixed bottom-0 right-0 z-40 flex h-[500px] w-[400px] flex-col rounded-tl-lg border-l border-t bg-card shadow-xl print:hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-2.5">
        <div>
          <span className="text-sm font-semibold">AI Assistant</span>
          <span className="ml-2 text-xs text-muted-foreground">
            Context: {currentContext}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={clearMessages}
            className="rounded p-1 text-xs text-muted-foreground hover:bg-muted"
            title="Clear chat"
          >
            Clear
          </button>
          <button
            onClick={() => setExpanded(false)}
            className="rounded p-1 text-muted-foreground hover:bg-muted"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <polyline points="4 14 10 14 10 20" />
              <polyline points="20 10 14 10 14 4" />
              <line x1="14" y1="10" x2="21" y2="3" />
              <line x1="3" y1="21" x2="10" y2="14" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-4">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
            <div>
              <p className="font-medium">AI Food Service Assistant</p>
              <p className="mt-1 text-xs">
                Ask about menus, recipes, HACCP, nutrition...
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <ChatMessage
              key={msg.id}
              message={msg}
              isStreaming={isStreaming && idx === messages.length - 1 && msg.role === "assistant"}
            />
          ))
        )}
      </div>

      {/* Input */}
      <ChatInput onSend={send} isStreaming={isStreaming} />
    </div>
  );
}
