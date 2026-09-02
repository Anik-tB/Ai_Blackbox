"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  GitBranch,
  GitCommit,
  Info,
  Layers,
  Lightbulb,
  ShieldCheck,
  Terminal,
  Zap,
} from "lucide-react";
import { createFixBranch, getIncident } from "../../../lib/api";
import { Incident } from "../../../lib/types";
import CausalGraph from "../../../components/CausalGraph";
import DiffViewer from "../../../components/DiffViewer";
import TraceWaterfall from "../../../components/TraceWaterfall";

export default function IncidentDetailPage() {
  const params = useParams();
  const incidentId = params?.id as string;
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [branchStatus, setBranchStatus] = useState<string | null>(null);
  const [creatingBranch, setCreatingBranch] = useState(false);
  const [activeTab, setActiveTab] = useState<"causal" | "evidence" | "diff" | "trace">("causal");

  useEffect(() => {
    if (!incidentId) return;
    const fetchDetail = async () => {
      setLoading(true);
      const data = await getIncident(incidentId);
      setIncident(data);
      setLoading(false);
    };
    fetchDetail();
  }, [incidentId]);

  const handleCreateBranch = async () => {
    if (!incident) return;
    setCreatingBranch(true);
    const res = await createFixBranch(incident.id);
    if (res.status === "success") {
      setBranchStatus(`Created branch: ${res.branch}`);
    } else {
      setBranchStatus(`Branch error: ${res.detail || "Unknown"}`);
    }
    setCreatingBranch(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400 text-sm">
        Loading incident {incidentId}...
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-400 space-y-4">
        <AlertCircle className="w-10 h-10 text-rose-500" />
        <p>Incident {incidentId} not found.</p>
        <Link href="/" className="px-4 py-2 bg-slate-800 text-slate-200 rounded-lg text-xs">
          Back to Overview
        </Link>
      </div>
    );
  }

  const confidencePct = incident.confidence
    ? Math.round(incident.confidence <= 1 ? incident.confidence * 100 : incident.confidence)
    : 85;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-blue-500 selection:text-white">
      {/* Top Bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link
              href="/"
              className="p-2 text-slate-400 hover:text-slate-200 bg-slate-800/60 hover:bg-slate-800 rounded-xl transition"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-sm font-bold text-amber-400">{incident.id}</span>
                <span className="px-2 py-0.5 text-[10px] bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-full font-bold">
                  {incident.severity}
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  {incident.occurrences} occurrences
                </span>
              </div>
              <h1 className="text-sm font-semibold text-slate-200">{incident.error_type}</h1>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleCreateBranch}
              disabled={creatingBranch}
              className="flex items-center space-x-2 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-medium transition shadow-lg shadow-emerald-600/20 disabled:opacity-50"
            >
              <GitBranch className="w-4 h-4" />
              <span>{creatingBranch ? "Creating Branch..." : "Create Fix Branch"}</span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {branchStatus && (
          <div className="p-3 bg-emerald-950/40 border border-emerald-500/30 rounded-xl text-xs text-emerald-300 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{branchStatus}</span>
          </div>
        )}

        {/* Primary RCA Card */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
            <div className="flex items-center space-x-2 text-rose-400 text-xs font-semibold uppercase tracking-wider">
              <Zap className="w-4 h-4" />
              <span>Probable Root Cause</span>
            </div>
            <p className="text-lg font-medium text-slate-100 leading-relaxed">
              {incident.root_cause || "Analysis in progress..."}
            </p>
            <div className="pt-2 border-t border-slate-800 text-xs text-slate-400 flex items-center space-x-4">
              <span>Culprit: <span className="text-slate-300 font-mono">{incident.culprit}</span></span>
              <span>Service: <span className="text-slate-300 font-mono">{incident.service}</span></span>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Confidence Score</span>
              </div>
              <div className="text-5xl font-extrabold text-emerald-400 font-mono">
                {confidencePct}%
              </div>
              <p className="text-xs text-slate-400 mt-2">
                Supported by AST syntax inspection, runtime stack frames, and Git blame history.
              </p>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between text-xs">
              <span className="text-slate-400">Risk Assessment:</span>
              <span className="font-semibold text-emerald-400 uppercase">
                {incident.risk || "Low"}
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-800 space-x-6 text-sm font-medium">
          <button
            onClick={() => setActiveTab("causal")}
            className={`pb-3 transition relative ${
              activeTab === "causal" ? "text-blue-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Causal Graph
            {activeTab === "causal" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />
            )}
          </button>
          <button
            onClick={() => setActiveTab("evidence")}
            className={`pb-3 transition relative ${
              activeTab === "evidence" ? "text-blue-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Evidence & Hypotheses
            {activeTab === "evidence" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />
            )}
          </button>
          <button
            onClick={() => setActiveTab("diff")}
            className={`pb-3 transition relative ${
              activeTab === "diff" ? "text-blue-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Proposed Fix & Tests
            {activeTab === "diff" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />
            )}
          </button>
          <button
            onClick={() => setActiveTab("trace")}
            className={`pb-3 transition relative ${
              activeTab === "trace" ? "text-blue-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Trace & Logs
            {activeTab === "trace" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />
            )}
          </button>
        </div>

        {/* Tab 1: Causal Graph */}
        {activeTab === "causal" && (
          <div className="space-y-6">
            <CausalGraph data={incident.causal_chain} />
          </div>
        )}

        {/* Tab 2: Evidence & Hypotheses */}
        {activeTab === "evidence" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div className="flex items-center space-x-2 text-emerald-400 text-xs font-semibold uppercase tracking-wider">
                <CheckCircle2 className="w-4 h-4" />
                <span>Confirmed Evidence (Verified Facts)</span>
              </div>
              <ul className="space-y-2.5 text-xs text-slate-300">
                {incident.evidence && incident.evidence.length > 0 ? (
                  incident.evidence.map((item, idx) => (
                    <li key={idx} className="flex items-start space-x-2">
                      <span className="text-emerald-400 font-bold">✓</span>
                      <span>{item}</span>
                    </li>
                  ))
                ) : (
                  <p className="text-slate-500">No verified evidence recorded.</p>
                )}
              </ul>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div className="flex items-center space-x-2 text-blue-400 text-xs font-semibold uppercase tracking-wider">
                <Info className="w-4 h-4" />
                <span>Probable Hypotheses</span>
              </div>
              <ul className="space-y-3 text-xs text-slate-300">
                {incident.hypotheses && incident.hypotheses.length > 0 ? (
                  incident.hypotheses.map((h, idx) => (
                    <li key={idx} className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                      <p className="text-slate-200">{h.description}</p>
                      <span className="text-[10px] text-blue-400 font-mono">
                        Confidence: {Math.round(h.confidence * 100)}%
                      </span>
                    </li>
                  ))
                ) : (
                  <p className="text-slate-500">No alternate hypotheses proposed.</p>
                )}
              </ul>
            </div>
          </div>
        )}

        {/* Tab 3: Fix & Tests */}
        {activeTab === "diff" && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
              <div className="flex items-center space-x-2 text-emerald-400 text-xs font-semibold uppercase tracking-wider">
                <Lightbulb className="w-4 h-4" />
                <span>Recommended Action</span>
              </div>
              <p className="text-sm text-slate-200 leading-relaxed">
                {incident.suggested_fix || "No recommendation available."}
              </p>
            </div>

            <DiffViewer patch={incident.proposed_patch} />

            {incident.generated_test && (
              <div className="rounded-xl border border-slate-800 bg-slate-950 overflow-hidden text-xs font-mono">
                <div className="px-4 py-2.5 bg-slate-900/80 border-b border-slate-800 text-slate-300 font-semibold">
                  Generated Pytest Regression Suite
                </div>
                <div className="p-4 overflow-x-auto text-cyan-300 whitespace-pre">
                  {incident.generated_test}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Trace & Logs */}
        {activeTab === "trace" && (
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800">
            <TraceWaterfall
              frames={incident.latest_event?.frames}
              breadcrumbs={incident.latest_event?.breadcrumbs}
            />
          </div>
        )}
      </main>
    </div>
  );
}
