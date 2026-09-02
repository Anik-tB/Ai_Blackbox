"use client";

import React, { useState } from "react";
import { CausalGraphData, CausalNode } from "../lib/types";
import { AlertCircle, ArrowDown, CheckCircle2, Info, Zap } from "lucide-react";

interface Props {
  data: CausalGraphData | null;
}

export default function CausalGraph({ data }: Props) {
  const [selectedNode, setSelectedNode] = useState<CausalNode | null>(null);

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="p-8 text-center bg-white border border-slate-200 rounded-2xl text-slate-500 shadow-xs">
        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-slate-400" />
        <p className="text-sm font-medium">No causal relationships inferred yet.</p>
      </div>
    );
  }

  const getNodeIcon = (type: string) => {
    switch (type) {
      case "anomaly":
        return <Zap className="w-4 h-4 text-amber-600" />;
      case "hypothesis":
        return <Info className="w-4 h-4 text-blue-600" />;
      default:
        return <CheckCircle2 className="w-4 h-4 text-emerald-600" />;
    }
  };

  const getNodeBorder = (type: string, isSelected: boolean) => {
    if (isSelected) return "border-emerald-600 ring-2 ring-emerald-500/20 bg-emerald-50/30";
    switch (type) {
      case "anomaly":
        return "border-amber-300 hover:border-amber-500 bg-amber-50/30";
      case "hypothesis":
        return "border-blue-300 hover:border-blue-500 bg-blue-50/30";
      default:
        return "border-emerald-200 hover:border-emerald-500 bg-white";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold tracking-wider text-slate-500 uppercase">
          Reconstructed Causal Chain
        </h3>
        <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
          {data.nodes.length} nodes · {data.edges.length} transitions
        </span>
      </div>

      <div className="relative p-8 bg-white border border-slate-200 rounded-2xl shadow-xs overflow-x-auto">
        <div className="flex flex-col items-center space-y-4 min-w-[500px]">
          {data.nodes.map((node, index) => {
            const edge = data.edges.find((e) => e.to === node.id);
            const isSelected = selectedNode?.id === node.id;

            return (
              <React.Fragment key={node.id}>
                {/* Edge transition pill & arrow */}
                {edge && (
                  <div className="flex flex-col items-center py-1 group cursor-default">
                    <div className="flex items-center space-x-2 px-3 py-1 bg-emerald-50/80 border border-emerald-200 rounded-full text-[11px] font-medium text-emerald-800 shadow-2xs">
                      <span>{edge.reason || "caused"}</span>
                      {edge.confidence && (
                        <span className="px-1.5 py-0.2 bg-emerald-600 text-white font-mono text-[10px] font-bold rounded">
                          {Math.round(edge.confidence * 100)}%
                        </span>
                      )}
                    </div>
                    <ArrowDown className="w-4 h-4 text-emerald-600 my-1 animate-pulse" />
                  </div>
                )}

                {/* Node card */}
                <div
                  onClick={() => setSelectedNode(node)}
                  className={`w-full max-w-xl p-4 rounded-xl border shadow-xs transition-all duration-200 cursor-pointer ${getNodeBorder(
                    node.type,
                    isSelected
                  )}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
                        {getNodeIcon(node.type)}
                      </div>
                      <div>
                        <p className="text-sm font-bold text-slate-900">{node.label}</p>
                        <p className="text-xs text-slate-500 capitalize font-medium">Type: {node.type}</p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                      #{index + 1}
                    </span>
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
