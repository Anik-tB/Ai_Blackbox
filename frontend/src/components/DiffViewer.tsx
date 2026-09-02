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
      <div className="p-6 text-center bg-white border border-slate-200 rounded-xl text-slate-500 text-sm shadow-xs">
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
    <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden text-xs font-mono">
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-50 border-b border-slate-200">
        <div className="flex items-center space-x-2 text-slate-700 font-bold">
          <FileCode2 className="w-4 h-4 text-emerald-600" />
          <span>Proposed Git Patch</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center space-x-1.5 px-3 py-1 text-slate-600 hover:text-emerald-700 bg-white hover:bg-emerald-50 border border-slate-200 rounded-md shadow-2xs transition cursor-pointer"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? "Copied!" : "Copy Diff"}</span>
        </button>
      </div>

      <div className="p-4 overflow-x-auto space-y-0.5 bg-white">
        {lines.map((line, idx) => {
          let lineStyle = "text-slate-600";
          let bgStyle = "";

          if (line.startsWith("+") && !line.startsWith("+++")) {
            lineStyle = "text-emerald-900 font-medium";
            bgStyle = "bg-emerald-50 -mx-4 px-4 block border-l-3 border-emerald-600";
          } else if (line.startsWith("-") && !line.startsWith("---")) {
            lineStyle = "text-rose-900 font-medium";
            bgStyle = "bg-rose-50 -mx-4 px-4 block border-l-3 border-rose-500";
          } else if (line.startsWith("@@")) {
            lineStyle = "text-cyan-800 font-bold";
            bgStyle = "bg-cyan-50/60 -mx-4 px-4 block";
          } else if (line.startsWith("---") || line.startsWith("+++")) {
            lineStyle = "text-slate-400 font-bold";
          }

          return (
            <div key={idx} className={`${bgStyle} whitespace-pre py-0.5`}>
              <span className="inline-block w-8 text-right pr-3 text-slate-400 select-none font-mono">
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
