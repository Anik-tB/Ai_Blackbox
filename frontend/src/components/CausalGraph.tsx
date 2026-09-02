"use client";

import React, { useState } from "react";
import { CausalGraphData, CausalNode } from "../lib/types";
import { AlertCircle, ArrowDown, CheckCircle2, GitCommit, Info, Zap } from "lucide-react";

interface Props {
  data: CausalGraphData | null;
}

export default function CausalGraph({ data }: Props) {
  const [selectedNode, setSelectedNode] = useState<CausalNode | null>(null);

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-900/50 border border-slate-800 rounded-xl text-slate-400">
        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-slate-500" />
        <p className="text-sm">No causal relationships inferred yet.</p>
      </div>
    );
  }

  const getNodeIcon = (type: string) => {
    switch (type) {
      case "anomaly":
        return <Zap className="w-4 h-4 text-amber-400" />;
      case "hypothesis":
        return <Info className="w-4 h-4 text-blue-400" />;
      default:
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
    }
  };

  const getNodeBorder = (type: string, isSelected: boolean) => {
    if (isSelected) return "border-blue-500 ring-2 ring-blue-500/30 bg-slate-800";
    switch (type) {
      case "anomaly":
        return "border-amber-500/40 hover:border-amber-400 bg-slate-900/80";
      case "hypothesis":
        return "border-blue-500/40 hover:border-blue-400 bg-slate-900/80";
      default:
        return "border-emerald-500/40 hover:border-emerald-400 bg-slate-900/80";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
          Reconstructed Causal Chain
        </h3>
        <span className="text-xs text-slate-500">
          {data.nodes.length} nodes · {data.edges.length} causal transitions
        </span>
      </div>

      <div className="relative p-6 bg-slate-950/80 border border-slate-800/80 rounded-2xl overflow-x-auto">
        <div className="flex flex-col items-center space-y-4 min-w-[500px]">
          {data.nodes.map((node, index) => {
            const edge = data.edges.find((e) => e.to === node.id);
            const isSelected = selectedNode?.id === node.id;

            return (
              <React.Fragment key={node.id}>
                {/* Edge transition indicator */}
                {edge && (
                  <div className="flex flex-col items-center py-1 group cursor-default">
                    <div className="flex items-center space-x-2 px-3 py-1 bg-slate-900 border border-slate-800 rounded-full text-[11px] text-slate-400 shadow-sm">
                      <span>{edge.reason || "caused"}</span>
                      {edge.confidence && (
                        <span className="px-1.5 py-0.2 bg-blue-500/10 text-blue-400 font-mono text-[10px] rounded border border-blue-500/20">
                          {Math.round(edge.confidence * 100)}%
                        </span>
                      )}
                    </div>
                    <ArrowDown className="w-4 h-4 text-slate-600 my-1 animate-pulse" />
                  </div>
                )}

                {/* Node card */}
                <div
                  onClick={() => setSelectedNode(node)}
                  className={`w-full max-w-xl p-4 rounded-xl border transition-all duration-200 cursor-pointer ${getNodeBorder(
                    node.type,
                    isSelected
                  )}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-slate-950 rounded-lg border border-slate-800">
                        {getNodeIcon(node.type)}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-slate-200">{node.label}</p>
                        <p className="text-xs text-slate-500 capitalize">Type: {node.type}</p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500">#{index + 1}</span>
                  </div>
                </div>
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
