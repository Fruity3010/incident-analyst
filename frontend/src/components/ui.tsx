import type { ReactNode } from "react";

export const CRIME_TYPES: Record<string, string> = {
  ransomware: "Ransomware",
  phishing: "Phishing",
  online_fraud: "Online fraud / scam",
  business_email_compromise: "Business email compromise",
  data_breach: "Data breach",
  money_laundering: "Money laundering",
  human_trafficking: "Human trafficking",
  drug_trafficking: "Drug trafficking",
  other: "Other",
};

const CRIME_COLORS: Record<string, { dot: string; badge: string }> = {
  ransomware: { dot: "bg-red-500", badge: "bg-red-50 text-red-700 ring-red-600/15" },
  phishing: { dot: "bg-amber-500", badge: "bg-amber-50 text-amber-800 ring-amber-600/20" },
  online_fraud: { dot: "bg-orange-500", badge: "bg-orange-50 text-orange-700 ring-orange-600/15" },
  business_email_compromise: { dot: "bg-violet-500", badge: "bg-violet-50 text-violet-700 ring-violet-600/15" },
  data_breach: { dot: "bg-sky-500", badge: "bg-sky-50 text-sky-700 ring-sky-600/15" },
  money_laundering: { dot: "bg-emerald-500", badge: "bg-emerald-50 text-emerald-700 ring-emerald-600/15" },
  human_trafficking: { dot: "bg-pink-500", badge: "bg-pink-50 text-pink-700 ring-pink-600/15" },
  drug_trafficking: { dot: "bg-teal-500", badge: "bg-teal-50 text-teal-700 ring-teal-600/15" },
  other: { dot: "bg-gray-400", badge: "bg-gray-50 text-gray-700 ring-gray-500/15" },
};

export const crimeDot = (type: string) => (CRIME_COLORS[type] ?? CRIME_COLORS.other).dot;

export const LANGUAGES: Record<string, string> = { en: "English", fr: "French", es: "Spanish", ar: "Arabic", other: "Other" };

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong.";
}

const ICONS = {
  reports: "M9 12h6m-6 4h6M9 8h2m-4 13h10a2 2 0 0 0 2-2V8.4a2 2 0 0 0-.6-1.4l-3.4-3.4A2 2 0 0 0 13.6 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2Z",
  agent: "M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.4-4 8-9 8a9.9 9.9 0 0 1-4.3-1L3 20l1.3-3.9A7.4 7.4 0 0 1 3 12c0-4.4 4-8 9-8s9 3.6 9 8Z",
  stats: "M4 20V10m6 10V4m6 16v-7m4 7H3",
  plus: "M12 5v14m-7-7h14",
  close: "M6 6l12 12M18 6 6 18",
  back: "M15 18l-6-6 6-6",
  globe: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm-9-9h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3Z",
  tag: "M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9-9-9Zm4.5-4.5h.01",
  language: "M4 5h8M8 3v2m2.5 0C9.7 9.7 7 13 4 15m2.5-6c1 2.2 3 4 5.5 5M13 21l4-9 4 9m-6.7-3h5.4",
  calendar: "M8 3v3m8-3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z",
  tool: "M14.7 6.3a4 4 0 0 0-5.4 5.4l-6 6a1.4 1.4 0 0 0 2 2l6-6a4 4 0 0 0 5.4-5.4l-2.5 2.5-2-.5-.5-2 2.5-2.5Z",
  check: "M5 12.5 10 17 19 7",
  send: "M5 12h14m-6-6 6 6-6 6",
  memory: "M12 3v2m0 14v2M5 12H3m18 0h-2M7 7 5.5 5.5m11.5 0L17 7M7 17l-1.5 1.5M17 17l1.5 1.5M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z",
  upload: "M12 16V4m0 0-4 4m4-4 4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3",
  shield: "M12 3 4.5 6v6c0 4.5 3.2 7.8 7.5 9 4.3-1.2 7.5-4.5 7.5-9V6L12 3Z",
  trash: "M4 7h16M10 11v6m4-6v6M6 7l1 13h10l1-13M9 7V4h6v3",
  spark: "M12 3v4m0 10v4M3 12h4m10 0h4M6.3 6.3l2.8 2.8m5.8 5.8 2.8 2.8m0-11.4-2.8 2.8m-5.8 5.8-2.8 2.8",
};

export type IconName = keyof typeof ICONS;

export function Icon({ name, className = "h-4 w-4" }: { name: IconName; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden>
      <path d={ICONS[name]} />
    </svg>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-gray-900">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-gray-500">{description}</p>}
      </div>
      {actions}
    </div>
  );
}

export function Card({ title, actions, children, className = "" }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-gray-200/80 bg-white shadow-[0_1px_2px_rgba(16,24,40,0.04)] ${className}`}>
      {title && (
        <header className="flex items-center justify-between gap-3 border-b border-gray-100 px-5 py-3.5">
          <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

export function StatTile({ label, value, icon }: { label: string; value: ReactNode; icon: IconName }) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-gray-200/80 bg-white px-5 py-4 shadow-[0_1px_2px_rgba(16,24,40,0.04)]">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-brand-600">
        <Icon name={icon} className="h-5 w-5" />
      </span>
      <div>
        <p className="text-xs font-medium text-gray-500">{label}</p>
        <p className="text-2xl font-semibold tabular-nums tracking-tight text-gray-900">{value}</p>
      </div>
    </div>
  );
}

export function CrimeBadge({ type }: { type: string }) {
  const c = CRIME_COLORS[type] ?? CRIME_COLORS.other;
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${c.badge}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
      {CRIME_TYPES[type] ?? type}
    </span>
  );
}

export function LanguageBadge({ code }: { code: string }) {
  return (
    <span title={LANGUAGES[code] ?? code} className="inline-flex items-center rounded-md bg-gray-100 px-1.5 py-0.5 font-mono text-[11px] font-semibold uppercase text-gray-700">
      {code}
    </span>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 text-sm text-gray-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-200 border-t-brand-500" />
      {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-3.5 py-3 text-sm text-red-700">
      <span>{message}</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="shrink-0 font-medium underline">
          Retry
        </button>
      )}
    </div>
  );
}

export function Empty({ title, icon = "reports", children }: { title: string; icon?: IconName; children?: ReactNode }) {
  return (
    <div className="px-6 py-14 text-center">
      <span className="mx-auto grid h-11 w-11 place-items-center rounded-xl bg-gray-100 text-gray-500">
        <Icon name={icon} className="h-5 w-5" />
      </span>
      <p className="mt-3 text-sm font-semibold text-gray-900">{title}</p>
      {children && <div className="mt-1 text-sm text-gray-500">{children}</div>}
    </div>
  );
}

export function Confidence({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2" title={`Extraction confidence ${pct}%`}>
      <div className="h-1.5 w-16 rounded-full bg-gray-100">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs tabular-nums text-gray-600">{pct}%</span>
    </div>
  );
}

export const inputClass =
  "w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-brand-500 focus:ring-4 focus:ring-brand-100";

export const primaryButton =
  "inline-flex items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50";

export const secondaryButton =
  "inline-flex items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 disabled:opacity-50";

export function formatDate(d: string | null): string {
  if (!d) return "Unknown";
  return new Date(d + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export function countries(r: { locations: { country: string }[] }): string {
  return [...new Set(r.locations.map((l) => l.country))].join(", ") || "—";
}
