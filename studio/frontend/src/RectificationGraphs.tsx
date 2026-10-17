import { useState, useRef } from "react";
import type { Candidate, Sample } from "./reconciliation-types";
export const number = (v: number | null | undefined, digits = 3) =>
  v == null ? "unavailable" : v.toFixed(digits);
type Kind = "mapping" | "correction" | "derivative";
export function RectificationGraphs({ candidate }: { candidate: Candidate }) {
  const [units, setUnits] = useState<
    "correction" | "correction_px" | "equivalent_mm"
  >("correction_px");
  const samples = candidate.report.samples || [];
  if (!samples.length)
    return (
      <p role="status">
        Mapping unavailable: {candidate.report.reasons.join("; ")}
      </p>
    );
  return (
    <section className="rect-graphs" aria-label="Core mapping inspection">
      <label>
        Correction units
        <select
          aria-label="Correction units"
          value={units}
          onChange={(e) => setUnits(e.target.value as typeof units)}
        >
          <option value="correction">normalized</option>
          <option value="correction_px">pixels</option>
          <option value="equivalent_mm">mm equivalent source correction</option>
        </select>
      </label>
      {(["mapping", "correction", "derivative"] as Kind[]).map((kind) => (
        <Graph
          key={kind + candidate.id}
          candidate={candidate}
          samples={samples}
          kind={kind}
          units={units}
        />
      ))}
      <p>
        Core analytic extrema: minimum{" "}
        {number(candidate.report.derivative_extrema?.minimum.derivative, 9)} at
        x=
        {number(
          candidate.report.derivative_extrema?.minimum.source_normalized,
          9,
        )}
        ; maximum{" "}
        {number(candidate.report.derivative_extrema?.maximum.derivative, 9)} at
        x=
        {number(
          candidate.report.derivative_extrema?.maximum.source_normalized,
          9,
        )}
        . Hover values are exact core samples; curves connect those samples.
      </p>
    </section>
  );
}
function Graph({
  candidate,
  samples,
  kind,
  units,
}: {
  candidate: Candidate;
  samples: Sample[];
  kind: Kind;
  units: "correction" | "correction_px" | "equivalent_mm";
}) {
  const lo = samples[0].x,
    hi = samples.at(-1)!.x;
  const [domain, setDomain] = useState([lo, hi]),
    [hover, setHover] = useState<Sample | null>(null);
  const drag = useRef<{ x: number; domain: number[] } | null>(null);
  const field =
    kind === "mapping" ? "y" : kind === "derivative" ? "derivative" : units;
  const values = samples
    .map((s) => s[field])
    .filter((x): x is number => x != null);
  const limits = candidate.report.allowed_scale || [0.9, 1.1];
  const yl = Math.min(...values, kind === "derivative" ? limits[0] : 0),
    yh = Math.max(
      ...values,
      kind === "derivative" ? limits[1] : kind === "mapping" ? hi : 0,
    ),
    pad = Math.max(0.001, (yh - yl) * 0.12);
  const X = (x: number) =>
      50 + (680 * (x - domain[0])) / (domain[1] - domain[0]),
    Y = (y: number) => 205 - (170 * (y - yl + pad)) / (yh - yl + 2 * pad);
  const title =
    kind === "mapping"
      ? "Mapping graph"
      : kind === "derivative"
        ? "Derivative / local-scale graph"
        : "Correction graph";
  const unit =
    kind === "mapping"
      ? "normalized target"
      : kind === "derivative"
        ? "scale relative to affine baseline"
        : units === "correction_px"
          ? "px"
          : units === "correction"
            ? "normalized"
            : "mm equivalent source correction";
  function at(e: React.PointerEvent<SVGSVGElement>) {
    const b = e.currentTarget.getBoundingClientRect();
    return (
      domain[0] +
      ((((e.clientX - b.left) * 760) / b.width - 50) / 680) *
        (domain[1] - domain[0])
    );
  }
  function zoom(factor: number) {
    const mid = (domain[0] + domain[1]) / 2,
      half = ((domain[1] - domain[0]) * factor) / 2;
    setDomain([mid - half, mid + half]);
  }
  const support = candidate.report.extrapolation?.fitted_support || [lo, hi];
  return (
    <figure className="rect-graph">
      <figcaption>
        {title} · {unit}
      </figcaption>
      <div>
        <button aria-label={`Zoom in ${kind}`} onClick={() => zoom(0.7)}>
          Zoom +
        </button>
        <button aria-label={`Zoom out ${kind}`} onClick={() => zoom(1.4)}>
          Zoom −
        </button>
        <button onClick={() => setDomain([lo, hi])}>Reset {kind}</button>
        <span>Drag to pan · x normalized source</span>
      </div>
      <svg
        aria-label={title}
        role="img"
        viewBox="0 0 760 245"
        onPointerDown={(e) => {
          drag.current = { x: e.clientX, domain: [...domain] };
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
        onPointerMove={(e) => {
          const x = at(e);
          if (drag.current) {
            const d = drag.current,
              dx =
                (((e.clientX - d.x) * 760) /
                  e.currentTarget.getBoundingClientRect().width /
                  680) *
                (d.domain[1] - d.domain[0]);
            setDomain([d.domain[0] - dx, d.domain[1] - dx]);
          }
          setHover(
            samples.reduce((a, b) =>
              Math.abs(a.x - x) < Math.abs(b.x - x) ? a : b,
            ),
          );
        }}
      >
        <defs>
          <clipPath id={`clip-${kind}`}>
            <rect x="50" y="20" width="680" height="190" />
          </clipPath>
        </defs>
        <g clipPath={`url(#clip-${kind})`}>
          {[
            [lo, support[0]],
            [support[1], hi],
          ].map(([a, b], i) => (
            <rect
              key={i}
              x={X(a)}
              width={Math.max(0, X(b) - X(a))}
              y="20"
              height="190"
              fill="#694b25"
              opacity=".5"
            />
          ))}
          {kind === "derivative" && (
            <>
              <rect
                x="50"
                width="680"
                y={Y(limits[1])}
                height={Y(limits[0]) - Y(limits[1])}
                fill="#245b49"
                opacity=".5"
              />
              <path
                d={`M50 ${Y(limits[0])} H730 M50 ${Y(limits[1])} H730`}
                stroke="#8cdbc0"
                strokeDasharray="6 4"
              />
            </>
          )}
          <path
            d={
              kind === "mapping"
                ? `M${X(domain[0])} ${Y(domain[0])} L${X(domain[1])} ${Y(domain[1])}`
                : `M50 ${Y(kind === "derivative" ? 1 : 0)} H730`
            }
            stroke="#90a3af"
            strokeDasharray="5 5"
          />
          <polyline
            fill="none"
            stroke="#6fdfd4"
            strokeWidth="2.5"
            points={samples
              .filter((s) => s[field] != null)
              .map((s) => `${X(s.x)},${Y(s[field]!)}`)
              .join(" ")}
          />
          {kind === "mapping" &&
            candidate.report.anchors.map((a, i) => (
              <g key={a.id || i}>
                {a.role === "HELD_OUT" ? (
                  <path
                    d={`M${X(a.image) - 4} ${Y(a.world_normalized) - 4} l8 8 m-8 0 l8 -8`}
                    stroke="#ffc576"
                  />
                ) : (
                  <circle
                    cx={X(a.image)}
                    cy={Y(a.world_normalized)}
                    r={a.locked ? 5 : 3.5}
                    fill={a.locked ? "#fff" : "#6fdfd4"}
                  />
                )}
              </g>
            ))}
          {hover && (
            <line
              x1={X(hover.x)}
              x2={X(hover.x)}
              y1="20"
              y2="210"
              stroke="#fff"
              opacity=".45"
            />
          )}
        </g>
        <path d="M50 20 V210 H730" fill="none" stroke="#68818c" />
        <text x="50" y="235">
          {number(domain[0])}
        </text>
        <text x="660" y="235">
          {number(domain[1])}
        </text>
        <text x="0" y="30">
          {number(yh)}
        </text>
        <text x="0" y="205">
          {number(yl)}
        </text>
      </svg>
      <output>
        {hover
          ? `x ${number(hover.x, 9)} · ${number(hover[field], 9)} ${unit} · source ${number(hover.source_px)} px · target ${number(hover.target_px)} px${hover.extrapolated ? " · EXTRAPOLATED" : ""}`
          : "Hover for exact core samples · FIT ● / HELD-OUT × / LOCKED ○"}
      </output>
      {kind === "derivative" && (
        <p>
          Allowed {limits.map((v) => number(v, 6)).join(" – ")}. Actual{" "}
          {candidate.report.local_scale_range
            ?.map((v) => number(v, 9))
            .join(" – ")}{" "}
          ·{" "}
          {candidate.report.reasons.includes("OUTSIDE SCALE LIMIT")
            ? "FAIL: OUTSIDE SCALE LIMIT"
            : "Scale band PASS"}
        </p>
      )}
    </figure>
  );
}
