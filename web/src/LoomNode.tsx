import { useContext } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import type { LoomNodeData } from "./graph";
import { ConfigContext, ENUM_OPTIONS } from "./configContext";

const KIND_COLOR: Record<string, string> = {
  io: "#2563eb", // blue — touches the outside world
  model: "#9333ea", // purple — the single model node
  deterministic: "#334155", // slate — pure code
};

// A single editable config field, typed from its current value.
function Field({
  keyName,
  value,
  onChange,
}: {
  keyName: string;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const options = ENUM_OPTIONS[keyName];
  let control;
  if (typeof value === "boolean") {
    control = (
      <input
        className="nodrag"
        type="checkbox"
        checked={value}
        onChange={(e) => onChange(e.target.checked)}
      />
    );
  } else if (options) {
    control = (
      <select className="nodrag" value={String(value)} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o} value={o}>
            {o === "" ? "(none)" : o}
          </option>
        ))}
      </select>
    );
  } else if (typeof value === "number") {
    control = (
      <input
        className="nodrag"
        type="number"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
      />
    );
  } else {
    control = (
      <input
        className="nodrag"
        type="text"
        value={String(value)}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  return (
    <label className="loom-field">
      <span>{keyName}</span>
      {control}
    </label>
  );
}

export function LoomNode({ data }: NodeProps<Node<LoomNodeData>>) {
  const { loom } = data;
  const { configs, setConfig } = useContext(ConfigContext);
  const color = KIND_COLOR[loom.kind] ?? "#334155";
  const conf = configs[loom.id] ?? {};
  const keys = Object.keys(conf);

  return (
    <div className="loom-node" style={{ borderColor: color }}>
      <Handle type="target" position={Position.Left} />
      <div className="loom-node__head" style={{ background: color }}>
        <span className="loom-node__title">{loom.id}</span>
        <span className="loom-node__kind">{loom.kind}</span>
      </div>
      <div className="loom-node__intent">{loom.intent}</div>
      {keys.length > 0 && (
        <div className="loom-node__config">
          {keys.map((k) => (
            <Field key={k} keyName={k} value={conf[k]} onChange={(v) => setConfig(loom.id, k, v)} />
          ))}
        </div>
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
