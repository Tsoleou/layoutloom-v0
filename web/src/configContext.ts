import { createContext } from "react";

// Per-node editable config, keyed by Loom node id -> { config key: value }.
// LoomNode reads/writes its own slice; App owns the state and posts it on render.
export interface ConfigCtx {
  configs: Record<string, Record<string, unknown>>;
  setConfig: (nodeId: string, key: string, value: unknown) => void;
}

export const ConfigContext = createContext<ConfigCtx>({
  configs: {},
  setConfig: () => {},
});

// Config keys that should render as a dropdown instead of a free text field.
export const ENUM_OPTIONS: Record<string, string[]> = {
  layout: ["random", "text-left", "text-right", "text-top"],
  reasoning_effort: ["", "low", "medium", "high"],
  format: ["png", "jpeg"],
};
