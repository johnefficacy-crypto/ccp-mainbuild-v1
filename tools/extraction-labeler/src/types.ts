export type Bbox = [number, number, number, number]; // [xmin, ymin, xmax, ymax] top-left normalized [0..1]

export interface Region {
  page: number;
  bbox: Bbox;
  text_excerpt?: string;
}

export interface LabeledQuestion {
  /** Internal UI ID — not serialized to fixture. */
  id: string;
  question_number: number;
  question_text: string;
  normalized_question_hash?: string;
  regions: Region[];
  notes?: string;
  out_of_scope_v1?: boolean;
}

export interface PaperMeta {
  paper_name: string;
  year: number;
  page_count: number;
}

export interface SessionState {
  documentId: string;
  examId: string;
  paperMeta: PaperMeta;
  questions: LabeledQuestion[];
}
