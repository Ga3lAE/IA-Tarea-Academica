import type { ReactNode } from "react";
import { Briefcase, Building, Check, Droplets, House, Users } from "lucide-react";
import { STEP_META, headline, summarizeStep } from "../lib/summary";
import type { Answers, StepId } from "../lib/types";

export const STEP_ICON: Record<StepId, typeof House> = {
  hogar: House,
  vivienda: Building,
  servicios: Droplets,
  integrantes: Users,
  trabajo: Briefcase,
};

/* ------------------------------------------------------------------ Cabecera */

export function Header({ onHome, right }: { onHome: () => void; right?: ReactNode }) {
  return (
    <header className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 pt-5 pb-2 sm:px-8 sm:pt-7">
      <a
        href="/"
        onClick={(e) => {
          e.preventDefault();
          onHome();
        }}
        className="group flex items-center gap-3 rounded-2xl"
      >
        <span className="grid size-10 place-items-center rounded-[0.9rem] bg-chai text-surface shadow-lift transition group-hover:bg-chai-dark">
          <House className="size-5" strokeWidth={2.2} />
        </span>
        <span className="leading-tight">
          <span className="block font-display text-[0.98rem] font-semibold text-espresso sm:text-[1.05rem]">
            <span className="sm:hidden">Vida del Hogar</span>
            <span className="hidden sm:inline">Condiciones de Vida del Hogar</span>
          </span>
          <span className="block text-xs font-semibold tracking-wide text-cinnamon">Lima Metropolitana y Callao</span>
        </span>
      </a>
      {right}
    </header>
  );
}

/* ------------------------------------------------------------------- Progreso */

export function Progress({ steps, current, done }: { steps: StepId[]; current: number; done: (s: StepId) => boolean }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-sm font-semibold text-cinnamon">
          Paso <span className="font-mono text-espresso tabular-nums">{current + 1}</span> de{" "}
          <span className="font-mono tabular-nums">{steps.length}</span>
        </p>
        <p className="text-sm font-medium text-cinnamon">{STEP_META[steps[current]].short}</p>
      </div>
      <ol className="mt-2.5 flex gap-1.5" aria-label="Progreso de la encuesta">
        {steps.map((s, i) => (
          <li
            key={s}
            aria-current={i === current ? "step" : undefined}
            className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${
              i === current ? "bg-chai" : i < current && done(s) ? "bg-honey" : "bg-subtle"
            }`}
          >
            <span className="sr-only">
              {STEP_META[s].title}
              {i < current && done(s) ? " (completado)" : ""}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/* ----------------------------------------------------------------- Ficha viva */

interface LiveSummaryProps {
  answers: Answers;
  steps: StepId[];
  current: StepId | "revision";
  done: (s: StepId) => boolean;
  canVisit: (s: StepId) => boolean;
  onGo: (s: StepId) => void;
}

export function LiveSummary({ answers, steps, current, done, canVisit, onGo }: LiveSummaryProps) {
  const head = headline(answers);
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-rim bg-latte/50 px-5 py-4">
        <p className="eyebrow">Ficha del hogar</p>
        <p className="mt-1 font-display text-lg leading-snug text-espresso">{head || "Se irá completando con tus respuestas"}</p>
      </div>
      <ol className="divide-y divide-rim/70">
        {steps.map((s) => {
          const Icon = STEP_ICON[s];
          const items = summarizeStep(s, answers);
          const isCurrent = s === current;
          const complete = done(s) && !isCurrent;
          const clickable = canVisit(s) && !isCurrent;
          return (
            <li key={s}>
              <button
                type="button"
                disabled={!clickable}
                onClick={() => onGo(s)}
                className={`w-full px-5 py-3.5 text-left transition ${clickable ? "hover:bg-latte/40" : ""} ${isCurrent ? "bg-canvas/70" : ""}`}
              >
                <span className="flex items-center gap-2.5">
                  <span
                    className={`grid size-7 shrink-0 place-items-center rounded-full ${
                      complete ? "bg-sage-tint text-sage" : isCurrent ? "bg-chai text-surface" : "bg-subtle text-cinnamon"
                    }`}
                  >
                    {complete ? <Check className="size-4" strokeWidth={3} /> : <Icon className="size-3.5" />}
                  </span>
                  <span className={`text-sm font-bold ${isCurrent ? "text-chai" : "text-espresso"}`}>{STEP_META[s].title}</span>
                  {clickable && <span className="ml-auto text-xs font-semibold text-chai">Editar</span>}
                </span>
                {items.length > 0 && (
                  <dl className="mt-2 space-y-1 pl-[2.375rem] text-[0.8125rem] leading-snug">
                    {items.map((it) => (
                      <div key={it.label} className="flex gap-1.5">
                        <dt className="shrink-0 text-cinnamon">{it.label}:</dt>
                        <dd className="font-medium text-espresso">{it.value}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
