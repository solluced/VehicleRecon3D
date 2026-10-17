import type { Reference, View } from "./types";
export type Anchor = {
  id: string;
  semantic: string;
  image: number;
  world_normalized: number;
  role: "FIT" | "HELD_OUT";
  locked: boolean;
  confidence: number;
  provenance: string;
  observation_id?: string;
};
export type ReconciliationRequest = {
  view: View;
  gauge_view: View;
  reference_role: string;
  axis: "u" | "v";
  image_domain_px: number[];
  affine_domain_px: number[];
  anchors: Anchor[];
  max_scale_change: number;
  allow_extrapolation: boolean;
};
export type Sample = {
  x: number;
  y: number;
  correction: number;
  correction_px: number;
  equivalent_mm: number | null;
  derivative: number;
  source_px: number;
  target_px: number;
  extrapolated: boolean;
};
export type Feature = {
  id: string;
  semantic: string;
  pixel: number[];
  projected_affine: number[];
  projected_raw?: number[];
  rectified_pixel?: number[];
  raw_residual_px: number;
  rectified_residual_px: number;
  tolerance_px: number;
  status?: string;
  delta_px?: number;
  critical?: boolean;
};
export type Magnitude = {
  maximum_correction_px: number;
  maximum_absolute_normalized: number;
  maximum_equivalent_mm: number | null;
  range: number[];
};
export type Stats = {
  max_critical_px: number | null;
  mean_critical_px: number | null;
  held_out_rms_px: number | null;
  failed_critical: number;
};
export type Report = {
  eligible: boolean;
  status: string;
  reasons: string[];
  distortion?: string;
  samples?: Sample[];
  anchors: Anchor[];
  allowed_scale: number[];
  local_scale_range?: number[];
  derivative_extrema?: {
    minimum: { source_normalized: number; derivative: number };
    maximum: { source_normalized: number; derivative: number };
  };
  strictly_monotonic: boolean;
  derivative_positive: boolean;
  foldover: boolean;
  whole_crop?: Magnitude;
  overhangs?: { front: Magnitude | null; rear: Magnitude | null };
  between_datums?: Magnitude;
  extrapolation?: {
    fraction: number;
    fitted_support: number[];
    front_range: number[] | null;
    rear_range: number[] | null;
    policy: string;
  };
  before?: Stats;
  after?: Stats;
  held_out: Feature[];
  feature_comparison?: Feature[];
  rms_fit_correction_px?: number | null;
  rms_heldout_correction_px?: number | null;
  rms_all_landmark_correction_px?: number | null;
};
export type Candidate = {
  id: string;
  revision: number;
  status: string;
  active: boolean;
  freshness: string;
  creator: string;
  view: View;
  request: ReconciliationRequest;
  report: Report;
  reason?: string;
  source_revision?: string;
  source_hashes?: Record<string, string>;
  base_calibration_hash?: string;
  algorithm?: string;
  physical_basis?: string;
};
export type CandidateSummary = Pick<
  Candidate,
  "id" | "revision" | "status" | "active" | "freshness" | "creator" | "view"
>;
export type CalibrationView = {
  crop: number[];
  reference_id?: string;
  source_state?: string;
  source_history?: {
    reference_id: string;
    source_sha256: string;
    crop: number[];
  }[];
};
export type ReconciliationContext = {
  read_only: boolean;
  revision?: string;
  default_request?: ReconciliationRequest;
  calibration?: CalibrationView;
  views?: Partial<Record<View, CalibrationView>>;
  references: Reference[];
  candidates: (CandidateSummary | Candidate)[];
  issue?: string;
};
