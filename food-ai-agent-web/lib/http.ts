import { getAccessToken, refreshAccessToken } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

interface FetchOptions extends RequestInit {
  skipAuth?: boolean;
}

class HttpError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "HttpError";
  }
}

async function http<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { skipAuth = false, headers: customHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(customHeaders as Record<string, string>),
  };

  if (!skipAuth) {
    const token = getAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  let response = await fetch(`${API_BASE}${path}`, { headers, ...rest });

  // Auto-refresh on 401
  if (response.status === 401 && !skipAuth) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${getAccessToken()}`;
      response = await fetch(`${API_BASE}${path}`, { headers, ...rest });
    } else {
      window.location.href = "/login";
      throw new HttpError(401, "UNAUTHORIZED", "Session expired");
    }
  }

  const json = await response.json();

  if (!response.ok || json.success === false) {
    throw new HttpError(
      response.status,
      json.error?.code ?? "UNKNOWN_ERROR",
      json.error?.message ?? "Request failed",
      json.error?.details
    );
  }

  return json.data as T;
}

export { http, HttpError, API_BASE };

/**
 * SSE streaming helper for AI chat.
 */
export async function* streamChat(
  body: Record<string, unknown>
): AsyncGenerator<{ type: string; [key: string]: unknown }> {
  const token = getAccessToken();
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok || !response.body) {
    throw new Error("Failed to connect to chat stream");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        if (data) {
          yield JSON.parse(data);
        }
      }
    }
  }
}
