import { useRef, useState } from "react";
import { Send, FileText, Sparkles, User } from "lucide-react";
import { streamChat, type Citation } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export function ChatPanel({ collectionId, hasDocuments }: { collectionId: string; hasDocuments: boolean }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const conversationId = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    });
  };

  const send = async () => {
    const question = input.trim();
    if (!question || streaming) return;

    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user", content: question },
      { role: "assistant", content: "" },
    ]);
    setStreaming(true);
    scrollToBottom();

    const appendToAssistant = (fn: (m: ChatMessage) => ChatMessage) => {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last && last.role === "assistant") next[next.length - 1] = fn(last);
        return next;
      });
    };

    await streamChat(collectionId, question, conversationId.current, {
      onMeta: (id) => {
        conversationId.current = id;
      },
      onToken: (token) => {
        appendToAssistant((m) => ({ ...m, content: m.content + token }));
        scrollToBottom();
      },
      onCitations: (citations) => {
        appendToAssistant((m) => ({ ...m, citations }));
      },
      onError: (message) => {
        appendToAssistant((m) => ({
          ...m,
          content: m.content || `Error: ${message}`,
        }));
      },
      onDone: () => {
        setStreaming(false);
        scrollToBottom();
      },
    });
  };

  return (
    <div className="flex h-[640px] flex-col rounded-xl border bg-card shadow-soft">
      <div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto p-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-3 rounded-full bg-primary/10 p-4">
              <Sparkles className="h-7 w-7 text-primary" />
            </div>
            <h3 className="text-lg font-semibold">Ask anything about your documents</h3>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">
              {hasDocuments
                ? "Answers are grounded in your uploaded sources and include citations."
                : "Upload a document first, then ask a question here."}
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={cn("flex gap-3", m.role === "user" && "flex-row-reverse")}>
            <div
              className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                m.role === "user" ? "bg-secondary" : "bg-primary text-primary-foreground",
              )}
            >
              {m.role === "user" ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
            </div>
            <div className={cn("max-w-[80%] space-y-2", m.role === "user" && "items-end")}>
              <div
                className={cn(
                  "whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm",
                  m.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-foreground",
                )}
              >
                {m.content || (streaming && i === messages.length - 1 ? <Spinner className="h-4 w-4" /> : "")}
              </div>

              {m.citations && m.citations.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-xs font-medium text-muted-foreground">Sources</p>
                  <div className="flex flex-col gap-1.5">
                    {m.citations.map((c) => (
                      <div
                        key={c.chunk_id}
                        className="rounded-lg border bg-background px-3 py-2 text-xs"
                      >
                        <div className="flex items-center gap-1.5 font-medium">
                          <FileText className="h-3.5 w-3.5 text-primary" />
                          <span className="rounded bg-primary/10 px-1.5 text-primary">[{c.index}]</span>
                          {c.filename}
                          <span className="ml-auto text-muted-foreground">
                            {(c.score * 100).toFixed(0)}% match
                          </span>
                        </div>
                        <p className="mt-1 line-clamp-2 text-muted-foreground">{c.snippet}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="border-t p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
          className="flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={hasDocuments ? "Ask a question..." : "Upload a document to start"}
            className="h-11"
            disabled={streaming}
          />
          <Button type="submit" size="icon" className="h-11 w-11 shrink-0" disabled={streaming || !input.trim()}>
            {streaming ? <Spinner className="h-4 w-4" /> : <Send className="h-4 w-4" />}
          </Button>
        </form>
      </div>
    </div>
  );
}
