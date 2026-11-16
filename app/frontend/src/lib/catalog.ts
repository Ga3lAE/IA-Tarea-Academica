import raw from "../../../shared/survey_catalog.json";

export type OptionValue = number | string | boolean;

export interface Option {
  value: OptionValue;
  label: string;
  hint?: string;
  group?: string;
}

export interface FieldSpec {
  type: "boolean" | "select" | "integer" | "choice";
  label: string;
  help?: string;
  options?: Option[];
  options_from?: string;
  min?: number;
  max?: number;
  unit?: [string, string];
  visible_if?: Record<string, number[]>;
}

export const catalog = raw as unknown as { version: string; fields: Record<string, FieldSpec> };

export function spec(name: string): FieldSpec {
  const s = catalog.fields[name];
  if (!s) throw new Error(`Campo desconocido en el catálogo: ${name}`);
  return s;
}

export function optionsOf(name: string): Option[] {
  const s = spec(name);
  return s.options_from ? optionsOf(s.options_from) : (s.options ?? []);
}

export function labelOf(name: string, value: OptionValue | undefined | null): string {
  if (value === undefined || value === null) return "—";
  return optionsOf(name).find((o) => o.value === value)?.label ?? String(value);
}

export function countLabel(n: number, name: string): string {
  const unit = spec(name).unit;
  if (!unit) return String(n);
  return `${n} ${n === 1 ? unit[0] : unit[1]}`;
}
