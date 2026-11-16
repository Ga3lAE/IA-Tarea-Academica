import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  ChevronDown,
  ChevronLeft,
  CircleCheck,
  ClipboardList,
  LoaderCircle,
  Pencil,
  RotateCcw,
  Save,
  Send,
  TriangleExclamationPoint,
} from "lucide-react";
import { Header, LiveSummary, Progress, STEP_ICON } from "../components/chrome";
import { submitSurvey } from "../lib/api";
import { reconcile, stepErrors, stepOfField, toPayload, visibleSteps } from "../lib/rules";
import { clearDraft, loadDraft, saveDraft } from "../lib/storage";
import { STEP_META, summarizeStep } from "../lib/summary";
import { EMPTY_ANSWERS, type Answers, type FieldErrors, type Receipt, type StepId } from "../lib/types";
import { StepHogar, StepIntegrantes, StepServicios, StepTrabajo, StepVivienda, type StepProps } from "../steps/Steps";

type View = StepId | "revision";

const STEP_COMPONENT: Record<StepId, (p: StepProps) => React.JSX.Element> = {
  hogar: StepHogar,
  vivienda: StepVivienda,
  servicios: StepServicios,
  integrantes: StepIntegrantes,
  trabajo: StepTrabajo,
};

function scrollToFirstError(errors: FieldErrors) {
  const first = Object.keys(errors)[0];
  if (!first) return;
  requestAnimationFrame(() => {
    const el = document.getElementById(`q-${first}`) ?? document.getElementById("q-n_6_13");
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
    el?.querySelector<HTMLElement>("input, select, button")?.focus({ preventScroll: true });
  });
}

export function Survey({ onHome }: { onHome: () => void }) {
  const initial = useMemo(() => loadDraft(), []);
  const [answers, setAnswers] = useState<Answers>(() => initial?.answers ?? EMPTY_ANSWERS);
  const [view, setView] = useState<View>(() => initial?.step ?? "hogar");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);

  const steps = visibleSteps(answers);
  const currentView: View = view !== "revision" && !steps.includes(view) ? "servicios" : view;
  const index = currentView === "revision" ? steps.length - 1 : steps.indexOf(currentView);
  const done = (s: StepId) => Object.keys(stepErrors(s, answers)).length === 0;
  const canVisit = (s: StepId) => steps.slice(0, steps.indexOf(s)).every(done);

  useEffect(() => {
    if (receipt) return;
    saveDraft(answers, currentView);
    setSavedAt(new Date());
  }, [answers, currentView, receipt]);

  const go = (v: View) => {
    setErrors({});
    setSubmitError(null);
    setView(v);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const set: StepProps["set"] = (field, value) => {
    setAnswers((prev) => reconcile({ ...prev, [field]: value as never }));
    setErrors((prev) => {
      if (!(field in prev)) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const next = () => {
    if (currentView === "revision") return;
    const errs = stepErrors(currentView, answers);
    if (Object.keys(errs).length) {
      setErrors(errs);
      scrollToFirstError(errs);
      return;
    }
    go(index + 1 < steps.length ? steps[index + 1] : "revision");
  };

  const back = () => {
    if (currentView === "revision") return go(steps[steps.length - 1]);
    if (index > 0) go(steps[index - 1]);
    else onHome();
  };

  const restart = () => {
    if (!window.confirm("¿Borrar todas las respuestas y empezar una nueva encuesta?")) return;
    clearDraft();
    setAnswers(EMPTY_ANSWERS);
    setReceipt(null);
    go("hogar");
  };

  const submit = async () => {
    const firstInvalid = steps.find((s) => !done(s));
    if (firstInvalid) {
      go(firstInvalid);
      const errs = stepErrors(firstInvalid, answers);
      setErrors(errs);
      scrollToFirstError(errs);
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    const res = await submitSurvey(toPayload(answers));
    setSubmitting(false);
    if (res.ok) {
      clearDraft();
      setReceipt(res.receipt);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else if (res.kind === "invalid") {
      const target = Object.keys(res.errors).map(stepOfField).find(Boolean) ?? steps[0];
      setView(target);
      setErrors(res.errors);
      scrollToFirstError(res.errors);
    } else {
      setSubmitError(res.message);
    }
  };

  const newSurvey = () => {
    clearDraft();
    setAnswers(EMPTY_ANSWERS);
    setReceipt(null);
    setView("hogar");
    onHome();
  };

  if (receipt) return <ReceiptView receipt={receipt} onHome={onHome} onNew={newSurvey} />;

  const headerRight = (
    <div className="flex items-center gap-1 sm:gap-2">
      {savedAt && (
        <span className="hidden items-center gap-1.5 text-xs font-semibold text-sage sm:flex" aria-live="polite">
          <Save aria-hidden className="size-3.5" /> Guardado en este dispositivo
        </span>
      )}
      <button type="button" className="btn-ghost" onClick={restart}>
        <RotateCcw aria-hidden className="size-4" />
        <span className="hidden sm:inline">Reiniciar</span>
      </button>
    </div>
  );

  const summary = (
    <LiveSummary answers={answers} steps={steps} current={currentView} done={done} canVisit={canVisit} onGo={go} />
  );

  return (
    <>
      <Header onHome={onHome} right={headerRight} />
      <main className="mx-auto grid max-w-6xl gap-6 px-5 pt-4 pb-28 sm:px-8 lg:grid-cols-[minmax(0,1fr)_21rem] lg:gap-8 lg:pb-16">
        <section aria-labelledby="step-title" className="min-w-0">
          <div className="mb-5">
            {currentView === "revision" ? (
              <p className="text-sm font-semibold text-cinnamon">Último paso · Revisión</p>
            ) : (
              <Progress steps={steps} current={index} done={done} />
            )}
          </div>

          <details className="card mb-5 overflow-hidden lg:hidden">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-3.5 font-semibold">
              <span className="flex items-center gap-2">
                <ClipboardList aria-hidden className="size-4 text-chai" />
                Ficha del hogar
              </span>
              <ChevronDown aria-hidden className="size-4 text-cinnamon" />
            </summary>
            <div className="border-t border-rim [&>.card]:rounded-none [&>.card]:border-0 [&>.card]:shadow-none">{summary}</div>
          </details>

          <div ref={cardRef} key={currentView} className="card animate-rise p-6 sm:p-9">
            {currentView === "revision" ? (
              <ReviewView answers={answers} steps={steps} onEdit={go} />
            ) : (
              <>
                <header className="mb-8 flex items-start gap-4">
                  <StepBadge step={currentView} />
                  <div>
                    <h1 id="step-title" className="font-display text-3xl font-semibold tracking-tight text-espresso sm:text-[2.1rem]">
                      {STEP_META[currentView].title}
                    </h1>
                    <p className="mt-1 text-cinnamon">{STEP_META[currentView].subtitle}</p>
                  </div>
                </header>
                {(() => {
                  const Step = STEP_COMPONENT[currentView];
                  return <Step a={answers} set={set} errors={errors} />;
                })()}
              </>
            )}
          </div>

          {submitError && (
            <p role="alert" className="mt-4 flex items-start gap-2 rounded-2xl bg-brick-tint px-4 py-3 text-sm font-medium text-brick">
              <TriangleExclamationPoint aria-hidden className="mt-0.5 size-4 shrink-0" />
              {submitError}
            </p>
          )}

          <nav
            aria-label="Navegación de la encuesta"
            className="fixed inset-x-0 bottom-0 z-10 flex items-center justify-between gap-3 border-t border-rim bg-surface/95 px-5 py-3 backdrop-blur sm:px-8 lg:static lg:mt-6 lg:border-0 lg:bg-transparent lg:p-0 lg:backdrop-blur-none"
          >
            <button type="button" className="btn-secondary" onClick={back}>
              <ChevronLeft aria-hidden className="size-4" />
              {index === 0 && currentView !== "revision" ? "Inicio" : "Anterior"}
            </button>
            {currentView === "revision" ? (
              <button type="button" className="btn-primary" onClick={submit} disabled={submitting}>
                {submitting ? <LoaderCircle aria-hidden className="size-5 animate-spin" /> : <Send aria-hidden className="size-4" />}
                {submitting ? "Enviando…" : "Enviar encuesta"}
              </button>
            ) : (
              <button type="button" className="btn-primary" onClick={next}>
                {index + 1 < steps.length ? (
                  "Continuar"
                ) : (
                  <>
                    <span className="sm:hidden">Revisar</span>
                    <span className="hidden sm:inline">Revisar respuestas</span>
                  </>
                )}
                <ArrowRight aria-hidden className="size-4" />
              </button>
            )}
          </nav>
        </section>

        <aside className="hidden lg:block">
          <div className="sticky top-6">{summary}</div>
        </aside>
      </main>
    </>
  );
}

function StepBadge({ step }: { step: StepId }) {
  const Icon = STEP_ICON[step];
  return (
    <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-latte text-chai">
      <Icon aria-hidden className="size-6" />
    </span>
  );
}

/* ------------------------------------------------------------------ Revisión */

function ReviewView({ answers, steps, onEdit }: { answers: Answers; steps: StepId[]; onEdit: (s: StepId) => void }) {
  return (
    <>
      <header className="mb-7">
        <h1 id="step-title" className="font-display text-3xl font-semibold tracking-tight text-espresso sm:text-[2.1rem]">
          Revisa tus respuestas
        </h1>
        <p className="mt-1 text-cinnamon">Si algo no es correcto, puedes editar cada bloque antes de enviar.</p>
      </header>
      <div className="space-y-3.5">
        {steps.map((s) => {
          const Icon = STEP_ICON[s];
          return (
            <section key={s} className="rounded-2xl border border-rim bg-canvas/40 p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="flex items-center gap-2.5 font-bold">
                  <Icon aria-hidden className="size-4 text-chai" />
                  {STEP_META[s].title}
                </h2>
                <button type="button" className="btn-ghost" onClick={() => onEdit(s)}>
                  <Pencil aria-hidden className="size-3.5" /> Editar
                </button>
              </div>
              <dl className="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-2">
                {summarizeStep(s, answers).map((it) => (
                  <div key={it.label}>
                    <dt className="text-xs font-semibold tracking-wide text-cinnamon uppercase">{it.label}</dt>
                    <dd className="font-medium text-espresso">{it.value}</dd>
                  </div>
                ))}
              </dl>
            </section>
          );
        })}
      </div>
      <p className="mt-6 flex items-start gap-2 text-sm text-cinnamon">
        <Check aria-hidden className="mt-0.5 size-4 shrink-0 text-sage" />
        Al enviar, el servidor verifica que las respuestas sean coherentes. No se guarda ningún dato que te identifique.
      </p>
    </>
  );
}

/* --------------------------------------------------------------- Comprobante */

function ReceiptView({ receipt, onHome, onNew }: { receipt: Receipt; onHome: () => void; onNew: () => void }) {
  const fecha = new Date(receipt.received_at).toLocaleString("es-PE", {
    dateStyle: "long",
    timeStyle: "short",
    timeZone: "America/Lima",
  });
  return (
    <>
      <Header onHome={onHome} />
      <main className="mx-auto max-w-3xl px-5 pt-6 pb-16 sm:px-8">
        <div className="card animate-rise overflow-hidden">
          <div className="bg-sage-tint px-6 py-8 text-center sm:px-10">
            <span className="mx-auto grid size-16 place-items-center rounded-full bg-sage text-surface shadow-[0_10px_24px_-12px_rgb(61_107_79/0.7)]">
              <CircleCheck aria-hidden className="size-8" />
            </span>
            <h1 className="mt-5 font-display text-3xl font-semibold text-espresso sm:text-4xl">¡Gracias! Encuesta registrada</h1>
            <p className="mx-auto mt-2 max-w-md text-cinnamon">Tus respuestas fueron recibidas y son coherentes entre sí.</p>
            <dl className="mx-auto mt-6 inline-grid grid-cols-2 gap-x-8 gap-y-1 rounded-2xl bg-surface/80 px-6 py-3 text-left">
              <dt className="text-xs font-semibold tracking-wide text-cinnamon uppercase">Folio</dt>
              <dt className="text-xs font-semibold tracking-wide text-cinnamon uppercase">Fecha</dt>
              <dd className="font-mono text-lg font-semibold tracking-wider text-espresso">{receipt.receipt_id}</dd>
              <dd className="font-medium text-espresso">{fecha}</dd>
            </dl>
          </div>

          <div className="px-6 py-7 sm:px-10">
            <div className="flex items-start gap-3 rounded-2xl border border-honey/40 bg-latte/60 px-4 py-3.5">
              <LoaderCircle aria-hidden className="mt-0.5 size-5 shrink-0 text-honey" />
              <div>
                <p className="font-semibold text-espresso">Estado: lista para evaluación</p>
                <p className="text-sm leading-relaxed text-cinnamon">{receipt.message}</p>
              </div>
            </div>

            <h2 className="mt-8 font-display text-xl font-semibold">Resumen de tu hogar</h2>
            <div className="mt-4 space-y-5">
              {receipt.summary.map((b) => (
                <section key={b.block}>
                  <h3 className="eyebrow">{b.block}</h3>
                  <dl className="mt-2 grid gap-x-6 gap-y-2 sm:grid-cols-2">
                    {b.items.map((it) => (
                      <div key={it.label}>
                        <dt className="text-sm text-cinnamon">{it.label}</dt>
                        <dd className="font-medium">{it.value}</dd>
                      </div>
                    ))}
                  </dl>
                </section>
              ))}
            </div>

            <div className="mt-9 flex flex-wrap gap-3">
              <button type="button" className="btn-primary" onClick={onNew}>
                <RotateCcw aria-hidden className="size-4" />
                Completar una nueva encuesta
              </button>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
