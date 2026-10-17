import type { Schema } from "./types";
export type SurfaceNode = {
  id: string;
  op: string;
  parameters: Record<string, unknown>;
  dependencies: string[];
  draft: boolean;
  reversed?: string[];
};
export type SurfacePatch = {
  id: string;
  sample: string;
  name?: string;
  semantic_role?: string;
  material_role?: string;
  resolution: number[];
  settings: { mirror?: boolean; normal?: number[] };
  us?: number[];
  vs?: number[];
};
export type Adjacency = {
  a: string;
  b: string;
  edge_a: string;
  edge_b: string;
  reverse: boolean;
  tolerance_m: number;
  max_gap_m?: number;
  rms_gap_m?: number;
  normal_angle_max_deg?: number;
  status?: string;
  samples?: number[][];
  tangent_label?: string;
};
export type SurfaceGraph = {
  schema_version: number;
  nodes: SurfaceNode[];
  patches: SurfacePatch[];
  adjacency?: Adjacency[];
};
export type Validation = { category: string; status: string; message: string };
export type SurfaceContext = {
  revision: string;
  graph: SurfaceGraph | null;
  evaluation_allowed: boolean;
  gate: string;
  cage_boundaries: { id: string; x_range: number[]; points: number[][] }[];
  validation: Validation[];
};
export type Operation = {
  id: string;
  version: number;
  description: string;
  required_inputs: string[];
  optional_inputs: string[];
  parameter_schema: { properties: Record<string, Schema>; required: string[] };
  output_type: string;
  preview_supported: boolean;
  topology_supported: boolean;
  limitation?: string;
};
export type SurfaceCatalog = {
  operations: Operation[];
  capabilities: Record<string, unknown>;
};
export type SurfaceMesh = {
  id: string;
  node_id: string;
  operation: string;
  positions: number[][];
  triangles: number[][];
  normals: number[][];
  face_normals: { origin: number[]; normal: number[] }[];
  resolution: number[];
  issues: string[];
  status: string;
  semantic_role: string;
};
export type SurfacePreview = {
  boundaries?: { id: string; points: number[][] }[];
  revision: string;
  graph_hash: string;
  identity: string;
  quality: string;
  status: string;
  certified_current: boolean;
  label: string;
  topology_label: string;
  authority: string;
  patches: SurfaceMesh[];
  adjacency: Adjacency[];
  corners: Record<
    string,
    { connection: string; gap_m: number; tolerance_m: number; status: string }[]
  >;
  validation: Validation[];
  generation_ms: number;
  sampled_patches: string[];
  evaluated_nodes: string[];
};
export const previewCurrent = (
  preview: SurfacePreview | null,
  revision: string,
) => !!preview && preview.revision === revision && preview.certified_current;
