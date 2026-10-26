import { FormEvent, useState } from "react";
import { api } from "../lib/api";
import { Button, Card, PageHeader, Textarea, useToast } from "../components/ui";

type ToolCall = { name: string; arguments: unknown; ok: boolean; error: string | null; duration_ms: number };
type Message = { role: "user" | "assistant"; content: string; tool_calls?: ToolCall[] };

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [toastMessage, setToastMessage] = useState("");
  const toast = useToast();

  async function send(event?: FormEvent) {
    event?.preventDefault();
    const content = input.trim();
    if (!content || pending) return;
    const next = [...messages, { role: "user" as const, content }];
    setMessages(next);
    setInput("");
    setPending(true);
    try {
      const result = await api<{ reply: string; tool_calls: ToolCall[] }>("/chat", {
        method: "POST",
        json: { messages: next.slice(-20).map(({ role, content: text }) => ({ role, content: text })) },
      });
      setMessages([...next, { role: "assistant", content: result.reply, tool_calls: result.tool_calls }]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Chat request failed";
      toast(message);
      setToastMessage(message);
      window.setTimeout(() => setToastMessage(""), 5000);
      setMessages(next.slice(0, -1));
      setInput(content);
    } finally {
      setPending(false);
    }
  }

  return <>
    <PageHeader title="Chat" description="Ask questions using the tools available to your account."
      action={<Button variant="secondary" disabled={pending} onClick={() => { setMessages([]); setInput(""); }}>New chat</Button>} />
    {toastMessage && <div role="alert" className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{toastMessage}</div>}
    <Card className="flex min-h-[60vh] flex-col">
      <div className="flex-1 space-y-5" aria-live="polite">
        {messages.length === 0 && <p className="py-12 text-center text-sm text-muted-foreground">Start a conversation.</p>}
        {messages.map((message, index) => <div key={index} className={message.role === "user" ? "ml-auto max-w-[85%]" : "mr-auto max-w-[85%]"}>
          <div className={`whitespace-pre-wrap rounded-xl px-4 py-3 text-sm ${message.role === "user" ? "bg-primary/15" : "bg-muted"}`}>
            <div className="mb-1 text-xs font-semibold uppercase text-muted-foreground">{message.role}</div>
            {message.content}
          </div>
          {message.role === "assistant" && message.tool_calls?.length ? <div className="mt-2 flex flex-wrap gap-2">
            {message.tool_calls.map((call, callIndex) => <details key={`${call.name}-${callIndex}`} className="rounded-lg border border-border bg-black/20 px-3 py-2 text-xs">
              <summary className="cursor-pointer"><span className="font-medium">{call.name}</span> · {call.ok ? "ok" : "failed"} · {call.duration_ms} ms</summary>
              <pre className="mt-2 max-w-full overflow-auto whitespace-pre-wrap text-muted-foreground">{JSON.stringify(call.arguments, null, 2)}</pre>
              {call.error && <p className="mt-2 text-red-300">{call.error}</p>}
            </details>)}
          </div> : null}
        </div>)}
        {pending && <p className="text-sm text-muted-foreground">Thinking…</p>}
      </div>
      <form onSubmit={send} className="mt-6 flex items-end gap-3">
        <Textarea value={input} maxLength={8000} rows={3} placeholder="Write a message…" disabled={pending}
          onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); } }} />
        <Button type="submit" disabled={pending || !input.trim()}>{pending ? "Sending…" : "Send"}</Button>
      </form>
    </Card>
  </>;
}
