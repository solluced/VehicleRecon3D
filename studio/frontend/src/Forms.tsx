import { useEffect, useState } from "react";
import { controls } from "./geometry";
import type {
  AuthoringCommand,
  Measurement,
  Observation,
  Schema,
  Selection,
  Snapshot,
  View,
} from "./types";
import type { EditorClient } from "./api";
export function RolePicker({
  roles,
  value,
  onChange,
  disabled = false,
}: {
  roles: string[];
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  const [search, setSearch] = useState("");
  return (
    <div className="role-picker">
      <label>
        Find semantic role
        <input
          aria-label="Find semantic role"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search core roles…"
          disabled={disabled}
        />
      </label>
      <label>
        Semantic role
        <select
          aria-label="Semantic role"
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
        >
          {roles
            .filter(
              (r) =>
                r === value || r.toLowerCase().includes(search.toLowerCase()),
            )
            .map((r) => (
              <option key={r}>{r}</option>
            ))}
        </select>
      </label>
    </div>
  );
}
export function SchemaField({
  label,
  schema,
  value,
  onChange,
  disabled = false,
}: {
  label: string;
  schema: Schema;
  value: unknown;
  onChange: (v: unknown) => void;
  disabled?: boolean;
}) {
  const kinds = Array.isArray(schema.type) ? schema.type : [schema.type];
  const nullable = kinds.includes("null"),
    numeric = kinds.includes("number") || kinds.includes("integer");
  const id = "field-" + label.replaceAll(" ", "_");
  return (
    <label htmlFor={id}>
      {label}
      {schema.enum ? (
        <select
          id={id}
          aria-label={label}
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        >
          {schema.enum.map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
      ) : kinds.includes("boolean") ? (
        <input
          id={id}
          aria-label={label}
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
        />
      ) : (
        <input
          id={id}
          aria-label={label}
          type={numeric ? "number" : "text"}
          step={numeric ? "any" : undefined}
          min={schema.minimum ?? schema.exclusiveMinimum}
          max={schema.maximum}
          value={value == null ? "" : String(value)}
          placeholder={nullable ? "Unknown" : ""}
          disabled={disabled}
          onChange={(e) =>
            onChange(
              numeric
                ? e.target.value === "" && nullable
                  ? null
                  : Number(e.target.value)
                : e.target.value,
            )
          }
        />
      )}
    </label>
  );
}
export function Properties({
  observation: o,
  selection,
  client,
  roles,
  onRoleChanged,
  canEdit,
}: {
  observation: Observation;
  selection: Selection;
  client: EditorClient;
  roles: string[];
  onRoleChanged: (r: string) => void;
  canEdit: boolean;
}) {
  const [values, setValues] = useState({
    role: o.semantic_role,
    view: o.view,
    uncertainty: o.uncertainty_px,
    visibility: o.visibility,
    measured: o.measured,
    provenance: o.provenance.type,
    method: o.provenance.method,
    citation: o.provenance.citation || "",
  });
  const control =
    controls(o).find((p) => p.id === selection?.point) || controls(o)[0];
  const [pixel, setPixel] = useState(control?.pixel || [0, 0]);
  useEffect(() => {
    setValues({
      role: o.semantic_role,
      view: o.view,
      uncertainty: o.uncertainty_px,
      visibility: o.visibility,
      measured: o.measured,
      provenance: o.provenance.type,
      method: o.provenance.method,
      citation: o.provenance.citation || "",
    });
    setPixel(control?.pixel || [0, 0]);
  }, [o, selection?.point]);
  const disabled = !canEdit;
  function patch(p: Partial<typeof values>) {
    setValues((v) => ({ ...v, ...p }));
  }
  async function save() {
    const commands: AuthoringCommand[] = [
      {
        type: "SetObservationProperties",
        observation_id: o.id,
        values: {
          semantic_role: values.role,
          view: values.view,
          uncertainty_px: values.uncertainty,
          visibility: values.visibility,
          measured: values.visibility === "inferred" ? false : values.measured,
          provenance: {
            ...o.provenance,
            type: values.provenance,
            method: values.method,
            citation: values.citation || undefined,
          },
        },
      },
    ];
    if (control && pixel.some((v, i) => v !== control.pixel[i]))
      commands.push(
        "points" in o
          ? {
              type: "MoveSplinePoint",
              target: "observation",
              entity_id: o.id,
              point_id: control.id!,
              point: pixel,
            }
          : { type: "MoveObservation", observation_id: o.id, pixel },
      );
    if (await client.commands(commands)) onRoleChanged(values.role);
  }
  return (
    <div className="inspector-content">
      <div className="section-caption">{o.kind.toUpperCase()} PROPERTIES</div>
      <label>
        Stable ID
        <input
          aria-label="Stable ID"
          value={o.id}
          readOnly
          className="readonly"
        />
      </label>
      <RolePicker
        roles={roles}
        value={values.role}
        onChange={(role) => patch({ role })}
        disabled={disabled}
      />
      <SchemaField
        label="Observation view"
        schema={{ enum: ["front", "side", "rear", "top"] }}
        value={values.view}
        onChange={(v) => patch({ view: v as View })}
        disabled={disabled}
      />
      {control && (
        <div className="pair">
          <SchemaField
            label="Pixel X"
            schema={{ type: "number", minimum: 0 }}
            value={pixel[0]}
            onChange={(v) => setPixel([Number(v), pixel[1]])}
            disabled={disabled}
          />
          <SchemaField
            label="Pixel Y"
            schema={{ type: "number", minimum: 0 }}
            value={pixel[1]}
            onChange={(v) => setPixel([pixel[0], Number(v)])}
            disabled={disabled}
          />
        </div>
      )}
      {selection?.point && (
        <small className="mono">Knot {selection.point}</small>
      )}
      <SchemaField
        label="Uncertainty (px)"
        schema={{ type: "number", minimum: 0 }}
        value={values.uncertainty}
        onChange={(v) => patch({ uncertainty: Number(v) })}
        disabled={disabled}
      />
      <SchemaField
        label="Visibility"
        schema={{ enum: ["observed", "inferred", "occluded", "unobserved"] }}
        value={values.visibility}
        onChange={(v) => patch({ visibility: v as typeof values.visibility })}
        disabled={disabled}
      />
      <SchemaField
        label="Measured"
        schema={{ type: "boolean" }}
        value={values.measured}
        onChange={(v) => patch({ measured: Boolean(v) })}
        disabled={disabled || values.visibility === "inferred"}
      />
      <SchemaField
        label="Provenance"
        schema={{ enum: ["official", "measured", "inferred", "approximate"] }}
        value={values.provenance}
        onChange={(v) => patch({ provenance: v as typeof values.provenance })}
        disabled={disabled}
      />
      <SchemaField
        label="Method"
        schema={{ type: "string" }}
        value={values.method}
        onChange={(v) => patch({ method: String(v) })}
        disabled={disabled}
      />
      <SchemaField
        label="Source citation"
        schema={{ type: "string" }}
        value={values.citation}
        onChange={(v) => patch({ citation: String(v) })}
        disabled={disabled}
      />
      <label>
        Source identity
        <input
          aria-label="Source identity"
          readOnly
          value={o.source_sha256}
          className="readonly"
        />
      </label>
      <small>Original source pixels · revision {o.revision}</small>
      <button
        className="primary"
        disabled={disabled}
        onClick={() => void save()}
      >
        Apply properties
      </button>
    </div>
  );
}
export function Settings({
  snapshot: s,
  schemas,
  profiles,
  client,
  disabled,
}: {
  snapshot: Snapshot;
  schemas: Record<string, Schema>;
  profiles: string[];
  client: EditorClient;
  disabled: boolean;
}) {
  const [name, setName] = useState(s.project.asset_name),
    [profile, setProfile] = useState(s.project.vehicle_profile),
    [state, setState] = useState(s.project.authoring_state || "DRAFT");
  const [dimensions, setDimensions] = useState(s.project.dimensions),
    [provenance, setProvenance] =
      useState<Measurement["provenance"]["type"]>("approximate"),
    [method, setMethod] = useState("Manual dimension entry"),
    [citation, setCitation] = useState(""),
    [uncertainty, setUncertainty] = useState<number | undefined>();
  useEffect(() => {
    setName(s.project.asset_name);
    setProfile(s.project.vehicle_profile);
    setState(s.project.authoring_state || "DRAFT");
    setDimensions(s.project.dimensions);
  }, [s.revision]);
  const schema = schemas.project_v2 || {},
    fields = schema.properties || {};
  async function save() {
    const commands: AuthoringCommand[] = [];
    if (name !== s.project.asset_name || profile !== s.project.vehicle_profile)
      commands.push({
        type: "SetProjectMetadata",
        values: { asset_name: name, vehicle_profile: profile },
      });
    if (state !== s.project.authoring_state)
      commands.push({
        type: "SetProjectSettings",
        section: "authoring_state",
        value: state,
      });
    for (const key of [
      "length_m",
      "width_m",
      "height_m",
      "wheelbase_m",
    ] as const)
      if (dimensions[key] !== s.project.dimensions[key])
        commands.push({
          type: "SetMeasurement",
          dimension: key,
          measurement: {
            id: "measure_" + key,
            value: dimensions[key] as number | null,
            unit: "m",
            meaning: key,
            provenance: {
              type: provenance,
              method,
              ...(citation ? { citation } : {}),
            },
            ...(uncertainty === undefined ? {} : { uncertainty }),
          },
        });
    if (commands.length) await client.commands(commands);
  }
  return (
    <div className="inspector-content">
      <div className="section-caption">PROJECT SETTINGS</div>
      <label>
        Project ID
        <input readOnly value={s.project.project_id} className="readonly" />
      </label>
      <SchemaField
        label="Asset name"
        schema={fields.asset_name || { type: "string" }}
        value={name}
        onChange={(v) => setName(String(v))}
        disabled={disabled}
      />
      <SchemaField
        label="Vehicle profile"
        schema={{ ...fields.vehicle_profile, enum: profiles }}
        value={profile}
        onChange={(v) => setProfile(String(v))}
        disabled={disabled}
      />
      <SchemaField
        label="Authoring state"
        schema={fields.authoring_state || { enum: ["DRAFT", "READY"] }}
        value={state}
        onChange={(v) => setState(String(v))}
        disabled={disabled}
      />
      <div className="section-caption">KNOWN DIMENSIONS</div>
      <small>Leave blank for unknown. Values are stored in metres.</small>
      {Object.entries(fields.dimensions?.properties || {})
        .filter(([k]) => k.endsWith("_m"))
        .map(([key, field]) => (
          <SchemaField
            key={key}
            label={key.replace("_m", " (m)").replaceAll("_", " ")}
            schema={field}
            value={dimensions[key]}
            onChange={(v) =>
              setDimensions((d) => ({ ...d, [key]: v as number | null }))
            }
            disabled={disabled}
          />
        ))}
      <SchemaField
        label="Dimension provenance"
        schema={{ enum: ["official", "measured", "inferred", "approximate"] }}
        value={provenance}
        onChange={(v) => setProvenance(v as typeof provenance)}
        disabled={disabled}
      />
      <SchemaField
        label="Dimension method"
        schema={{ type: "string" }}
        value={method}
        onChange={(v) => setMethod(String(v))}
        disabled={disabled}
      />
      <SchemaField
        label="Dimension citation"
        schema={{ type: "string" }}
        value={citation}
        onChange={(v) => setCitation(String(v))}
        disabled={disabled}
      />
      <SchemaField
        label="Dimension uncertainty (m)"
        schema={{ type: ["number", "null"], minimum: 0 }}
        value={uncertainty}
        onChange={(v) => setUncertainty(v == null ? undefined : Number(v))}
        disabled={disabled}
      />
      <button
        className="primary"
        onClick={() => void save()}
        disabled={disabled}
      >
        Apply settings
      </button>
      {s.measurements.length > 0 && (
        <details>
          <summary>Saved measurements</summary>
          {s.measurements.map((m) => (
            <p key={m.id}>
              {m.meaning}: {m.value ?? "Unknown"} {m.unit} · {m.provenance.type}
              <br />
              <small>{m.provenance.citation || m.provenance.method}</small>
            </p>
          ))}
        </details>
      )}
    </div>
  );
}
