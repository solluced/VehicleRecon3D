// @vitest-environment jsdom
import { afterEach, it, expect, vi } from "vitest";
import { render, fireEvent, screen, cleanup } from "@testing-library/react";
import { RolePicker, SchemaField, Properties } from "./Forms";
import type { Observation } from "./types";
import type { EditorClient } from "./api";
afterEach(cleanup);
it("preserves unedited provenance metadata during a property edit", () => {
  const commands = vi.fn().mockResolvedValue(true);
  const observation: Observation = {
    id: "one",
    kind: "point",
    view: "side",
    semantic_role: "roof",
    pixel: [10, 20],
    reference_id: "multiview",
    source_sha256: "a".repeat(64),
    crop_id: "b".repeat(64),
    revision: 1,
    uncertainty_px: 1,
    visibility: "observed",
    measured: true,
    provenance: {
      type: "measured",
      method: "manual",
      confidence: 0.8,
      provider: "human",
      author: "Analyst",
    },
  };
  render(
    <Properties
      observation={observation}
      selection={{ entity: "one" }}
      client={{ commands } as unknown as EditorClient}
      roles={["roof"]}
      onRoleChanged={() => {}}
      canEdit
    />,
  );
  fireEvent.change(screen.getByLabelText("Uncertainty (px)"), {
    target: { value: "2" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Apply properties" }));
  expect(commands.mock.calls[0][0][0].values.provenance).toMatchObject({
    confidence: 0.8,
    provider: "human",
    author: "Analyst",
  });
});
it("filters actual profile roles and commits selection", () => {
  const changed = vi.fn();
  render(
    <RolePicker
      roles={["roof", "hood", "wheel_arch"]}
      value="roof"
      onChange={changed}
    />,
  );
  fireEvent.change(screen.getByLabelText("Find semantic role"), {
    target: { value: "hood" },
  });
  expect(screen.queryByRole("option", { name: "wheel_arch" })).toBeNull();
  fireEvent.change(screen.getByLabelText("Semantic role"), {
    target: { value: "hood" },
  });
  expect(changed).toHaveBeenCalledWith("hood");
});
it("keeps nullable physical measurements unknown when cleared", () => {
  const changed = vi.fn();
  render(
    <SchemaField
      label="Length"
      schema={{ type: ["number", "null"] }}
      value={4.8}
      onChange={changed}
    />,
  );
  fireEvent.change(screen.getByLabelText("Length"), { target: { value: "" } });
  expect(changed).toHaveBeenCalledWith(null);
});
it("generates enum and boolean controls from schema", () => {
  const changed = vi.fn();
  render(
    <>
      <SchemaField
        label="State"
        schema={{ enum: ["DRAFT", "READY"] }}
        value="DRAFT"
        onChange={changed}
      />
      <SchemaField
        label="Measured"
        schema={{ type: "boolean" }}
        value={false}
        onChange={changed}
      />
    </>,
  );
  fireEvent.change(screen.getByLabelText("State"), {
    target: { value: "READY" },
  });
  expect(changed).toHaveBeenCalledWith("READY");
  fireEvent.click(screen.getByLabelText("Measured"));
  expect(changed).toHaveBeenCalledWith(true);
});
