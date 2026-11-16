import { countLabel, labelOf } from "./catalog";
import { adultos14a64, isSolo, menores14, needsWaterFrequency } from "./rules";
import type { Answers, StepId, SummaryItem } from "./types";

export const STEP_META: Record<StepId, { title: string; short: string; subtitle: string }> = {
  hogar: { title: "Tu hogar", short: "Hogar", subtitle: "Empecemos por lo básico: cuántas personas viven contigo y dónde." },
  vivienda: { title: "La vivienda", short: "Vivienda", subtitle: "Cómo es el lugar donde vive tu hogar." },
  servicios: { title: "Tenencia y servicios", short: "Servicios", subtitle: "Agua, desagüe, cocina e internet." },
  integrantes: { title: "Integrantes y estudios", short: "Integrantes", subtitle: "Edades de quienes viven en el hogar y nivel de estudios." },
  trabajo: { title: "Trabajo y pensiones", short: "Trabajo", subtitle: "Para terminar, la situación laboral del hogar." },
};

const has = (v: unknown) => v !== undefined && v !== null;

/** Resumen legible por paso (ficha viva y revisión). Solo incluye lo ya respondido. */
export function summarizeStep(step: StepId, a: Answers): SummaryItem[] {
  const out: SummaryItem[] = [];
  const add = (label: string, value: string | undefined | false) => {
    if (value) out.push({ label, value });
  };
  switch (step) {
    case "hogar":
      add("Situación", has(a.es_hogar_secundario) && (a.es_hogar_secundario ? "Comparte la vivienda con otro hogar" : "Hogar principal"));
      add("Distrito", has(a.ubigeo) && labelOf("ubigeo", a.ubigeo));
      add("Integrantes", has(a.n_miembros) && countLabel(a.n_miembros!, "n_miembros"));
      break;
    case "vivienda":
      add("Tipo", has(a.tipo_vivienda) && labelOf("tipo_vivienda", a.tipo_vivienda));
      add("Paredes", has(a.material_pared) && labelOf("material_pared", a.material_pared));
      add("Piso", has(a.material_piso) && labelOf("material_piso", a.material_piso));
      add(
        "Habitaciones",
        has(a.total_habitaciones) &&
          countLabel(a.total_habitaciones!, "total_habitaciones") +
            (has(a.total_dormitorios) ? `, ${countLabel(a.total_dormitorios!, "total_dormitorios")}` : ""),
      );
      break;
    case "servicios":
      add("Tenencia", has(a.tenencia_vivienda) && labelOf("tenencia_vivienda", a.tenencia_vivienda));
      add("Agua", has(a.fuente_agua) && labelOf("fuente_agua", a.fuente_agua));
      add("Frecuencia", needsWaterFrequency(a) && has(a.agua_todos_los_dias) && labelOf("agua_todos_los_dias", a.agua_todos_los_dias));
      add("Baño", has(a.conexion_bano) && labelOf("conexion_bano", a.conexion_bano));
      add("Cocina con", has(a.combustible_cocina) && labelOf("combustible_cocina", a.combustible_cocina));
      add("Internet", has(a.tiene_internet) && labelOf("tiene_internet", a.tiene_internet));
      break;
    case "integrantes":
      add("Jefatura", has(a.jefe_mujer) && labelOf("jefe_mujer", a.jefe_mujer) + (has(a.jefe_edad) ? `, ${a.jefe_edad} años` : ""));
      add("Estudios", has(a.educ_jefe) && labelOf("educ_jefe", a.educ_jefe));
      if (has(a.n_miembros) && !isSolo(a) && has(a.jefe_edad)) {
        add("Edades", `${menores14(a)} menores de 14 · ${adultos14a64(a)} de 14 a 64 · ${a.n_mayores_65} de 65+`);
      }
      add("Nivel más alto", a.otro_mas_estudios === true && has(a.educ_max_hogar) && labelOf("educ_max_hogar", a.educ_max_hogar));
      break;
    case "trabajo":
      add("La jefatura trabajó", has(a.jefe_ocupado) && (a.jefe_ocupado === 1 ? "Sí" : "No"));
      if (a.jefe_ocupado === 1) {
        add("Horas", has(a.jefe_horas_semanales) && countLabel(a.jefe_horas_semanales!, "jefe_horas_semanales"));
        add("Se desempeña como", has(a.jefe_cat_ocupacional) && labelOf("jefe_cat_ocupacional", a.jefe_cat_ocupacional));
        add("Registro", has(a.jefe_empresa_ruc) && labelOf("jefe_empresa_ruc", a.jefe_empresa_ruc));
      }
      add("Pensiones", has(a.jefe_sin_pension) && labelOf("jefe_sin_pension", a.jefe_sin_pension));
      add("Trabajan", has(a.n_ocupados) && countLabel(a.n_ocupados!, "n_ocupados"));
      break;
  }
  return out;
}

/** Frase corta que resume el hogar en la cabecera de la ficha viva. */
export function headline(a: Answers): string {
  const parts: string[] = [];
  if (has(a.n_miembros)) parts.push(a.n_miembros === 1 ? "1 integrante" : `${a.n_miembros} integrantes`);
  if (a.es_hogar_secundario) parts.push("Vivienda compartida");
  else if (has(a.tipo_vivienda)) parts.push(labelOf("tipo_vivienda", a.tipo_vivienda));
  if (has(a.fuente_agua)) parts.push(a.fuente_agua! <= 2 ? "Agua de red pública" : labelOf("fuente_agua", a.fuente_agua));
  return parts.join(" · ");
}
