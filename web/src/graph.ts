// Turn the Loom Graph contract into React Flow nodes/edges.
//
// The contract carries no positions, so we lay nodes out by longest-path level
// from the source nodes (a simple layered DAG layout): entry/io nodes on the
// left, the model node next, then each downstream deterministic node in its own
// column. Nodes sharing a level stack vertically.
import type { Edge, Node } from "@xyflow/react";
import type { LoomGraph, LoomNode } from "./api";

export interface LoomNodeData extends Record<string, unknown> {
  loom: LoomNode;
}

const COL_W = 260;
const ROW_H = 130;

// Longest-path level: max over predecessors of (level(pred) + 1), sources = 0.
function computeLevels(graph: LoomGraph): Map<string, number> {
  const preds = new Map<string, string[]>();
  graph.nodes.forEach((n) => preds.set(n.id, []));
  graph.edges.forEach((e) => preds.get(e.to)?.push(e.from));

  const level = new Map<string, number>();
  const resolve = (id: string, stack: Set<string>): number => {
    if (level.has(id)) return level.get(id)!;
    if (stack.has(id)) return 0; // contract has no loops; guard anyway
    stack.add(id);
    const parents = preds.get(id) ?? [];
    const lvl = parents.length ? Math.max(...parents.map((p) => resolve(p, stack) + 1)) : 0;
    stack.delete(id);
    level.set(id, lvl);
    return lvl;
  };
  graph.nodes.forEach((n) => resolve(n.id, new Set()));
  return level;
}

export function toFlow(graph: LoomGraph): { nodes: Node<LoomNodeData>[]; edges: Edge[] } {
  const level = computeLevels(graph);

  // Row index within each column, assigned in contract order.
  const rowInCol = new Map<string, number>();
  const colCount = new Map<number, number>();
  graph.nodes.forEach((n) => {
    const lvl = level.get(n.id)!;
    const row = colCount.get(lvl) ?? 0;
    rowInCol.set(n.id, row);
    colCount.set(lvl, row + 1);
  });

  const nodes: Node<LoomNodeData>[] = graph.nodes.map((n) => ({
    id: n.id,
    type: "loom",
    position: { x: level.get(n.id)! * COL_W, y: rowInCol.get(n.id)! * ROW_H },
    data: { loom: n },
  }));

  const edges: Edge[] = graph.edges.map((e, i) => ({
    id: `e${i}`,
    source: e.from,
    target: e.to,
    label: e.from_port === e.to_port ? e.from_port : `${e.from_port}→${e.to_port}`,
    animated: e.from === "LLM Banner Plan",
  }));

  return { nodes, edges };
}
