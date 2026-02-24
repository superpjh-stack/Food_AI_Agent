"use client";

import { cn } from "@/lib/utils/cn";
import { ToolCallDisplay } from "./tool-call-display";

interface ChatMessageProps {
  message: {
    id: string;
    role: "user" | "assistant";
    content: string;
    toolCalls?: { name: string; status: string; data?: unknown }[];
    citations?: { title: string; type: string }[];
    timestamp: string;
  };
  isStreaming?: boolean;
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      {/* Avatar */}
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-medium",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
        )}
      >
        {isUser ? "U" : "AI"}
      </div>

      {/* Content */}
      <div className={cn("max-w-[80%] space-y-2", isUser ? "text-right" : "text-left")}>
        <div
          className={cn(
            "inline-block rounded-lg px-3 py-2 text-sm",
            isUser ? "bg-primary text-primary-foreground" : "bg-muted",
          )}
        >
          {/* Tool calls */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <div className="mb-2 space-y-1">
              {message.toolCalls.map((tc, idx) => (
                <ToolCallDisplay key={idx} name={tc.name} status={tc.status} data={tc.data} />
              ))}
            </div>
          )}

          {/* Text content - simple rendering (no react-markdown dependency) */}
          {message.content && (
            <div className="whitespace-pre-wrap">
              {renderContent(message.content)}
              {isStreaming && (
                <span className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-current" />
              )}
            </div>
          )}

          {/* Citations */}
          {message.citations && message.citations.length > 0 && (
            <div className="mt-2 border-t border-current/10 pt-2">
              <div className="text-xs opacity-70">Sources:</div>
              {message.citations.map((c, idx) => (
                <div key={idx} className="text-xs opacity-60">
                  [{idx + 1}] {c.title} ({c.type})
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="text-xs text-muted-foreground">
          {new Date(message.timestamp).toLocaleTimeString("ko-KR", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </div>
  );
}

/** Simple content renderer that highlights allergen warnings. */
function renderContent(content: string): React.ReactNode {
  // Highlight allergen warning patterns
  const parts = content.split(/(\u26A0[^\n]*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("\u26A0")) {
      return (
        <span key={i} className="font-medium text-red-500">
          {part}
        </span>
      );
    }
    return part;
  });
}
