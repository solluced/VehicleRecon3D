import { describe, it, expect } from "vitest";
import { constrainWorldMove } from "./world-tools";
describe("world interaction safety", () => {
  for (const mode of ["X", "Y", "Z", "XY", "XZ", "YZ"])
    it("locks unselected coordinates in " + mode, () => {
      const before = [1, 2, 3],
        proposed = [4, 5, 6],
        result = constrainWorldMove(before, proposed, mode);
      for (let i = 0; i < 3; i++)
        expect(result[i]).toBe(
          mode.includes("XYZ"[i]) ? proposed[i] : before[i],
        );
      expect(before).toEqual([1, 2, 3]);
    });
  it("refuses unconstrained or nonfinite gestures", () => {
    expect(() => constrainWorldMove([0, 0, 0], [1, 1, 1], "XYZ")).toThrow();
    expect(() => constrainWorldMove([0, 0, 0], [NaN, 1, 1], "X")).toThrow();
  });
});
