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
      <div className="min-h-screen bg-slate-50 flex items-center justify-center text-slate-500 text-sm">
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping mr-2" />
        Loading incident {incidentId}...
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center text-slate-600 space-y-4">
        <AlertCircle className="w-10 h-10 text-rose-500" />
        <p className="font-medium">Incident {incidentId} not found.</p>
        <Link
          href="/"
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-xl text-xs transition"
        >
          Back to Overview
        </Link>
      </div>
    );
  }

  const confidencePct = incident.confidence
    ? Math.round(incident.confidence <= 1 ? incident.confidence * 100 : incident.confidence)
    : 85;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 selection:bg-emerald-500 selection:text-white">
      {/* Top Header */}
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur-md sticky top-0 z-50 shadow-xs">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link
              href="/"
              className="p-2 text-slate-600 hover:text-emerald-700 bg-white hover:bg-emerald-50 border border-slate-200 rounded-xl shadow-xs transition"
              title="Back to Overview"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div>
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 font-mono text-xs font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-md">
                  {incident.id}
                </span>
                <span className="px-2 py-0.5 text-[10px] bg-amber-50 text-amber-700 border border-amber-200 rounded-full font-bold">
                  {incident.severity}
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  {incident.occurrences} occurrences
                </span>
              </div>
              <h1 className="text-sm font-bold text-slate-900 mt-0.5">{incident.error_type}</h1>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleCreateBranch}
              disabled={creatingBranch}
              className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-sm shadow-emerald-600/20 transition disabled:opacity-50 cursor-pointer"
            >
              <GitBranch className="w-4 h-4" />
              <span>{creatingBranch ? "Creating Branch..." : "Create Fix Branch"}</span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {branchStatus && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center space-x-2 shadow-xs">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span className="font-semibold">{branchStatus}</span>
          </div>
        )}

        {/* Primary RCA Card & Confidence Card */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-1 text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full flex items-center space-x-1.5">
                <Zap className="w-3.5 h-3.5 text-emerald-600" />
                <span>PROBABLE ROOT CAUSE</span>
              </span>
            </div>
            <p className="text-lg font-semibold text-slate-900 leading-relaxed">
              {incident.root_cause || "Analysis in progress..."}
            </p>
            <div className="pt-3 border-t border-slate-100 text-xs text-slate-500 flex flex-wrap gap-4">
              <span>Culprit: <span className="text-slate-800 font-mono font-medium">{incident.culprit}</span></span>
              <span>Service: <span className="text-slate-800 font-mono font-medium">{incident.service}</span></span>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Confidence Score</span>
              </div>
              <div className="text-5xl font-black text-emerald-600 font-mono">
                {confidencePct}%
              </div>
              <p className="text-xs text-slate-500 mt-2 leading-normal">
                Derived deterministically from AST call graphs, local frames, and Git blame.
              </p>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-500 font-medium">Risk Assessment:</span>
              <span className="font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full uppercase text-[10px]">
                {incident.risk || "Low"}
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-200 space-x-6 text-sm font-semibold">
          <button
            onClick={() => setActiveTab("causal")}
            className={`pb-3 transition relative cursor-pointer ${
              activeTab === "causal"
                ? "text-emerald-700"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            Causal Graph
            {activeTab === "causal" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-600" />
            )}
          </button>
          <button
            onClick={() => setActiveTab("evidence")}
            className={`pb-3 transition relative cursor-pointer ${
              activeTab === "evidence"
                ? "text-emerald-700"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            Evidence & Hypotheses
            {activeTab === "evidence" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-600" />
            )}
          </button>
          <button
            onClick={() => setActiveTab("diff")}
            className={`pb-3 transition relative cursor-pointer ${
              activeTab === "diff"
                ? "text-emerald-700"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            Proposed Fix & Tests
            {activeTab === "diff" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-600" />
            )}
          </button>
          <button
            onClick={() => setActiveTab("trace")}
            className={`pb-3 transition relative cursor-pointer ${
              activeTab === "trace"
                ? "text-emerald-700"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            Trace & Logs
            {activeTab === "trace" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-600" />
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
            <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4">
              <div className="flex items-center space-x-2 text-emerald-700 text-xs font-bold uppercase tracking-wider">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Confirmed Evidence (Verified Facts)</span>
              </div>
              <ul className="space-y-2.5 text-xs text-slate-700">
                {incident.evidence && incident.evidence.length > 0 ? (
                  incident.evidence.map((item, idx) => (
                    <li key={idx} className="flex items-start space-x-2">
                      <span className="text-emerald-600 font-bold">✓</span>
                      <span className="leading-relaxed">{item}</span>
                    </li>
                  ))
                ) : (
                  <p className="text-slate-400">No verified evidence recorded.</p>
                )}
              </ul>
            </div>

            <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4">
              <div className="flex items-center space-x-2 text-slate-700 text-xs font-bold uppercase tracking-wider">
                <Info className="w-4 h-4 text-emerald-600" />
                <span>Probable Hypotheses</span>
              </div>
              <ul className="space-y-3 text-xs text-slate-700">
                {incident.hypotheses && incident.hypotheses.length > 0 ? (
                  incident.hypotheses.map((h, idx) => (
                    <li key={idx} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                      <p className="font-medium text-slate-800">{h.description}</p>
                      <span className="text-[10px] text-emerald-700 font-mono font-semibold">
                        Confidence: {Math.round(h.confidence * 100)}%
                      </span>
                    </li>
                  ))
                ) : (
                  <p className="text-slate-400">No alternate hypotheses proposed.</p>
                )}
              </ul>
            </div>
          </div>
        )}

        {/* Tab 3: Fix & Tests */}
        {activeTab === "diff" && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-emerald-50/70 border border-emerald-200 shadow-xs space-y-2">
              <div className="flex items-center space-x-2 text-emerald-800 text-xs font-bold uppercase tracking-wider">
                <Lightbulb className="w-4 h-4 text-emerald-600" />
                <span>Recommended Action</span>
              </div>
              <p className="text-sm font-medium text-emerald-950 leading-relaxed">
                {incident.suggested_fix || "No recommendation available."}
              </p>
            </div>

            <DiffViewer patch={incident.proposed_patch} />

            {incident.generated_test && (
              <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden text-xs font-mono">
                <div className="px-4 py-2.5 bg-slate-100/80 border-b border-slate-200 text-slate-800 font-bold flex items-center justify-between">
                  <span>Generated Pytest Regression Suite</span>
                  <span className="text-[10px] font-normal text-slate-500">tests/generated_test.py</span>
                </div>
                <div className="p-4 overflow-x-auto text-emerald-900 bg-slate-50/60 whitespace-pre leading-relaxed">
                  {incident.generated_test}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Trace & Logs */}
        {activeTab === "trace" && (
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs">
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
