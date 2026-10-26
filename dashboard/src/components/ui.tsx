import { ReactNode } from "react";
import { cn } from "../lib/utils";

export function Button({ className, variant = "primary", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost" }) {
  return <button className={cn("rounded-lg px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50", {
    "bg-primary text-black hover:brightness-110": variant === "primary",
    "bg-muted text-foreground hover:bg-white/15": variant === "secondary",
    "bg-destructive text-white hover:brightness-110": variant === "danger",
    "text-muted-foreground hover:bg-muted hover:text-foreground": variant === "ghost",
  }, className)} {...props} />;
}

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn("w-full rounded-lg border border-border bg-black/20 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground", className)} {...props} />;
}

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn("w-full rounded-lg border border-border bg-black/20 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground", className)} {...props} />;
}

export function Select({ className, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn("w-full rounded-lg border border-border bg-black/20 px-3 py-2 text-sm text-foreground", className)} {...props} />;
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <section className={cn("rounded-xl border border-border bg-card p-5 shadow-xl shadow-black/10", className)}>{children}</section>;
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "success" | "danger" | "warning" | "info" | "neutral" }) {
  return <span className={cn("inline-flex rounded-full px-2 py-1 text-xs font-medium", {
    "bg-emerald-500/15 text-emerald-300": tone === "success",
    "bg-red-500/15 text-red-300": tone === "danger",
    "bg-amber-500/15 text-amber-300": tone === "warning",
    "bg-blue-500/15 text-blue-300": tone === "info",
    "bg-muted text-muted-foreground": tone === "neutral",
  })}>{children}</span>;
}

export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
    <div className="max-h-[90vh] w-full max-w-xl overflow-auto rounded-xl border border-border bg-card p-6 shadow-2xl">
      <div className="mb-5 flex items-center justify-between"><h2 className="text-lg font-semibold">{title}</h2><Button variant="ghost" onClick={onClose}>Close</Button></div>
      {children}
    </div>
  </div>;
}

export function PageHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <div className="mb-6 flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-2xl font-semibold">{title}</h1>{description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}</div>{action}</div>;
}

export function Loading() { return <div className="rounded-lg border border-border p-8 text-center text-sm text-muted-foreground">Loading…</div>; }
export function Empty({ children = "Nothing here yet." }: { children?: ReactNode }) { return <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">{children}</div>; }
export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) { return <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">Unable to load data: {error instanceof Error ? error.message : "Unknown error"} {retry && <Button className="ml-3" variant="secondary" onClick={retry}>Retry</Button>}</div>; }

export function useToast() {
  return (message: string) => window.dispatchEvent(new CustomEvent("dashboard-toast", { detail: message }));
}
