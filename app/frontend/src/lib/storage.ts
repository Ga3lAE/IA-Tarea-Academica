import { EMPTY_ANSWERS, type Answers, type StepId } from "./types";

const KEY = "encuesta-hogar:v1";

export interface Draft {
  answers: Answers;
  step: StepId | "revision";
  updatedAt: string;
}

export function loadDraft(): Draft | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const d = JSON.parse(raw) as Draft;
    return { ...d, answers: { ...EMPTY_ANSWERS, ...d.answers } };
  } catch {
    return null;
  }
}

export function saveDraft(answers: Answers, step: Draft["step"]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify({ answers, step, updatedAt: new Date().toISOString() }));
  } catch {
    /* almacenamiento no disponible (modo privado): la encuesta sigue funcionando sin borrador */
  }
}

export function clearDraft(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* sin acción */
  }
}

const DEFAULT_KEYS = new Set(["n_ninos_0_5", "n_6_13", "n_mayores_65"]);

export function hasProgress(d: Draft | null): boolean {
  return !!d && Object.entries(d.answers).some(([k, v]) => !DEFAULT_KEYS.has(k) && v !== undefined);
}
