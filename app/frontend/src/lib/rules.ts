import type { Answers, FieldErrors, StepId } from "./types";

/** Reglas de la encuesta: mismas que valida el backend (app/backend/api/rules.py). */

export const STEP_FIELDS: Record<StepId, string[]> = {
  hogar: ["es_hogar_secundario", "ubigeo", "n_miembros"],
  vivienda: ["tipo_vivienda", "material_pared", "material_piso", "total_habitaciones", "total_dormitorios"],
  servicios: ["tenencia_vivienda", "fuente_agua", "agua_todos_los_dias", "conexion_bano", "combustible_cocina", "tiene_internet"],
  integrantes: ["jefe_mujer", "jefe_edad", "educ_jefe", "n_ninos_0_5", "n_menores_14", "n_6_13", "n_mayores_65", "otro_mas_estudios", "educ_max_hogar"],
  trabajo: ["jefe_ocupado", "jefe_horas_semanales", "jefe_cat_ocupacional", "jefe_empresa_ruc", "jefe_sin_pension", "n_ocupados"],
};

export const ALL_STEPS: StepId[] = ["hogar", "vivienda", "servicios", "integrantes", "trabajo"];

export function visibleSteps(a: Answers): StepId[] {
  return a.es_hogar_secundario ? ALL_STEPS.filter((s) => s !== "vivienda") : ALL_STEPS;
}

export const needsWaterFrequency = (a: Answers) => a.fuente_agua !== undefined && [1, 2, 3].includes(a.fuente_agua);
export const isSolo = (a: Answers) => a.n_miembros === 1;
export const jefeIsSenior = (a: Answers) => (a.jefe_edad ?? 0) >= 65;
export const menores14 = (a: Answers) => a.n_ninos_0_5 + a.n_6_13;
export const adultos14a64 = (a: Answers) => (a.n_miembros ?? 0) - menores14(a) - a.n_mayores_65;

/** Cupos libres para seguir sumando personas en el desglose por edades. */
export function freeAgeSlots(a: Answers): number {
  const n = a.n_miembros ?? 0;
  // Si la jefatura tiene menos de 65 años, ella ocupa un cupo del grupo 14-64.
  const reserved = jefeIsSenior(a) ? 0 : 1;
  return Math.max(0, n - menores14(a) - a.n_mayores_65 - reserved);
}

export const minMayores65 = (a: Answers) => (jefeIsSenior(a) ? 1 : 0);

/** Máximo de personas ocupadas: el empleo se mide en personas de 14 años a más. */
export function maxOcupados(a: Answers): number {
  const enEdad = (a.n_miembros ?? 0) - menores14(a);
  return Math.max(0, enEdad - (a.jefe_ocupado === 0 ? 1 : 0));
}

/** Como en la ENAHO (P510A1), el registro del lugar de trabajo no se pregunta a trabajadores del hogar (código 0). */
export const asksWorkplaceRegistry = (a: Answers) => a.jefe_cat_ocupacional !== 6;

export const higherEducationAvailable = (a: Answers) => a.educ_jefe !== undefined && a.educ_jefe < 11;

/** Ajustes automáticos tras cada respuesta, para que la encuesta no permita estados incoherentes. */
export function reconcile(prev: Answers): Answers {
  const a = { ...prev };
  if (a.total_habitaciones !== undefined && a.total_dormitorios !== undefined && a.total_dormitorios > a.total_habitaciones) {
    a.total_dormitorios = a.total_habitaciones;
  }
  if (!needsWaterFrequency(a)) a.agua_todos_los_dias = undefined;

  if (isSolo(a)) {
    a.n_ninos_0_5 = 0;
    a.n_6_13 = 0;
    if (a.jefe_edad !== undefined) a.n_mayores_65 = jefeIsSenior(a) ? 1 : 0;
    a.otro_mas_estudios = false;
    if (a.jefe_ocupado !== undefined) a.n_ocupados = a.jefe_ocupado;
  } else if (a.n_miembros !== undefined) {
    // Si se reduce el número de integrantes, recortar el desglose sin dejarlo incoherente.
    const n = a.n_miembros;
    a.n_mayores_65 = Math.max(minMayores65(a), Math.min(a.n_mayores_65, jefeIsSenior(a) ? n : n - 1));
    const cupoMenores = Math.max(0, n - a.n_mayores_65 - (jefeIsSenior(a) ? 0 : 1));
    if (menores14(a) > cupoMenores) {
      const exceso = menores14(a) - cupoMenores;
      const quitar613 = Math.min(a.n_6_13, exceso);
      a.n_6_13 -= quitar613;
      a.n_ninos_0_5 = Math.max(0, a.n_ninos_0_5 - (exceso - quitar613));
    }
  }

  if (!higherEducationAvailable(a)) a.otro_mas_estudios = a.educ_jefe === undefined ? a.otro_mas_estudios : false;
  if (a.educ_max_hogar !== undefined && a.educ_jefe !== undefined && a.educ_max_hogar <= a.educ_jefe) {
    a.educ_max_hogar = undefined;
  }
  if (!isSolo(a) && a.jefe_ocupado !== undefined && a.n_miembros !== undefined && maxOcupados(a) === 0) a.n_ocupados = 0;
  if (a.n_ocupados !== undefined) {
    a.n_ocupados = Math.min(a.n_ocupados, maxOcupados(a));
    if (a.jefe_ocupado === 1 && a.n_ocupados < 1 && maxOcupados(a) >= 1 && !isSolo(a)) a.n_ocupados = 1;
  }
  return a;
}

const REQUIRED = "Responde esta pregunta para continuar.";

/** Errores que impiden avanzar desde un paso. */
export function stepErrors(step: StepId, a: Answers): FieldErrors {
  const e: FieldErrors = {};
  const need = (field: keyof Answers, msg = REQUIRED) => {
    if (a[field] === undefined || a[field] === "") e[field] = msg;
  };
  switch (step) {
    case "hogar":
      need("es_hogar_secundario", "Elige una opción.");
      need("ubigeo", "Elige el distrito (o «Prefiero no indicarlo»).");
      need("n_miembros", "Indica cuántas personas viven en el hogar.");
      break;
    case "vivienda":
      need("tipo_vivienda", "Elige el tipo de vivienda.");
      need("material_pared", "Elige el material de las paredes.");
      need("material_piso", "Elige el material del piso.");
      need("total_habitaciones", "Indica el número de habitaciones.");
      need("total_dormitorios", "Indica cuántas se usan para dormir.");
      if (a.total_habitaciones !== undefined && a.total_dormitorios !== undefined && a.total_dormitorios > a.total_habitaciones) {
        e.total_dormitorios = "No puede haber más dormitorios que habitaciones.";
      }
      break;
    case "servicios":
      need("tenencia_vivienda", "Elige una opción.");
      need("fuente_agua", "Elige de dónde obtienen el agua.");
      if (needsWaterFrequency(a)) need("agua_todos_los_dias", "Indica si tienen agua todos los días.");
      need("conexion_bano", "Elige una opción.");
      need("combustible_cocina", "Elige una opción.");
      need("tiene_internet", "Elige una opción.");
      break;
    case "integrantes":
      need("jefe_mujer", "Elige una opción.");
      need("jefe_edad", "Indica la edad.");
      need("educ_jefe", "Elige el nivel de estudios.");
      if (a.jefe_edad !== undefined && (a.jefe_edad < 18 || a.jefe_edad > 100)) e.jefe_edad = "Ingresa una edad entre 18 y 100 años.";
      if (!isSolo(a)) {
        if (jefeIsSenior(a) && a.n_mayores_65 < 1) e.n_mayores_65 = "Cuenta a la jefa o jefe en este grupo.";
        if (adultos14a64(a) < (jefeIsSenior(a) ? 0 : 1)) e.n_6_13 = "Las edades suman más personas que el hogar.";
        if (higherEducationAvailable(a)) {
          need("otro_mas_estudios", "Elige una opción.");
          if (a.otro_mas_estudios) need("educ_max_hogar", "Elige el nivel más alto alcanzado.");
        }
      }
      break;
    case "trabajo":
      need("jefe_ocupado", "Elige una opción.");
      if (a.jefe_ocupado === 1) {
        need("jefe_horas_semanales", "Indica las horas trabajadas.");
        if (a.jefe_horas_semanales !== undefined && (a.jefe_horas_semanales < 0 || a.jefe_horas_semanales > 100)) {
          e.jefe_horas_semanales = "Ingresa entre 0 y 100 horas.";
        }
        need("jefe_cat_ocupacional", "Elige una opción.");
        if (asksWorkplaceRegistry(a)) need("jefe_empresa_ruc", "Elige una opción.");
      }
      need("jefe_sin_pension", "Elige una opción.");
      if (!isSolo(a)) need("n_ocupados", "Indica cuántas personas trabajaron.");
      break;
  }
  return e;
}

/** Convierte las respuestas de la interfaz al contrato exacto de POST /api/v1/surveys/validate. */
export function toPayload(a: Answers): Record<string, unknown> {
  const sec = a.es_hogar_secundario === true;
  const ocupado = a.jefe_ocupado === 1;
  const educMax = a.otro_mas_estudios && a.educ_max_hogar !== undefined ? a.educ_max_hogar : a.educ_jefe;
  return {
    es_hogar_secundario: sec,
    ubigeo: a.ubigeo ?? "__nuevo_distrito__",
    n_miembros: a.n_miembros,
    tipo_vivienda: sec ? null : a.tipo_vivienda,
    material_pared: sec ? null : a.material_pared,
    material_piso: sec ? null : a.material_piso,
    total_habitaciones: sec ? null : a.total_habitaciones,
    total_dormitorios: sec ? null : a.total_dormitorios,
    tenencia_vivienda: a.tenencia_vivienda,
    fuente_agua: a.fuente_agua,
    agua_todos_los_dias: needsWaterFrequency(a) ? a.agua_todos_los_dias : null,
    conexion_bano: a.conexion_bano,
    combustible_cocina: a.combustible_cocina,
    tiene_internet: a.tiene_internet,
    jefe_mujer: a.jefe_mujer,
    jefe_edad: a.jefe_edad,
    educ_jefe: a.educ_jefe,
    educ_max_hogar: educMax,
    n_ninos_0_5: a.n_ninos_0_5,
    n_menores_14: menores14(a),
    n_mayores_65: a.n_mayores_65,
    jefe_ocupado: a.jefe_ocupado,
    jefe_horas_semanales: ocupado ? a.jefe_horas_semanales : null,
    jefe_cat_ocupacional: ocupado ? a.jefe_cat_ocupacional : null,
    jefe_empresa_ruc: ocupado ? (asksWorkplaceRegistry(a) ? a.jefe_empresa_ruc : 0) : null,
    jefe_sin_pension: a.jefe_sin_pension,
    n_ocupados: isSolo(a) ? a.jefe_ocupado : a.n_ocupados,
  };
}

/** Paso al que pertenece un campo (para llevar al usuario al error que devuelva el servidor). */
export function stepOfField(field: string): StepId | undefined {
  return ALL_STEPS.find((s) => STEP_FIELDS[s].includes(field));
}
