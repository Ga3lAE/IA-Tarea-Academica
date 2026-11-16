import { ArrowRight, HeartHandshake, Lock, RotateCcw, Save, ShieldCheck, Timer } from "lucide-react";
import { Header, STEP_ICON } from "../components/chrome";
import { ALL_STEPS } from "../lib/rules";
import { hasProgress, loadDraft, clearDraft } from "../lib/storage";
import { STEP_META } from "../lib/summary";

export function Landing({ onStart }: { onStart: () => void }) {
  const draft = loadDraft();
  const resume = hasProgress(draft);

  return (
    <>
      <Header onHome={() => undefined} />
      <main className="mx-auto max-w-6xl px-5 pb-16 sm:px-8">
        <section className="grid items-center gap-10 pt-8 lg:grid-cols-[1.15fr_0.85fr] lg:gap-14 lg:pt-14">
          <div className="animate-rise">
            <p className="eyebrow">Proyecto académico de investigación</p>
            <h1 className="mt-4 font-display text-[2.6rem] leading-[1.05] font-semibold tracking-tight text-espresso sm:text-6xl">
              ¿Cómo viven los hogares de <span className="text-chai italic">Lima y Callao</span>?
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-cinnamon">
              Esta encuesta recoge información sobre la vivienda, los servicios básicos, las personas que forman el hogar, sus estudios y
              su trabajo. Sigue la metodología de la Encuesta Nacional de Hogares (ENAHO) del INEI, con preguntas en lenguaje sencillo.
            </p>

            <ul className="mt-7 flex flex-wrap gap-2.5">
              {[
                { icon: Timer, text: "Unos 3 minutos" },
                { icon: Lock, text: "Anónima: sin nombres, DNI ni dirección" },
                { icon: Save, text: "Se guarda en tu dispositivo si recargas" },
              ].map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-center gap-2 rounded-full border border-rim bg-surface/80 px-3.5 py-2 text-sm font-semibold text-espresso">
                  <Icon aria-hidden className="size-4 text-chai" />
                  {text}
                </li>
              ))}
            </ul>

            <div className="mt-9 flex flex-wrap items-center gap-3">
              <button type="button" className="btn-primary px-7 py-3.5 text-base" onClick={onStart}>
                {resume ? "Continuar donde lo dejé" : "Iniciar encuesta"}
                <ArrowRight aria-hidden className="size-5" />
              </button>
              {resume && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    clearDraft();
                    onStart();
                  }}
                >
                  <RotateCcw aria-hidden className="size-4" />
                  Empezar de nuevo
                </button>
              )}
            </div>
          </div>

          <aside className="card animate-rise p-6 sm:p-7 [animation-delay:80ms]" aria-label="Contenido de la encuesta">
            <p className="eyebrow">Lo que te preguntaremos</p>
            <ol className="mt-5 space-y-4">
              {ALL_STEPS.map((s, i) => {
                const Icon = STEP_ICON[s];
                return (
                  <li key={s} className="flex gap-4">
                    <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-latte text-chai">
                      <Icon aria-hidden className="size-5" />
                    </span>
                    <span>
                      <span className="block font-semibold text-espresso">
                        <span className="mr-1.5 font-mono text-sm text-honey">{String(i + 1).padStart(2, "0")}</span>
                        {STEP_META[s].title}
                      </span>
                      <span className="block text-sm leading-snug text-cinnamon">{STEP_META[s].subtitle}</span>
                    </span>
                  </li>
                );
              })}
            </ol>
          </aside>
        </section>

        <section className="mt-16 grid gap-4 md:grid-cols-3" aria-label="Antes de empezar">
          {[
            {
              icon: HeartHandshake,
              title: "Para qué sirve",
              text: "Para estudiar las condiciones de vida de los hogares urbanos con fines de investigación. No hay respuestas buenas ni malas: responde según tu situación actual.",
            },
            {
              icon: ShieldCheck,
              title: "Qué no es",
              text: "No es un trámite oficial. No da ni quita acceso a programas sociales y no reemplaza la evaluación del SISFOH ni de ninguna entidad del Estado.",
            },
            {
              icon: Lock,
              title: "Tus datos",
              text: "No pedimos datos que te identifiquen. El borrador se guarda solo en este dispositivo y se borra al terminar; el servidor valida las respuestas sin almacenarlas.",
            },
          ].map(({ icon: Icon, title, text }) => (
            <article key={title} className="rounded-3xl border border-rim/80 bg-surface/70 p-6">
              <Icon aria-hidden className="size-6 text-honey" />
              <h2 className="mt-3 font-display text-xl font-semibold text-espresso">{title}</h2>
              <p className="mt-2 text-[0.95rem] leading-relaxed text-cinnamon">{text}</p>
            </article>
          ))}
        </section>
      </main>
      <footer className="border-t border-rim/70 py-6 text-center text-sm text-cinnamon">
        Encuesta de Condiciones de Vida del Hogar · Lima Metropolitana y Callao
      </footer>
    </>
  );
}
