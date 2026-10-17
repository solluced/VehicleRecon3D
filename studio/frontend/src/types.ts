import type {
  Observation,
  AuthoringCommand,
  Measurement,
} from "../../shared/generated/contracts";
export type { Observation, AuthoringCommand, Measurement };
export type View = "front" | "side" | "rear" | "top";
export type XY = { x: number; y: number };
export type Camera = XY & { scale: number };
export type LayerState = {
  name: string;
  category: "image" | "observations" | "curves" | "datums";
  visible: boolean;
  locked: boolean;
  opacity: number;
};
export type Preferences = {
  active_view?: View;
  reference_id?: string;
  viewport?: Camera;
  layers?: Record<string, LayerState>;
  assignments?: Record<string, string>;
};
export type Schema = {
  type?: string | string[];
  enum?: string[];
  const?: unknown;
  properties?: Record<string, Schema>;
  items?: Schema;
  minimum?: number;
  maximum?: number;
  exclusiveMinimum?: number;
  description?: string;
  required?: string[];
  $defs?: Record<string, Schema>;
  oneOf?: Schema[];
};
export type Reference = {
  id: string;
  role: string;
  size: number[];
  sha256: string;
};
export type Ready = {
  state: string;
  reasons?: string[];
  decision?: string;
  current?: boolean;
};
export type Snapshot = {
  id: string;
  revision: string;
  version: number;
  read_only: boolean;
  editable: boolean;
  project: {
    asset_name: string;
    project_id: string;
    vehicle_profile: string;
    authoring_state?: string;
    dimensions: Record<string, number | string | null>;
    validation?: Record<string, unknown>;
  };
  observations: Observation[];
  references: Reference[];
  roles: string[];
  measurements: Measurement[];
  views: Record<string, { crop_id: Record<string, string> }>;
  readiness: Record<string, Ready | unknown>;
  history: { undo: boolean; redo: boolean };
  preferences: Preferences;
};
export type ProjectEntry = Pick<
  Snapshot,
  "id" | "revision" | "version" | "read_only" | "project" | "readiness"
> & { issues?: string[] };
export type Selection = { entity: string; point?: string } | null;
export const defaults: Record<string, LayerState> = {
  image: {
    name: "Source Image",
    category: "image",
    visible: true,
    locked: true,
    opacity: 1,
  },
  observations: {
    name: "Observations",
    category: "observations",
    visible: true,
    locked: false,
    opacity: 1,
  },
  curves: {
    name: "Source Curves",
    category: "curves",
    visible: true,
    locked: false,
    opacity: 1,
  },
  datums: {
    name: "Landmarks / Datums",
    category: "datums",
    visible: true,
    locked: false,
    opacity: 1,
  },
};
export function category(o: Observation): LayerState["category"] {
  return ["axis", "measurement"].includes(o.semantic_role)
    ? "datums"
    : "points" in o
      ? "curves"
      : "observations";
}
export function layerFor(o: Observation, prefs: Preferences): string {
  return prefs.assignments?.[o.id] ?? category(o);
}
export function editable(o: Observation, prefs: Preferences): boolean {
  const l = prefs.layers?.[layerFor(o, prefs)] ?? defaults[category(o)];
  return l.visible && !l.locked;
}
