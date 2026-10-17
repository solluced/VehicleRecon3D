// @vitest-environment jsdom
import { afterEach, it, expect, vi } from "vitest";
import { render, fireEvent, screen, cleanup } from "@testing-library/react";
import { RolePicker, SchemaField } from "./Forms";
afterEach(cleanup);
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
