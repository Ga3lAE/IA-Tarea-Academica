import type { FieldErrors, Receipt } from "./types";

export type SubmitResult =
  | { ok: true; receipt: Receipt }
  | { ok: false; kind: "invalid"; errors: FieldErrors }
  | { ok: false; kind: "network" | "server"; message: string };

export async function submitSurvey(payload: Record<string, unknown>): Promise<SubmitResult> {
  let resp: Response;
  try {
    resp = await fetch("/api/v1/surveys/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return {
      ok: false,
      kind: "network",
      message: "No pudimos conectar con el servidor. Tus respuestas siguen guardadas en este dispositivo; inténtalo de nuevo en un momento.",
    };
  }
  if (resp.ok) return { ok: true, receipt: (await resp.json()) as Receipt };
  if (resp.status === 422) {
    const body = (await resp.json().catch(() => ({ errors: [] }))) as { errors?: { field: string; message: string }[] };
    const errors: FieldErrors = {};
    for (const e of body.errors ?? []) errors[e.field] ??= e.message;
    return { ok: false, kind: "invalid", errors };
  }
  return { ok: false, kind: "server", message: "El servidor tuvo un problema al recibir la encuesta. Inténtalo nuevamente." };
}
