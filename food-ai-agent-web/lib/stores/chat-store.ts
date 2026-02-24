import { create } from "zustand";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: { name: string; status: string; data?: unknown }[];
  citations?: { title: string; type: string }[];
  timestamp: string;
}

interface ChatStore {
  messages: ChatMessage[];
  isStreaming: boolean;
  conversationId: string | null;
  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (content: string) => void;
  setStreaming: (streaming: boolean) => void;
  setConversationId: (id: string | null) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isStreaming: false,
  conversationId: null,
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  updateLastMessage: (content) =>
    set((state) => {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last && last.role === "assistant") {
        messages[messages.length - 1] = { ...last, content: last.content + content };
      }
      return { messages };
    }),
  setStreaming: (isStreaming) => set({ isStreaming }),
  setConversationId: (conversationId) => set({ conversationId }),
  clearMessages: () => set({ messages: [], conversationId: null }),
}));
