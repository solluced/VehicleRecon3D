/** Interaction constraint only; projection and reconstruction stay in Python. */
export function constrainWorldMove(
  before: number[],
  proposed: number[],
  mode: string,
): number[] {
  if (
    !["X", "Y", "Z", "XY", "XZ", "YZ"].includes(mode) ||
    before.length !== 3 ||
    proposed.length !== 3 ||
    ![...before, ...proposed].every(Number.isFinite)
  )
    throw Error("Finite XYZ and explicit axis/plane constraint required");
  return proposed.map((v, i) => (mode.includes("XYZ"[i]) ? v : before[i]));
}
