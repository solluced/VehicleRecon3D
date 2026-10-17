import type { AuthoringCommand, Snapshot } from "./types";
import { applySnapshotDelta, type SnapshotDelta } from "./snapshot-delta";
export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }
}
export class API {
  csrf = "";
  tab = sessionStorage.getItem("vr-tab") || crypto.randomUUID();
  constructor() {
    sessionStorage.setItem("vr-tab", this.tab);
  }
  async call<T>(path: string, options: RequestInit = {}): Promise<T> {
    const r = await fetch("/api/v1" + path, {
      ...options,
      headers: {
        "X-Studio-Tab": this.tab,
        "X-CSRF-Token": this.csrf,
        ...options.headers,
      },
    });
    const data = await r.json();
    if (!r.ok)
      throw new APIError(
        r.status,
        data.message || "Request could not complete",
        data,
      );
    return data;
  }
  async bootstrap() {
    const fragment = new URLSearchParams(location.hash.slice(1));
    const secret = fragment.get("bootstrap");
    history.replaceState(null, "", location.pathname + location.search);
    const data = await this.call<{ csrf: string }>(
      secret ? "/session/bootstrap" : "/session",
      secret
        ? {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ secret }),
          }
        : {},
    );
    this.csrf = data.csrf;
  }
  post<T>(path: string, body: Record<string, unknown>) {
    return this.call<T>(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "If-Match": String(body.expected_revision || ""),
        "Idempotency-Key": crypto.randomUUID().replaceAll("-", ""),
      },
      body: JSON.stringify(body),
    });
  }
}
export type EditorState = {
  snapshot: Snapshot | null;
  busy: boolean;
  conflict: boolean;
  error: APIError | null;
  lease: string;
};
export class EditorClient {
  state: EditorState = {
    snapshot: null,
    busy: false,
    conflict: false,
    error: null,
    lease: "",
  };
  listeners = new Set<() => void>();
  constructor(public api: API) {}
  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };
  getSnapshot = () => this.state;
  set(patch: Partial<EditorState>) {
    this.state = { ...this.state, ...patch };
    this.listeners.forEach((fn) => fn());
  }
  async open(id: string) {
    let s: Snapshot;
    try {
      s = await this.api.call<Snapshot>("/projects/" + id);
    } catch (e) {
      this.set({ error: e as APIError });
      return false;
    }
    this.set({ snapshot: s, error: null, conflict: false, lease: "" });
    if (!s.read_only) {
      try {
        const l = await this.api.post<{ lease_id: string }>(
          "/projects/" + id + "/leases",
          { expected_revision: s.revision },
        );
        this.set({ lease: l.lease_id, snapshot: { ...s, editable: true } });
      } catch (e) {
        this.set({ error: e as APIError });
      }
    }
    return true;
  }
  get writable() {
    return (
      !!this.state.snapshot &&
      !this.state.snapshot.read_only &&
      !!this.state.lease &&
      !this.state.conflict &&
      !this.state.busy
    );
  }
  async run(
    operation: string,
    fields: Record<string, unknown> = {},
  ): Promise<boolean> {
    if (!this.writable) return false;
    const s = this.state.snapshot!;
    this.set({ busy: true, error: null });
    try {
      const result = await this.api.post<{
        snapshot?: Snapshot;
        snapshot_delta?: SnapshotDelta;
      }>("/projects/" + s.id + "/" + operation, {
        ...fields,
        expected_revision: s.revision,
        lease_id: this.state.lease,
        response_format: "delta",
      });
      let snapshot: Snapshot;
      try {
        snapshot =
          result.snapshot || applySnapshotDelta(s, result.snapshot_delta!);
      } catch {
        throw new APIError(
          409,
          "Incremental response is out of date. Reload canonical state to continue.",
        );
      }
      this.set({ snapshot, busy: false });
      return true;
    } catch (error) {
      const e = error as APIError;
      this.set({
        busy: false,
        error: e,
        conflict: e.status === 409 || e.status === 423,
      });
      // A failed drag/property commit displays canonical state; it is never saved locally.
      if (e.status !== 409 && e.status !== 423) {
        try {
          this.set({
            snapshot: await this.api.call<Snapshot>("/projects/" + s.id),
          });
        } catch {}
      }
      return false;
    }
  }
  commands(commands: AuthoringCommand[]) {
    return this.run("transactions", { commands });
  }
  async preferences(preferences: unknown) {
    const s = this.state.snapshot;
    if (!s || !this.state.lease || this.state.conflict || s.read_only) return;
    try {
      await this.api.post("/projects/" + s.id + "/preferences", {
        preferences,
        expected_revision: s.revision,
        lease_id: this.state.lease,
        response_format: "ack",
      });
    } catch (error) {
      const e = error as APIError;
      if (e.status === 409) void this.reconcile();
    }
  }
  external(revision: string) {
    if (
      !this.state.busy &&
      this.state.snapshot &&
      revision !== this.state.snapshot.revision
    )
      this.set({
        conflict: true,
        error: new APIError(
          409,
          "Project changed outside this editor. Reload to continue; your pending write was stopped.",
        ),
      });
  }
  async reconcile() {
    const start = this.state.snapshot;
    if (!start || this.state.busy) return;
    try {
      const r = await this.api.call<{ revision: string }>(
        "/projects/" + start.id + "/revision",
      );
      if (!this.state.busy && this.state.snapshot?.revision === start.revision)
        this.external(r.revision);
    } catch {}
  }
  async renew() {
    const s = this.state.snapshot;
    if (!s || !this.state.lease || this.state.busy || this.state.conflict)
      return;
    try {
      await this.api.post("/projects/" + s.id + "/leases", {
        expected_revision: s.revision,
      });
    } catch (error) {
      const e = error as APIError;
      if (e.status === 409) await this.reconcile();
      else if (e.status === 423) this.set({ conflict: true, error: e });
    }
  }
  async reload() {
    const id = this.state.snapshot!.id;
    if (!(await this.open(id))) return;
    if (this.writable) await this.run("reload");
  }
  async import(file: File, replacementView?: string) {
    if (!this.writable) return;
    const s = this.state.snapshot!;
    this.set({ busy: true, error: null });
    try {
      const result = await this.api.call<{ snapshot: Snapshot }>(
        "/projects/" + s.id + "/reference-imports",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/octet-stream",
            "If-Match": s.revision,
            "X-Expected-Revision": s.revision,
            "X-Editor-Lease": this.state.lease,
            ...(replacementView
              ? {
                  "X-Replacement-View": replacementView,
                  "X-Confirm-Replacement": "true",
                }
              : {}),
            "Idempotency-Key": crypto.randomUUID().replaceAll("-", ""),
          },
          body: file,
        },
      );
      this.set({ snapshot: result.snapshot, busy: false });
    } catch (e) {
      const error = e as APIError;
      this.set({
        busy: false,
        error,
        conflict: error.status === 409 || error.status === 423,
      });
    }
  }
}
