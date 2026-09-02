"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  Database,
  Layers,
  RefreshCw,
  Search,
  ShieldAlert,
  Terminal,
} from "lucide-react";
import { getHealth, getIncidents } from "../lib/api";
import { Incident } from "../lib/types";

export default function OverviewPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [health, setHealth] = useState<any>(null);

  const loadData = async () => {
    setLoading(true);
    const [incList, healthData] = await Promise.all([
      getIncidents(severityFilter === "ALL" ? undefined : severityFilter),
      getHealth(),
    ]);
    setIncidents(incList);
    setHealth(healthData);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // 10s auto-refresh
    return () => clearInterval(interval);
  }, [severityFilter]);

  const filtered = incidents.filter((inc) => {
    const q = searchQuery.toLowerCase();
    return (
      inc.id.toLowerCase().includes(q) ||
      inc.error_type.toLowerCase().includes(q) ||
      (inc.error_message || "").toLowerCase().includes(q) ||
      (inc.culprit || "").toLowerCase().includes(q) ||
      (inc.service || "").toLowerCase().includes(q)
    );
  });

  const criticalCount = incidents.filter((i) => i.severity === "CRITICAL").length;
  const highCount = incidents.filter((i) => i.severity === "HIGH").length;
  const uniqueServices = new Set(incidents.map((i) => i.service)).size;
  const totalErrors = incidents.reduce((acc, curr) => acc + (curr.occurrences || 1), 0);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-blue-500 selection:text-white">
      {/* Top Navigation */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20 text-white font-bold tracking-wider text-sm flex items-center space-x-1.5">
              <ShieldAlert className="w-5 h-5" />
              <span>AIBD</span>
            </div>
            <div>
              <h1 className="text-sm font-semibold text-slate-100 flex items-center space-x-2">
                <span>AI Black Box Debugger</span>
                <span className="px-2 py-0.5 text-[10px] bg-slate-800 text-slate-400 rounded-full border border-slate-700">
                  v0.1.0
                </span>
              </h1>
              <p className="text-[11px] text-slate-400">
                Observability · AST & Git Correlation · Root Cause Engine
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1.5 px-3 py-1 bg-slate-800/80 rounded-full border border-slate-700 text-xs text-slate-300">
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              <span>{health?.database_type || "Supabase / SQLite"}</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse ml-1" />
            </div>
            <button
              onClick={loadData}
              className="p-2 text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg transition"
              title="Refresh Incidents"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-400" : ""}`} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* KPI Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
              <span>Total Occurrences</span>
              <Activity className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-3xl font-bold tracking-tight text-white font-mono">
              {totalErrors}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Deduplicated across {incidents.length} fingerprints</p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
              <span>Critical Incidents</span>
              <AlertOctagon className="w-4 h-4 text-rose-400" />
            </div>
            <div className="text-3xl font-bold tracking-tight text-rose-400 font-mono">
              {criticalCount}
            </div>
            <p className="text-[11px] text-rose-500/80 mt-1">Immediate action required</p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
              <span>High Severity</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-3xl font-bold tracking-tight text-amber-400 font-mono">
              {highCount}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Uncaught exceptions & bugs</p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
              <span>Observed Services</span>
              <Layers className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-3xl font-bold tracking-tight text-emerald-400 font-mono">
              {uniqueServices}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">With fail-open agent hooks</p>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 bg-slate-900/40 border border-slate-800/80 rounded-2xl">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
            <input
              type="text"
              placeholder="Search error, culprit, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          {/* Severity selector tabs */}
          <div className="flex items-center space-x-1 p-1 bg-slate-950 border border-slate-800 rounded-xl text-xs">
            {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-3 py-1.5 rounded-lg font-medium transition ${
                  severityFilter === sev
                    ? "bg-slate-800 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        {/* Incidents Table */}
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/50 backdrop-blur-sm overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-3.5 px-6">ID</th>
                  <th className="py-3.5 px-6">Error & Culprit</th>
                  <th className="py-3.5 px-6">Severity</th>
                  <th className="py-3.5 px-6 text-right">Count</th>
                  <th className="py-3.5 px-6">Service</th>
                  <th className="py-3.5 px-6">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs">
                {loading && incidents.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-500">
                      <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-500" />
                      Loading incidents...
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-500">
                      No incidents matching your filter.
                    </td>
                  </tr>
                ) : (
                  filtered.map((inc) => {
                    const severityBadge =
                      inc.severity === "CRITICAL"
                        ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                        : inc.severity === "HIGH"
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        : "bg-blue-500/10 text-blue-400 border-blue-500/20";

                    return (
                      <tr
                        key={inc.id}
                        className="hover:bg-slate-800/40 transition group cursor-pointer"
                      >
                        <td className="py-4 px-6 font-mono font-bold text-amber-400">
                          <Link href={`/incidents/${inc.id}`} className="hover:underline">
                            {inc.id}
                          </Link>
                        </td>
                        <td className="py-4 px-6 max-w-md">
                          <div className="font-semibold text-slate-200">{inc.error_type}</div>
                          <div className="text-slate-400 text-[11px] truncate">
                            {inc.error_message || "No error message provided"}
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                            {inc.culprit}
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          <span
                            className={`px-2.5 py-1 rounded-full text-[10px] font-semibold tracking-wide border ${severityBadge}`}
                          >
                            {inc.severity}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-right font-mono font-semibold text-cyan-400">
                          {inc.occurrences}
                        </td>
                        <td className="py-4 px-6 text-slate-400 font-mono text-[11px]">
                          {inc.service}
                        </td>
                        <td className="py-4 px-6">
                          <Link
                            href={`/incidents/${inc.id}`}
                            className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium transition shadow-sm"
                          >
                            <span>Explain</span>
                            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition" />
                          </Link>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
