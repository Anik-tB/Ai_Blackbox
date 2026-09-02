"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Database,
  Layers,
  RefreshCw,
  Search,
  ShieldCheck,
  Zap,
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
    const interval = setInterval(loadData, 10000);
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
    <div className="min-h-screen bg-slate-50 text-slate-900 selection:bg-emerald-500 selection:text-white">
      {/* Top Header */}
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur-md sticky top-0 z-50 shadow-xs">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-emerald-600 rounded-xl shadow-md shadow-emerald-600/20 text-white font-bold tracking-wider text-sm flex items-center space-x-1.5">
              <ShieldCheck className="w-5 h-5" />
              <span>AIBD</span>
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                <span>AI Black Box Debugger</span>
                <span className="px-2 py-0.5 text-[10px] bg-emerald-50 text-emerald-700 font-semibold rounded-full border border-emerald-200">
                  v0.1.0
                </span>
              </h1>
              <p className="text-[11px] text-slate-500">
                Observability · AST & Git Correlation · Root Cause Engine
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1.5 bg-slate-100 rounded-full border border-slate-200 text-xs font-medium text-slate-700">
              <Database className="w-3.5 h-3.5 text-emerald-600" />
              <span>{health?.database_type || "Supabase / SQLite"}</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            </div>
            <button
              onClick={loadData}
              className="p-2 text-slate-600 hover:text-emerald-700 bg-white hover:bg-emerald-50 border border-slate-200 rounded-xl shadow-xs transition"
              title="Refresh Incidents"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-emerald-600" : ""}`} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* KPI Metrics in White & Green */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs hover:border-emerald-300 hover:shadow-sm transition">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-3">
              <span>Total Occurrences</span>
              <div className="p-2 bg-emerald-50 rounded-xl">
                <Activity className="w-4 h-4 text-emerald-600" />
              </div>
            </div>
            <div className="text-3xl font-bold tracking-tight text-slate-900 font-mono">
              {totalErrors}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Deduplicated across {incidents.length} incidents
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs hover:border-rose-300 hover:shadow-sm transition">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-3">
              <span>Critical Incidents</span>
              <div className="p-2 bg-rose-50 rounded-xl">
                <AlertOctagon className="w-4 h-4 text-rose-600" />
              </div>
            </div>
            <div className="text-3xl font-bold tracking-tight text-rose-600 font-mono">
              {criticalCount}
            </div>
            <p className="text-[11px] text-rose-600/80 mt-1">Requires immediate action</p>
          </div>

          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs hover:border-amber-300 hover:shadow-sm transition">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-3">
              <span>High Severity</span>
              <div className="p-2 bg-amber-50 rounded-xl">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
              </div>
            </div>
            <div className="text-3xl font-bold tracking-tight text-amber-600 font-mono">
              {highCount}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Uncaught exceptions & bugs</p>
          </div>

          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs hover:border-emerald-300 hover:shadow-sm transition">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-3">
              <span>Observed Services</span>
              <div className="p-2 bg-emerald-50 rounded-xl">
                <Layers className="w-4 h-4 text-emerald-600" />
              </div>
            </div>
            <div className="text-3xl font-bold tracking-tight text-emerald-700 font-mono">
              {uniqueServices}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">With fail-open agent hooks</p>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 bg-white border border-slate-200 rounded-2xl shadow-xs">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            <input
              type="text"
              placeholder="Search error, culprit, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
            />
          </div>

          {/* Severity selector tabs */}
          <div className="flex items-center space-x-1 p-1 bg-slate-100 border border-slate-200 rounded-xl text-xs">
            {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-3 py-1.5 rounded-lg font-semibold transition ${
                  severityFilter === sev
                    ? "bg-emerald-600 text-white shadow-sm"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        {/* Incidents Table */}
        <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  <th className="py-3.5 px-6">ID</th>
                  <th className="py-3.5 px-6">Error & Culprit</th>
                  <th className="py-3.5 px-6">Severity</th>
                  <th className="py-3.5 px-6 text-right">Count</th>
                  <th className="py-3.5 px-6">Service</th>
                  <th className="py-3.5 px-6">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {loading && incidents.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-600" />
                      Loading incidents...
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      No incidents matching your filter.
                    </td>
                  </tr>
                ) : (
                  filtered.map((inc) => {
                    const severityBadge =
                      inc.severity === "CRITICAL"
                        ? "bg-rose-50 text-rose-700 border-rose-200"
                        : inc.severity === "HIGH"
                        ? "bg-amber-50 text-amber-700 border-amber-200"
                        : "bg-emerald-50 text-emerald-700 border-emerald-200";

                    return (
                      <tr
                        key={inc.id}
                        className="hover:bg-emerald-50/30 transition group cursor-pointer"
                      >
                        <td className="py-4 px-6">
                          <Link
                            href={`/incidents/${inc.id}`}
                            className="inline-block px-2 py-0.5 font-mono font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-md hover:bg-emerald-100 transition"
                          >
                            {inc.id}
                          </Link>
                        </td>
                        <td className="py-4 px-6 max-w-md">
                          <div className="font-bold text-slate-900">{inc.error_type}</div>
                          <div className="text-slate-500 text-[11px] truncate mt-0.5">
                            {inc.error_message || "No error message provided"}
                          </div>
                          <div className="text-[10px] text-slate-400 font-mono mt-0.5">
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
                        <td className="py-4 px-6 text-right font-mono font-bold text-emerald-600">
                          {inc.occurrences}
                        </td>
                        <td className="py-4 px-6 text-slate-600 font-mono text-[11px]">
                          {inc.service}
                        </td>
                        <td className="py-4 px-6">
                          <Link
                            href={`/incidents/${inc.id}`}
                            className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs transition"
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
