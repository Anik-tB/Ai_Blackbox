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
          <Layers className="w-4 h-4 text-emerald-600" />
          <h3 className="text-xs font-bold tracking-wider text-slate-500 uppercase">
            Execution Call Stack ({frames?.length || 0} frames)
          </h3>
        </div>

        <div className="space-y-2">
          {frames && frames.length > 0 ? (
            frames.map((frame, idx) => (
              <div
                key={idx}
                className="p-3.5 bg-slate-50/60 border border-slate-200 rounded-xl hover:border-emerald-300 transition"
              >
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-mono text-emerald-800 font-bold">
                    {frame.function}()
                  </span>
                  <span className="text-slate-500 font-mono text-[11px]">
                    {frame.filename.split("/").slice(-2).join("/")}:{frame.lineno}
                  </span>
                </div>
                {frame.code_line && (
                  <div className="p-2.5 bg-white rounded-lg font-mono text-[11px] text-slate-800 overflow-x-auto border border-slate-200 shadow-2xs">
                    <code>{frame.code_line}</code>
                  </div>
                )}
                {frame.locals && Object.keys(frame.locals).length > 0 && (
                  <div className="mt-2 text-[10px] text-slate-500">
                    <span className="text-slate-700 font-bold">Locals: </span>
                    {Object.entries(frame.locals).map(([k, v]) => (
                      <span key={k} className="inline-block mr-2 font-mono">
                        {k}=<span className="text-amber-700 font-medium">{JSON.stringify(v)}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-400">No frames available.</p>
          )}
        </div>
      </div>

      {/* Chronological Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <Clock className="w-4 h-4 text-emerald-600" />
            <h3 className="text-xs font-bold tracking-wider text-slate-500 uppercase">
              Chronological Breadcrumbs ({breadcrumbs.length})
            </h3>
          </div>

          <div className="space-y-2 border-l-2 border-emerald-200 ml-2 pl-4">
            {breadcrumbs.map((b, idx) => (
              <div key={idx} className="relative text-xs py-0.5">
                <div className="absolute -left-[21px] top-2 w-2 h-2 rounded-full bg-emerald-500 border-2 border-white shadow-xs" />
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md font-mono font-semibold uppercase">
                    {b.category}
                  </span>
                  <span className="text-slate-800 font-mono font-medium">{b.message}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
