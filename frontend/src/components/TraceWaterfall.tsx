"use client";

import React from "react";
import { Clock, Layers, Terminal } from "lucide-react";

interface Props {
  frames?: Array<{
    filename: string;
    lineno: number;
    function: string;
    code_line?: string;
    locals?: Record<string, any>;
  }>;
  breadcrumbs?: Array<{
    timestamp: number;
    category: string;
    level: string;
    message: string;
  }>;
}

export default function TraceWaterfall({ frames, breadcrumbs }: Props) {
  return (
    <div className="space-y-6">
      {/* Stack Trace Frames */}
      <div>
        <div className="flex items-center space-x-2 mb-3">
          <Layers className="w-4 h-4 text-blue-400" />
          <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
            Execution Call Stack ({frames?.length || 0} frames)
          </h3>
        </div>

        <div className="space-y-2">
          {frames && frames.length > 0 ? (
            frames.map((frame, idx) => (
              <div
                key={idx}
                className="p-3 bg-slate-950 border border-slate-800 rounded-xl hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-mono text-cyan-400 font-medium">
                    {frame.function}()
                  </span>
                  <span className="text-slate-500 font-mono">
                    {frame.filename.split("/").slice(-2).join("/")}:{frame.lineno}
                  </span>
                </div>
                {frame.code_line && (
                  <div className="p-2 bg-slate-900 rounded font-mono text-[11px] text-slate-300 overflow-x-auto border border-slate-800/60">
                    <code>{frame.code_line}</code>
                  </div>
                )}
                {frame.locals && Object.keys(frame.locals).length > 0 && (
                  <div className="mt-2 text-[10px] text-slate-500">
                    <span className="text-slate-400 font-semibold">Locals: </span>
                    {Object.entries(frame.locals).map(([k, v]) => (
                      <span key={k} className="inline-block mr-2 font-mono">
                        {k}=<span className="text-amber-400/90">{JSON.stringify(v)}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-500">No frames available.</p>
          )}
        </div>
      </div>

      {/* Breadcrumbs leading up to crash */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <Clock className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
              Chronological Breadcrumbs ({breadcrumbs.length})
            </h3>
          </div>

          <div className="space-y-1.5 border-l-2 border-slate-800 ml-2 pl-4">
            {breadcrumbs.map((b, idx) => (
              <div key={idx} className="relative text-xs py-1">
                <div className="absolute -left-[21px] top-2.5 w-2 h-2 rounded-full bg-slate-700 border border-slate-900" />
                <div className="flex items-center space-x-2">
                  <span className="px-1.5 py-0.2 text-[10px] bg-slate-800 text-slate-400 rounded font-mono uppercase">
                    {b.category}
                  </span>
                  <span className="text-slate-300 font-mono">{b.message}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
