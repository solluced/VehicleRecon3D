import type { View } from "./types";
export type XYZ = [number, number, number];
export type ResidualRow = {
  id: string;
  observation_id: string;
  world_entity_id: string;
  point_id?: string;
  observation_point_id?: string;
  binding_type?: string;
  side?: number;
  view: View;
  semantic_role: string;
  observed_pixel: number[] | null;
  projected_pixel: number[];
  world: number[];
  residual_px: number | null;
  allowed_tolerance_px: number;
  status: string;
  heat: "PASS" | "NEAR" | "FAIL" | "UNKNOWN";
  critical: boolean;
  required: boolean;
  inferred: boolean;
};
export type SceneData = {
  mirrored_controls?: {
    id: string;
    entity_id: string;
    side: string;
    xyz: number[];
    display_only: boolean;
  }[];
  landmarks: Record<string, number[]>;
  controls: {
    id: string;
    entity_id: string;
    landmark: string | null;
    xyz: number[];
    semantic_role: string;
  }[];
  curves: {
    entity_id: string;
    source_entity_id?: string;
    semantic_role: string;
    kind: string;
    cyclic: boolean;
    world_samples: number[][];
    control_ids: string[];
    control_points: number[][];
    approximate: boolean;
    sample_kind: string;
  }[];
  wheels?: { id: string; xyz: number[]; world_samples: number[][] }[];
  wheel_geometry?: {
    radius_m: number;
    axles: { id: string; x: number; z: number; track_m: number }[];
  };
  symmetry?: { plane: string; declared: boolean; editing: string };
  axes: Record<string, string>;
  units: string;
};
export type WorldSelection = {
  entity: string;
  point?: string;
  kind: "landmark" | "curve" | "control";
  focusKey?: number;
} | null;
export type FitProposal = {
  proposal_id: string;
  revision: string;
  world_entity_id: string;
  old_xyz: number[] | null;
  proposed_xyz: number[] | null;
  status: string;
  rows: ResidualRow[];
  observations_used: string[];
  observations_excluded: { observation_id: string; reason: string }[];
  constraints: unknown[];
  conditioning: Record<string, unknown>;
  rms_residual_px?: number;
  max_residual_px?: number;
  ambiguity?: string;
  method: string;
};
export type Analysis = {
  calibration_source_sha256?: string;
  revision: string;
  read_only: boolean;
  legacy?: boolean;
  legacy_evidence_current?: boolean;
  source_condition?: string;
  unavailable_reason?: string;
  views: Record<
    string,
    {
      crop?: number[];
      calibrated: boolean;
      rectification: string;
      coordinate_system: string;
    }
  >;
  residuals: {
    status: string;
    rows: ResidualRow[];
    summary: Record<string, unknown>;
    coverage?: unknown;
  };
  heat_policy: { near_ratio: number; fail_ratio: number; metric: string };
  coverage: {
    entity_id: string;
    point_id?: string | null;
    views: Record<View, number>;
    semantic_roles: string[];
  }[];
  groups: {
    group: string;
    state: string;
    tolerance_status?: string;
    count: number;
    critical_failures: number;
  }[];
  correspondences: Record<string, unknown>[];
  world_landmarks: Record<string, number[]>;
  scene: SceneData;
  policy: {
    coverage_confirmed: boolean;
    critical_correspondence_ids: string[];
    required_views: View[];
    required_proofs: string[];
  } | null;
  reviews: Record<
    string,
    {
      subject: string | null;
      issue?: string;
      status: {
        state: string;
        decision: string;
        current: boolean;
        reasons: string[];
      };
      record: unknown;
    }
  >;
  wheelbase: {
    world_wheelbase_m: number | null;
    authoritative_wheelbase_m: number | null;
    difference_m: number | null;
    front_axle?: unknown;
    rear_axle?: unknown;
    authority: unknown;
  };
  ratios: {
    status: string;
    rows: {
      entity_id: string;
      semantic_role: string;
      views: Record<string, { ratio: number }>;
      delta: number | null;
      status: string;
    }[];
    reason?: string;
  };
  legacy_ratios?: {
    landmarks: {
      semantic: string;
      ratios: Record<string, number>;
      difference_top_minus_side: number;
      compatibility: string;
    }[];
  };
  legacy_summary?: Record<string, unknown>;
  rectification_candidates: Record<string, unknown>[];
  dimensions: Record<string, unknown>;
  measurements?: unknown[];
  input_identities: Record<string, string>;
};
export const heatColors = {
  PASS: "#65d9b5",
  NEAR: "#f0c769",
  FAIL: "#f18484",
  UNKNOWN: "#90a0b0",
};
