import { ArrowDownRight, ArrowUpRight, ChevronDown, Info, RotateCcw, ShieldCheck } from "lucide-react";
import { Header } from "../components/chrome";
import type { Factor, Prediction, Receipt } from "../lib/types";

const pct = (x: number, dec = 0) => `${(x * 100).toFixed(dec).replace(".", ",")} %`;

const NIVEL: Record<Prediction["nivel"], { titulo: string; texto: string; chip: string; acento: string }> = {
  alto: {
    titulo: "Probabilidad alta",
    texto: "El hogar estaría entre el 20 % de hogares de Lima y Callao con mayor probabilidad estimada de pobreza monetaria.",
    chip: "bg-chai text-surface",
    acento: "bg-chai",
  },
  medio: {
    titulo: "Probabilidad moderada",
    texto: "La estimación supera el umbral de riesgo del modelo, aunque el hogar no estaría entre el 20 % de mayor probabilidad.",
    chip: "bg-honey text-espresso",
    acento: "bg-honey",
  },
  bajo: {
    titulo: "Probabilidad baja",
    texto: "La estimación está por debajo del umbral de riesgo del modelo.",
    chip: "bg-sage text-surface",
    acento: "bg-sage",
  },
};

function Gauge({ p }: { p: Prediction }) {
  const clamp = (x: number) => Math.min(100, Math.max(0, x * 100));
  const marks = [
    { x: p.umbral_riesgo, label: `Umbral de riesgo · ${pct(p.umbral_riesgo)}` },
    { x: p.umbral_prioridad, label: `20 % con mayor probabilidad · desde ${pct(p.umbral_prioridad)}` },
  ];
  return (
    <div className="mt-6" aria-hidden>
      <div className="relative h-3 rounded-full bg-gradient-to-r from-sage-tint via-latte to-chai/30">
        {marks.map((m) => (
          <span key={m.label} className="absolute top-1/2 h-5 w-0.5 -translate-y-1/2 rounded bg-cinnamon/60" style={{ left: `${clamp(m.x)}%` }} />
        ))}
        <span
          className="absolute top-1/2 grid size-6 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border-4 border-surface bg-espresso shadow-card transition-all duration-700"
          style={{ left: `${clamp(p.probabilidad)}%` }}
        />
      </div>
      <div className="mt-2 flex justify-between font-mono text-xs text-cinnamon tabular-nums">
        <span>0 %</span>
        <span>100 %</span>
      </div>
      <ul className="mt-1 space-y-0.5 text-xs text-cinnamon">
        {marks.map((m) => (
          <li key={m.label} className="flex items-center gap-2">
            <span className="h-3 w-0.5 rounded bg-cinnamon/60" /> {m.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

function FactorList({ title, icon, items, max, tone, empty }: {
  title: string;
  icon: React.ReactNode;
  items: Factor[];
  max: number;
  tone: "up" | "down";
  empty: string;
}) {
  return (
    <section className="rounded-2xl border border-rim bg-canvas/40 p-5">
      <h3 className="flex items-center gap-2 font-bold">
        {icon}
        {title}
      </h3>
      {items.length === 0 ? (
        <p className="mt-3 text-sm text-cinnamon">{empty}</p>
      ) : (
        <ul className="mt-4 space-y-3.5">
          {items.map((f) => (
            <li key={f.variable}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="font-semibold text-espresso">{f.etiqueta}</span>
              </div>
              <p className="text-sm leading-snug text-cinnamon">{f.valor}</p>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-subtle">
                <div
                  className={`h-full rounded-full ${tone === "up" ? "bg-chai" : "bg-sage"}`}
                  style={{ width: `${Math.max(6, (Math.abs(f.contribucion) / max) * 100)}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function ResultView({ receipt, onHome, onNew }: { receipt: Receipt; onHome: () => void; onNew: () => void }) {
  const p = receipt.prediction;
  const fecha = new Date(receipt.received_at).toLocaleString("es-PE", { dateStyle: "long", timeStyle: "short", timeZone: "America/Lima" });
  const max = p ? Math.max(0.01, ...[...p.factores_riesgo, ...p.factores_proteccion].map((f) => Math.abs(f.contribucion))) : 1;
  const nivel = p ? NIVEL[p.nivel] : null;

  return (
    <>
      <Header onHome={onHome} />
      <main className="mx-auto max-w-4xl px-5 pt-6 pb-16 sm:px-8">
        <div className="card animate-rise overflow-hidden">
          {p && nivel ? (
            <div className="px-6 pt-8 pb-7 sm:px-10">
              <p className="eyebrow">Resultado de la estimación</p>
              <div className="mt-4 grid items-end gap-6 sm:grid-cols-[auto_1fr]">
                <div>
                  <p className="font-display text-7xl leading-none font-semibold tracking-tight text-espresso sm:text-8xl">
                    {Math.round(p.probabilidad * 100)}
                    <span className="text-4xl sm:text-5xl">%</span>
                  </p>
                  <p className="mt-2 max-w-[16rem] text-sm font-medium text-cinnamon">Probabilidad estimada de pobreza monetaria del hogar</p>
                </div>
                <div className="sm:pb-2">
                  <span className={`inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-bold ${nivel.chip}`}>{nivel.titulo}</span>
                  <p className="mt-3 leading-relaxed text-espresso">{nivel.texto}</p>
                  <p className="mt-2 text-sm leading-relaxed text-cinnamon">
                    Es mayor que la de {Math.min(99, Math.floor(p.percentil))} de cada 100 hogares de Lima y Callao con los que se
                    entrenó el modelo (ENAHO 2024–2025).
                  </p>
                </div>
              </div>
              <Gauge p={p} />
            </div>
          ) : (
            <div className="px-6 py-8 sm:px-10">
              <h1 className="font-display text-3xl font-semibold">Encuesta registrada</h1>
              <p className="mt-2 text-cinnamon">{receipt.message}</p>
            </div>
          )}

          {p && (
            <div className="border-t border-rim px-6 py-7 sm:px-10">
              <h2 className="font-display text-2xl font-semibold">¿Qué pesó más en la estimación?</h2>
              <p className="mt-1 text-sm text-cinnamon">Las barras muestran el peso relativo de cada característica en este hogar.</p>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <FactorList
                  title="Elevan la probabilidad"
                  icon={<ArrowUpRight aria-hidden className="size-4 text-chai" />}
                  items={p.factores_riesgo}
                  max={max}
                  tone="up"
                  empty="Ninguna característica elevó la estimación de forma apreciable."
                />
                <FactorList
                  title="Reducen la probabilidad"
                  icon={<ArrowDownRight aria-hidden className="size-4 text-sage" />}
                  items={p.factores_proteccion}
                  max={max}
                  tone="down"
                  empty="Ninguna característica redujo la estimación de forma apreciable."
                />
              </div>

              <div className="mt-6 rounded-2xl bg-subtle/70 px-5 py-4 text-sm leading-relaxed text-cinnamon">
                <p className="flex items-center gap-2 font-bold text-espresso">
                  <Info aria-hidden className="size-4 text-honey" /> Cómo leer este resultado
                </p>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  <li>Es una estimación estadística hecha con características del hogar; no mide su ingreso ni su gasto.</li>
                  <li>
                    En la evaluación del proyecto con la ENAHO 2025, el modelo identificó a 71 de cada 100 hogares pobres, y 46 de cada 100
                    hogares que marcó en riesgo lo eran realmente: puede equivocarse en ambos sentidos.
                  </li>
                  <li>
                    Los factores provienen de un modelo explicador auxiliar (estimó {pct(p.probabilidad_explicador)} para este hogar), por lo
                    que indican tendencias, no causas.
                  </li>
                </ul>
              </div>

              <p className="mt-4 flex items-start gap-2 text-sm text-cinnamon">
                <ShieldCheck aria-hidden className="mt-0.5 size-4 shrink-0 text-sage" />
                No es un resultado oficial: no da ni quita acceso a programas sociales ni reemplaza la evaluación del SISFOH. Tus respuestas no
                se guardaron.
              </p>
            </div>
          )}

          <div className="border-t border-rim px-6 py-6 sm:px-10">
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center justify-between font-semibold">
                Resumen de tus respuestas
                <ChevronDown aria-hidden className="size-4 text-cinnamon transition group-open:rotate-180" />
              </summary>
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
            </details>
            <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
              <p className="text-xs text-cinnamon">
                Folio <span className="font-mono font-semibold text-espresso">{receipt.receipt_id}</span> · {fecha}
                {p?.modelo?.hogares_entrenamiento
                  ? ` · Modelo Stacking entrenado con ${p.modelo.hogares_entrenamiento.toLocaleString("es-PE")} hogares`
                  : ""}
              </p>
              <button type="button" className="btn-primary" onClick={onNew}>
                <RotateCcw aria-hidden className="size-4" />
                Hacer una nueva estimación
              </button>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
