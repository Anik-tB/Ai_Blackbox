"use client";

import React, { useState } from "react";
import { Check, Copy, FileCode2 } from "lucide-react";

interface Props {
  patch: string | null;
}

export default function DiffViewer({ patch }: Props) {
  const [copied, setCopied] = useState(false);

  if (!patch) {
    return (
      <div className="p-6 text-center bg-slate-900/40 border border-slate-800 rounded-xl text-slate-500 text-sm">
        No code patch generated for this incident.
      </div>
    );
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(patch);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = patch.split("\n");

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 overflow-hidden text-xs font-mono">
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center space-x-2 text-slate-400">
          <FileCode2 className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-slate-300">Proposed Git Patch</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center space-x-1.5 px-2.5 py-1 text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded transition"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? "Copied!" : "Copy Diff"}</span>
        </button>
      </div>

      <div className="p-4 overflow-x-auto space-y-0.5">
        {lines.map((line, idx) => {
          let lineStyle = "text-slate-400";
          let bgStyle = "";

          if (line.startsWith("+") && !line.startsWith("+++")) {
            lineStyle = "text-emerald-300";
            bgStyle = "bg-emerald-950/30 -mx-4 px-4 block border-l-2 border-emerald-500";
          } else if (line.startsWith("-") && !line.startsWith("---")) {
            lineStyle = "text-rose-300";
            bgStyle = "bg-rose-950/30 -mx-4 px-4 block border-l-2 border-rose-500";
          } else if (line.startsWith("@@")) {
            lineStyle = "text-cyan-400 font-bold";
            bgStyle = "bg-cyan-950/20 -mx-4 px-4 block";
          } else if (line.startsWith("---") || line.startsWith("+++")) {
            lineStyle = "text-slate-500 font-bold";
          }

          return (
            <div key={idx} className={`${bgStyle} whitespace-pre`}>
              <span className={`inline-block w-8 text-right pr-3 text-slate-600 select-none`}>
                {idx + 1}
              </span>
              <span className={lineStyle}>{line}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
