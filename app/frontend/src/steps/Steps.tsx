import { Callout, ChoiceCards, DistrictSelect, Question, SectionLabel, Stepper } from "../components/ui";
import { optionsOf, type OptionValue } from "../lib/catalog";
import {
  adultos14a64,
  asksWorkplaceRegistry,
  freeAgeSlots,
  higherEducationAvailable,
  isSolo,
  jefeIsSenior,
  maxOcupados,
  menores14,
  minMayores65,
  needsWaterFrequency,
} from "../lib/rules";
import type { Answers, FieldErrors } from "../lib/types";

export interface StepProps {
  a: Answers;
  set: (field: keyof Answers, value: OptionValue | undefined) => void;
  errors: FieldErrors;
}

const num = (v: OptionValue) => v as number;

/* ---------------------------------------------------------------- 1. Hogar */

export function StepHogar({ a, set, errors }: StepProps) {
  return (
    <>
      <Question field="es_hogar_secundario" error={errors.es_hogar_secundario}>
        <ChoiceCards field="es_hogar_secundario" columns={2} value={a.es_hogar_secundario} onChange={(v) => set("es_hogar_secundario", v)} />
        {a.es_hogar_secundario && (
          <div className="mt-3">
            <Callout tone="warm">
              Como comparten la vivienda con otro hogar, omitiremos las preguntas sobre la construcción de la vivienda y pasaremos
              directo a los servicios de tu hogar.
            </Callout>
          </div>
        )}
      </Question>
      <Question field="ubigeo" kind="control" error={errors.ubigeo}>
        <DistrictSelect value={a.ubigeo} onChange={(v) => set("ubigeo", v)} />
      </Question>
      <Question field="n_miembros" kind="control" error={errors.n_miembros}>
        <Stepper field="n_miembros" value={a.n_miembros} onChange={(v) => set("n_miembros", v)} start={1} />
      </Question>
    </>
  );
}

/* ------------------------------------------------------------- 2. Vivienda */

export function StepVivienda({ a, set, errors }: StepProps) {
  return (
    <>
      <Question field="tipo_vivienda" error={errors.tipo_vivienda}>
        <ChoiceCards field="tipo_vivienda" value={a.tipo_vivienda} onChange={(v) => set("tipo_vivienda", num(v))} />
      </Question>
      <Question field="material_pared" error={errors.material_pared}>
        <ChoiceCards field="material_pared" value={a.material_pared} onChange={(v) => set("material_pared", num(v))} />
      </Question>
      <Question field="material_piso" error={errors.material_piso}>
        <ChoiceCards field="material_piso" value={a.material_piso} onChange={(v) => set("material_piso", num(v))} />
      </Question>
      <Question field="total_habitaciones" kind="control" error={errors.total_habitaciones}>
        <Stepper field="total_habitaciones" value={a.total_habitaciones} onChange={(v) => set("total_habitaciones", v)} start={1} />
      </Question>
      <Question field="total_dormitorios" kind="control" error={errors.total_dormitorios}>
        <Stepper
          field="total_dormitorios"
          value={a.total_dormitorios}
          max={a.total_habitaciones ?? 20}
          start={Math.min(1, a.total_habitaciones ?? 1)}
          onChange={(v) => set("total_dormitorios", v)}
        />
        {a.total_habitaciones !== undefined && (
          <p className="mt-2 text-sm text-cinnamon">Como máximo {a.total_habitaciones}, el total de habitaciones.</p>
        )}
      </Question>
    </>
  );
}

/* ------------------------------------------------------------ 3. Servicios */

export function StepServicios({ a, set, errors }: StepProps) {
  return (
    <>
      <Question field="tenencia_vivienda" error={errors.tenencia_vivienda}>
        <ChoiceCards field="tenencia_vivienda" value={a.tenencia_vivienda} onChange={(v) => set("tenencia_vivienda", num(v))} />
      </Question>
      <Question field="fuente_agua" error={errors.fuente_agua}>
        <ChoiceCards field="fuente_agua" value={a.fuente_agua} onChange={(v) => set("fuente_agua", num(v))} />
      </Question>
      {needsWaterFrequency(a) && (
        <div className="animate-rise">
          <Question field="agua_todos_los_dias" error={errors.agua_todos_los_dias}>
            <ChoiceCards field="agua_todos_los_dias" inline value={a.agua_todos_los_dias} onChange={(v) => set("agua_todos_los_dias", num(v))} />
          </Question>
        </div>
      )}
      <Question field="conexion_bano" error={errors.conexion_bano}>
        <ChoiceCards field="conexion_bano" value={a.conexion_bano} onChange={(v) => set("conexion_bano", num(v))} />
      </Question>
      <Question field="combustible_cocina" error={errors.combustible_cocina}>
        <ChoiceCards field="combustible_cocina" value={a.combustible_cocina} onChange={(v) => set("combustible_cocina", num(v))} />
      </Question>
      <Question field="tiene_internet" error={errors.tiene_internet}>
        <ChoiceCards field="tiene_internet" inline value={a.tiene_internet} onChange={(v) => set("tiene_internet", num(v))} />
      </Question>
    </>
  );
}

/* ---------------------------------------------------------- 4. Integrantes */

function AgeBreakdown({ a, set, errors }: StepProps) {
  const free = freeAgeSlots(a);
  const n = a.n_miembros ?? 0;
  const adultos = adultos14a64(a);
  const segs = [
    { label: "Menores de 14", value: menores14(a), cls: "bg-honey" },
    { label: "De 14 a 64", value: Math.max(0, adultos), cls: "bg-chai" },
    { label: "De 65 a más", value: a.n_mayores_65, cls: "bg-sage" },
  ];
  const error = errors.n_6_13 ?? errors.n_menores_14 ?? errors.n_ninos_0_5 ?? errors.n_mayores_65;
  const rows: { field: "n_ninos_0_5" | "n_6_13" | "n_mayores_65"; label: string; spec: string; min: number }[] = [
    { field: "n_ninos_0_5", label: "De 0 a 5 años", spec: "n_ninos_0_5", min: 0 },
    { field: "n_6_13", label: "De 6 a 13 años", spec: "n_menores_14", min: 0 },
    { field: "n_mayores_65", label: "De 65 años a más", spec: "n_mayores_65", min: minMayores65(a) },
  ];
  return (
    <div id="q-n_6_13" className="scroll-mt-28">
      <fieldset>
        <legend className="font-display text-xl leading-snug font-medium text-espresso sm:text-[1.35rem]">
          ¿Cuántas de las {n} personas del hogar tienen estas edades?
        </legend>
        <p className="mt-1.5 max-w-prose text-[0.95rem] leading-relaxed text-cinnamon">
          No necesitas contar a quienes tienen de 14 a 64 años: los calculamos con el total.
          {jefeIsSenior(a) && ` Incluye a la jefa o jefe del hogar entre las personas de 65 años a más.`}
        </p>
        <div className="mt-4 divide-y divide-rim/70 rounded-2xl border border-rim">
          {rows.map((r) => (
            <div key={r.field} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <label htmlFor={`in-${r.spec}`} className="font-semibold">
                {r.label}
              </label>
              <Stepper
                field={r.spec}
                label={r.label}
                size="md"
                value={a[r.field]}
                min={r.min}
                max={a[r.field] + free}
                onChange={(v) => set(r.field, v ?? r.min)}
              />
            </div>
          ))}
        </div>
      </fieldset>
      <div className="mt-4" aria-live="polite">
        <div className="flex h-2.5 overflow-hidden rounded-full bg-subtle">
          {segs.map((s) => (
            <div key={s.label} className={`${s.cls} transition-all duration-300`} style={{ width: n ? `${(s.value / n) * 100}%` : 0 }} />
          ))}
        </div>
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-cinnamon">
          {segs.map((s) => (
            <li key={s.label} className="flex items-center gap-1.5">
              <span className={`size-2.5 rounded-full ${s.cls}`} />
              {s.label}: <span className="font-mono font-semibold text-espresso tabular-nums">{s.value}</span>
            </li>
          ))}
        </ul>
      </div>
      {error && (
        <p role="alert" className="mt-3 rounded-xl bg-brick-tint px-3 py-2 text-sm font-medium text-brick">
          {error}
        </p>
      )}
    </div>
  );
}

export function StepIntegrantes(props: StepProps) {
  const { a, set, errors } = props;
  const solo = isSolo(a);
  const higherOptions = optionsOf("educ_jefe").filter((o) => a.educ_jefe !== undefined && num(o.value) > a.educ_jefe);
  return (
    <>
      <SectionLabel>Sobre la jefa o jefe del hogar</SectionLabel>
      <Question field="jefe_mujer" error={errors.jefe_mujer}>
        <ChoiceCards field="jefe_mujer" inline value={a.jefe_mujer} onChange={(v) => set("jefe_mujer", num(v))} />
      </Question>
      <Question field="jefe_edad" kind="control" error={errors.jefe_edad}>
        <Stepper field="jefe_edad" value={a.jefe_edad} onChange={(v) => set("jefe_edad", v)} start={40} clampOnBlur={false} />
      </Question>
      <Question field="educ_jefe" error={errors.educ_jefe}>
        <ChoiceCards field="educ_jefe" value={a.educ_jefe} onChange={(v) => set("educ_jefe", num(v))} />
      </Question>

      <SectionLabel>Las demás personas del hogar</SectionLabel>
      {solo ? (
        <Callout>
          Como el hogar tiene una sola persona, completamos las edades y el nivel de estudios del hogar con los datos de la jefa o jefe.
        </Callout>
      ) : (
        <>
          {a.jefe_edad === undefined ? (
            <Callout>Primero indica la edad de la jefa o jefe del hogar para registrar las edades de los demás.</Callout>
          ) : (
            <AgeBreakdown {...props} />
          )}
          {higherEducationAvailable(a) && (
            <div className="mt-7 border-t border-rim/70 pt-7">
              <Question
                field="otro_mas_estudios"
                label="¿Alguna otra persona del hogar tiene más estudios que la jefa o jefe?"
                help="Piensa en el nivel más alto que alguien del hogar haya aprobado."
                error={errors.otro_mas_estudios}
              >
                <ChoiceCards
                  field="otro_mas_estudios"
                  inline
                  options={[
                    { value: true, label: "Sí" },
                    { value: false, label: "No" },
                  ]}
                  value={a.otro_mas_estudios}
                  onChange={(v) => set("otro_mas_estudios", v)}
                />
              </Question>
              {a.otro_mas_estudios && (
                <div className="animate-rise mt-7">
                  <Question field="educ_max_hogar" error={errors.educ_max_hogar}>
                    <ChoiceCards field="educ_max_hogar" options={higherOptions} value={a.educ_max_hogar} onChange={(v) => set("educ_max_hogar", num(v))} />
                  </Question>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </>
  );
}

/* -------------------------------------------------------------- 5. Trabajo */

const HORAS_RAPIDAS = [
  { h: 20, label: "Medio tiempo · 20 h" },
  { h: 40, label: "40 h" },
  { h: 48, label: "Jornada completa · 48 h" },
];

export function StepTrabajo({ a, set, errors }: StepProps) {
  const solo = isSolo(a);
  const maxOcu = maxOcupados(a);
  return (
    <>
      <Question field="jefe_ocupado" error={errors.jefe_ocupado}>
        <ChoiceCards field="jefe_ocupado" inline value={a.jefe_ocupado} onChange={(v) => set("jefe_ocupado", num(v))} />
      </Question>
      {a.jefe_ocupado === 1 && (
        <div className="animate-rise space-y-0">
          <div className="border-t border-rim/70 pt-7 mt-7">
            <Question field="jefe_horas_semanales" kind="control" error={errors.jefe_horas_semanales}>
              <Stepper
                field="jefe_horas_semanales"
                value={a.jefe_horas_semanales}
                onChange={(v) => set("jefe_horas_semanales", v)}
                min={0}
                start={40}
                clampOnBlur={false}
              />
              <div className="mt-3 flex flex-wrap gap-2">
                {HORAS_RAPIDAS.map((q) => (
                  <button
                    key={q.h}
                    type="button"
                    onClick={() => set("jefe_horas_semanales", q.h)}
                    className={`rounded-full border px-3.5 py-1.5 text-sm font-semibold transition ${
                      a.jefe_horas_semanales === q.h ? "border-chai bg-latte text-chai" : "border-rim bg-surface text-cinnamon hover:border-chai/50"
                    }`}
                  >
                    {q.label}
                  </button>
                ))}
              </div>
            </Question>
          </div>
          <div className="border-t border-rim/70 pt-7 mt-7">
            <Question field="jefe_cat_ocupacional" error={errors.jefe_cat_ocupacional}>
              <ChoiceCards field="jefe_cat_ocupacional" value={a.jefe_cat_ocupacional} onChange={(v) => set("jefe_cat_ocupacional", num(v))} />
            </Question>
          </div>
          {asksWorkplaceRegistry(a) && (
            <div className="animate-rise border-t border-rim/70 pt-7 mt-7">
              <Question field="jefe_empresa_ruc" error={errors.jefe_empresa_ruc}>
                <ChoiceCards field="jefe_empresa_ruc" value={a.jefe_empresa_ruc} onChange={(v) => set("jefe_empresa_ruc", num(v))} />
              </Question>
            </div>
          )}
        </div>
      )}
      <Question field="jefe_sin_pension" error={errors.jefe_sin_pension}>
        <ChoiceCards field="jefe_sin_pension" inline value={a.jefe_sin_pension} onChange={(v) => set("jefe_sin_pension", num(v))} />
      </Question>
      {solo ? (
        <div className="border-t border-rim/70 pt-7">
          <Callout>Como el hogar tiene una sola persona, el número de personas que trabajan se completa con la respuesta anterior.</Callout>
        </div>
      ) : (
        <Question field="n_ocupados" kind="control" error={errors.n_ocupados}>
          <Stepper
            field="n_ocupados"
            value={a.n_ocupados}
            min={a.jefe_ocupado === 1 ? 1 : 0}
            max={maxOcu}
            start={a.jefe_ocupado === 1 ? 1 : 0}
            onChange={(v) => set("n_ocupados", v)}
          />
          <p className="mt-2 text-sm text-cinnamon">
            Hay {maxOcu + (a.jefe_ocupado === 0 ? 1 : 0)} {maxOcu + (a.jefe_ocupado === 0 ? 1 : 0) === 1 ? "persona" : "personas"} de 14 años a más en
            el hogar.
          </p>
        </Question>
      )}
    </>
  );
}
