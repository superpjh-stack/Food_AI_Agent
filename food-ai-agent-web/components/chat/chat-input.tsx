"use client";

import { useState, useRef, useCallback } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
}

export function ChatInput({ onSend, isStreaming }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, isStreaming, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 120) + "px";
    }
  };

  return (
    <div className="flex items-end gap-2 border-t bg-card p-3">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        placeholder={isStreaming ? "AI is responding..." : "Ask about menus, recipes, HACCP..."}
        disabled={isStreaming}
        rows={1}
        className="flex-1 resize-none rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
      />
      <button
        onClick={handleSubmit}
        disabled={isStreaming || !value.trim()}
        className="shrink-0 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {isStreaming ? "..." : "Send"}
      </button>
    </div>
  );
}
