const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export interface User {
  id: string;
  email: string;
  name: string;
}

export interface Collection {
  id: string;
  name: string;
  description: string;
  document_count: number;
  created_at: string;
}

export interface Document {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  status: "pending" | "processing" | "ready" | "failed";
  error: string;
  chunk_count: number;
  created_at: string;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  filename: string;
  snippet: string;
  score: number;
  index: number;
}

export interface AIInfo {
  chat_provider: string;
  chat_model: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dim: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
}

let accessToken: string | null = localStorage.getItem("sage_access");
let refreshToken: string | null = localStorage.getItem("sage_refresh");

export function setTokens(access: string | null, refresh: string | null) {
  accessToken = access;
  refreshToken = refresh;
  if (access) localStorage.setItem("sage_access", access);
  else localStorage.removeItem("sage_access");
  if (refresh) localStorage.setItem("sage_refresh", refresh);
  else localStorage.removeItem("sage_refresh");
}

export function getAccessToken() {
  return accessToken;
}

async function tryRefresh(): Promise<boolean> {
  if (!refreshToken) return false;
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) {
    setTokens(null, null);
    return false;
  }
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return true;
}

async function request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401 && retry && !path.startsWith("/auth/")) {
    if (await tryRefresh()) return request<T>(path, options, false);
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    const detail = typeof err.detail === "string" ? err.detail : "Request failed";
    throw new Error(detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface StreamHandlers {
  onMeta?: (conversationId: string) => void;
  onToken: (token: string) => void;
  onCitations?: (citations: Citation[]) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
}

export async function streamChat(
  collectionId: string,
  message: string,
  conversationId: string | null,
  handlers: StreamHandlers,
): Promise<void> {
  const res = await fetch(`${API_URL}/collections/${collectionId}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (!res.ok || !res.body) {
    handlers.onError?.("Failed to start chat stream");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const json = line.slice("data:".length).trim();
      if (!json) continue;
      try {
        const evt = JSON.parse(json);
        if (evt.type === "meta") handlers.onMeta?.(evt.conversation_id);
        else if (evt.type === "token") handlers.onToken(evt.value);
        else if (evt.type === "citations") handlers.onCitations?.(evt.citations);
        else if (evt.type === "error") handlers.onError?.(evt.message);
        else if (evt.type === "done") handlers.onDone?.();
      } catch {
        // ignore malformed event
      }
    }
  }
  handlers.onDone?.();
}

export const api = {
  register: (data: { email: string; name: string; password: string }) =>
    request<{ user: User; access_token: string; refresh_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  login: (data: { email: string; password: string }) =>
    request<{ user: User; access_token: string; refresh_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  me: () => request<User>("/auth/me"),

  aiInfo: () => request<AIInfo>("/ai/info"),

  listCollections: () => request<Collection[]>("/collections"),
  createCollection: (data: { name: string; description?: string }) =>
    request<Collection>("/collections", { method: "POST", body: JSON.stringify(data) }),
  getCollection: (id: string) => request<Collection>(`/collections/${id}`),
  deleteCollection: (id: string) =>
    request<void>(`/collections/${id}`, { method: "DELETE" }),

  listDocuments: (collectionId: string) =>
    request<Document[]>(`/collections/${collectionId}/documents`),
  uploadDocument: (collectionId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Document>(`/collections/${collectionId}/documents`, {
      method: "POST",
      body: form,
    });
  },
  deleteDocument: (collectionId: string, documentId: string) =>
    request<void>(`/collections/${collectionId}/documents/${documentId}`, { method: "DELETE" }),
};
