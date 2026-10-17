import type { View } from "./types";
export type CVComponent = {
  id: string;
  kind: "polyline" | "spline" | "circle";
  status: string;
  semantic_role: string;
  score: number | null;
  score_meaning?: string;
  points?: number[][];
  original_points?: number[][];
  working_points?: number[][];
  preview_points?: number[][];
  closed?: boolean;
  knots?: { pixel: number[]; left: number[]; right: number[] }[] | null;
  center?: number[];
  radius_px?: number;
  fit?: {
    max_deviation_px: number;
    rms_deviation_px: number;
    certified_max_deviation_px: number;
    tolerance_px: number;
    control_point_count: number;
    original_sample_count: number;
    method: string;
  };
};
export type CVProposal = {
  proposal_id: string;
  provider_id: string;
  provider_version: string;
  capability: string;
  source_revision: string;
  source_sha256: string;
  source_reference_id: string;
  source_role: string;
  source_size: number[];
  crop: number[];
  crop_id: string;
  view: View;
  parameters: Record<string, unknown>;
  created_input_hash: string;
  status: string;
  proposal_revision: number;
  components: CVComponent[];
  warnings: string[];
  rasters: ("mask" | "edges")[];
  raster_bounds?: number[];
  elapsed_ms: number;
  cache_hit: boolean;
};
export type CVProvider = {
  provider_id: string;
  name?: string;
  provider_version: string;
  available: boolean;
  capabilities: string[];
  classification: string;
  deterministic: boolean;
  runtime_requirements?: string[];
};
export type CVJob = {
  job_id: string;
  activity: string;
  result: string | null;
  progress: number;
  proposal_id: string | null;
  error: string | null;
};
export type AssistCanvas = {
  sourceId: string;
  view: View;
  crop?: number[];
  active: boolean;
  visible: boolean;
  opacity: number;
  components: CVComponent[];
  selected: string[];
  original: boolean;
  preview: number[][];
  box?: number[];
  rasters: { url: string; bounds: number[]; opacity: number }[];
  onDown: (p: number[]) => void;
  onMove: (p: number[], dragging: boolean) => void;
  onUp: (p: number[]) => void;
};
export type AssistTool =
  | "inspect"
  | "smart_edge"
  | "magic_select"
  | "detect_wheels"
  | "trace_contour"
  | "foreground"
  | "background";
