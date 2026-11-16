import type { ReactNode } from "react";
import { Check, ChevronDown, Info, Minus, Plus, TriangleExclamationPoint } from "lucide-react";
import { catalog, optionsOf, spec, type Option, type OptionValue } from "../lib/catalog";

/* ---------------------------------------------------------------- Pregunta */

interface QuestionProps {
  field: string;
  label?: string;
  help?: string;
  error?: string;
  /** "group" para opciones (fieldset/legend); "control" para un campo con <label>. */
  kind?: "group" | "control";
  children: ReactNode;
}

export function Question({ field, label, help, error, kind = "group", children }: QuestionProps) {
  const s = catalog.fields[field] ?? { label: "" };
  const text = label ?? s.label;
  const hint = help ?? s.help;
  const errId = `err-${field}`;
  const helpId = `help-${field}`;
  const describedBy = [hint ? helpId : "", error ? errId : ""].filter(Boolean).join(" ") || undefined;
  const heading = <span className="font-display text-xl leading-snug font-medium text-espresso sm:text-[1.35rem]">{text}</span>;
  const body = (
    <>
      {hint && (
        <p id={helpId} className="mt-1.5 max-w-prose text-[0.95rem] leading-relaxed text-cinnamon">
          {hint}
        </p>
      )}
      <div className="mt-4">{children}</div>
      {error && (
        <p id={errId} role="alert" className="mt-3 flex items-start gap-2 rounded-xl bg-brick-tint px-3 py-2 text-sm font-medium text-brick">
          <TriangleExclamationPoint aria-hidden className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      )}
    </>
  );
  return (
    <div id={`q-${field}`} className="scroll-mt-28 border-t border-rim/70 pt-7 first:border-t-0 first:pt-0 [.section-label+&]:border-t-0 [.section-label+&]:pt-0">
      {kind === "group" ? (
        <fieldset aria-describedby={describedBy} aria-invalid={!!error || undefined}>
          <legend>{heading}</legend>
          {body}
        </fieldset>
      ) : (
        <div>
          <label htmlFor={`in-${field}`}>{heading}</label>
          {body}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------- Opciones (cards) */

interface ChoiceProps {
  field: string;
  value: OptionValue | undefined;
  onChange: (v: OptionValue) => void;
  options?: Option[];
  columns?: 1 | 2 | 3;
  inline?: boolean;
}

export function ChoiceCards({ field, value, onChange, options, columns = 2, inline = false }: ChoiceProps) {
  const opts = options ?? optionsOf(field);
  const grid = inline
    ? "grid-cols-2 sm:flex sm:flex-wrap"
    : columns === 1
      ? "grid-cols-1"
      : columns === 3
        ? "grid-cols-1 sm:grid-cols-3"
        : "grid-cols-1 sm:grid-cols-2";
  return (
    <div className={`grid gap-2.5 ${grid}`}>
      {opts.map((o) => {
        const checked = value === o.value;
        return (
          <label
            key={String(o.value)}
            className={`group relative flex min-h-12 cursor-pointer items-start gap-3 rounded-2xl border bg-surface px-4 py-3 transition
              hover:border-chai/50 hover:bg-latte/40 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-chai has-[:focus-visible]:ring-offset-2 has-[:focus-visible]:ring-offset-surface
              ${checked ? "border-chai bg-latte shadow-[inset_0_0_0_1px_var(--color-chai)]" : "border-rim"}
              ${inline ? "sm:min-w-40 sm:items-center" : ""}`}
          >
            <input
              type="radio"
              name={field}
              className="sr-only"
              checked={checked}
              onChange={() => onChange(o.value)}
            />
            <span
              aria-hidden
              className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border-2 transition ${
                checked ? "border-chai bg-chai text-surface" : "border-rim bg-surface group-hover:border-chai/60"
              } ${inline ? "sm:mt-0" : ""}`}
            >
              {checked && <Check className="size-3" strokeWidth={3.5} />}
            </span>
            <span className="min-w-0">
              <span className="block font-semibold leading-snug">{o.label}</span>
              {o.hint && <span className="mt-0.5 block text-sm leading-snug text-cinnamon">{o.hint}</span>}
            </span>
          </label>
        );
      })}
    </div>
  );
}

/* ----------------------------------------------------------------- Contador */

interface StepperProps {
  field: string;
  value: number | undefined;
  onChange: (v: number | undefined) => void;
  min?: number;
  max?: number;
  start?: number;
  /** Si es falso, un valor menor al mínimo se deja para que lo marque la validación del paso. */
  clampOnBlur?: boolean;
  label?: string;
  size?: "lg" | "md";
}

export function Stepper({ field, value, onChange, min, max, start, clampOnBlur = true, label, size = "lg" }: StepperProps) {
  const s = spec(field);
  const lo = min ?? s.min ?? 0;
  const hi = max ?? s.max ?? 99;
  const unit = s.unit && value !== undefined ? (value === 1 ? s.unit[0] : s.unit[1]) : s.unit?.[1];
  const btn =
    size === "lg"
      ? "size-12 sm:size-[3.25rem]"
      : "size-11";
  const btnCls = `grid ${btn} shrink-0 place-items-center rounded-full border border-rim bg-surface text-espresso transition hover:border-chai hover:bg-latte active:scale-95 disabled:pointer-events-none disabled:opacity-35`;
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        className={btnCls}
        aria-label={`Disminuir ${label ?? s.label}`}
        disabled={value === undefined || value <= lo}
        onClick={() => onChange(Math.max(lo, (value ?? lo) - 1))}
      >
        <Minus className="size-5" />
      </button>
      <input
        id={`in-${field}`}
        type="number"
        inputMode="numeric"
        min={lo}
        max={hi}
        placeholder="—"
        value={value ?? ""}
        aria-label={label}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") return onChange(undefined);
          const n = Math.trunc(Number(raw));
          if (Number.isFinite(n)) onChange(Math.min(hi, Math.max(0, n)));
        }}
        onBlur={() => {
          if (clampOnBlur && value !== undefined && value < lo) onChange(lo);
        }}
        className={`${size === "lg" ? "h-14 w-20 text-3xl" : "h-12 w-16 text-2xl"} rounded-2xl border border-rim bg-canvas/60 text-center font-mono font-semibold tabular-nums text-espresso transition placeholder:text-rim focus:border-chai focus:bg-surface focus:outline-none`}
      />
      <button
        type="button"
        className={btnCls}
        aria-label={`Aumentar ${label ?? s.label}`}
        disabled={value !== undefined && value >= hi}
        onClick={() => onChange(value === undefined ? Math.min(hi, Math.max(lo, start ?? lo)) : Math.min(hi, value + 1))}
      >
        <Plus className="size-5" />
      </button>
      {unit && <span className="text-[0.95rem] font-medium text-cinnamon">{unit}</span>}
    </div>
  );
}

/* ----------------------------------------------------------------- Distrito */

export function DistrictSelect({ value, onChange }: { value: string | undefined; onChange: (v: string) => void }) {
  const opts = optionsOf("ubigeo");
  const groups = [...new Set(opts.map((o) => o.group ?? ""))];
  return (
    <div className="relative max-w-md">
      <select
        id="in-ubigeo"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className={`h-14 w-full cursor-pointer appearance-none rounded-2xl border bg-surface pr-12 pl-4 text-base font-semibold transition hover:border-chai/50 focus:border-chai focus:outline-none ${
          value ? "border-chai/60 text-espresso" : "border-rim text-cinnamon"
        }`}
      >
        <option value="" disabled>
          Elige el distrito
        </option>
        {groups.map((g) => (
          <optgroup key={g} label={g}>
            {opts
              .filter((o) => (o.group ?? "") === g)
              .map((o) => (
                <option key={String(o.value)} value={String(o.value)}>
                  {o.label}
                </option>
              ))}
          </optgroup>
        ))}
      </select>
      <ChevronDown aria-hidden className="pointer-events-none absolute top-1/2 right-4 size-5 -translate-y-1/2 text-chai" />
    </div>
  );
}

/* ------------------------------------------------------------------ Avisos */

export function Callout({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "warm" }) {
  return (
    <div
      className={`animate-rise flex items-start gap-3 rounded-2xl px-4 py-3 text-[0.95rem] leading-relaxed ${
        tone === "warm" ? "bg-latte text-espresso" : "bg-subtle/70 text-cinnamon"
      }`}
    >
      <Info aria-hidden className={`mt-0.5 size-[1.15rem] shrink-0 ${tone === "warm" ? "text-chai" : "text-honey"}`} />
      <div>{children}</div>
    </div>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <p className="section-label eyebrow mb-4 border-t border-rim/70 pt-8 first:border-t-0 first:pt-0">{children}</p>;
}
