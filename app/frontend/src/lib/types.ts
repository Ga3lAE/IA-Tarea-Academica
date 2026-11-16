/** Respuestas tal como las maneja la interfaz (antes de convertirlas al contrato de la API). */
export interface Answers {
  es_hogar_secundario?: boolean;
  ubigeo?: string;
  n_miembros?: number;
  tipo_vivienda?: number;
  material_pared?: number;
  material_piso?: number;
  total_habitaciones?: number;
  total_dormitorios?: number;
  tenencia_vivienda?: number;
  fuente_agua?: number;
  agua_todos_los_dias?: number;
  conexion_bano?: number;
  combustible_cocina?: number;
  tiene_internet?: number;
  jefe_mujer?: number;
  jefe_edad?: number;
  educ_jefe?: number;
  /** Solo interfaz: ¿otra persona del hogar tiene más estudios que la jefatura? */
  otro_mas_estudios?: boolean;
  educ_max_hogar?: number;
  n_ninos_0_5: number;
  /** Solo interfaz: niñas y niños de 6 a 13 años (la API recibe n_menores_14 = 0-5 + 6-13). */
  n_6_13: number;
  n_mayores_65: number;
  jefe_ocupado?: number;
  jefe_horas_semanales?: number;
  jefe_cat_ocupacional?: number;
  jefe_empresa_ruc?: number;
  jefe_sin_pension?: number;
  n_ocupados?: number;
}

export const EMPTY_ANSWERS: Answers = { n_ninos_0_5: 0, n_6_13: 0, n_mayores_65: 0 };

export type StepId = "hogar" | "vivienda" | "servicios" | "integrantes" | "trabajo";

export interface SummaryItem {
  label: string;
  value: string;
}

export interface SummaryBlock {
  block: string;
  items: SummaryItem[];
}

export interface Factor {
  variable: string;
  etiqueta: string;
  valor: string;
  /** Contribución en log-odds del modelo explicador (positiva eleva la estimación). */
  contribucion: number;
}

export interface Prediction {
  probabilidad: number;
  percentil: number;
  nivel: "alto" | "medio" | "bajo";
  en_riesgo: boolean;
  prioritario_top20: boolean;
  umbral_riesgo: number;
  umbral_prioridad: number;
  probabilidad_explicador: number;
  factores_riesgo: Factor[];
  factores_proteccion: Factor[];
  modelo: {
    nombre?: string;
    explicador?: string;
    hogares_entrenamiento: number;
    anios: number[];
    creado: string;
  };
}

export interface Receipt {
  receipt_id: string;
  received_at: string;
  status: string;
  message: string;
  summary: SummaryBlock[];
  prediction?: Prediction;
}

export type FieldErrors = Partial<Record<string, string>>;
