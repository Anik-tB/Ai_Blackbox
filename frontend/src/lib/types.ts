export interface CausalNode {
  id: string;
  label: string;
  type: "fact" | "hypothesis" | "anomaly" | "action";
  metadata?: Record<string, any>;
}

export interface CausalEdge {
  from: string;
  to: string;
  reason: string;
  confidence: number;
  evidence?: string;
}

export interface CausalGraphData {
  nodes: CausalNode[];
  edges: CausalEdge[];
}

export interface Hypothesis {
  description: string;
  confidence: number;
}

export interface Incident {
  id: string;
  error_type: string;
  error_message: string;
  service: string;
  culprit: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  occurrences: number;
  first_seen: number;
  last_seen: number;
  status: string;
  root_cause: string | null;
  confidence: number | null;
  causal_chain: CausalGraphData | null;
  evidence: string[];
  hypotheses: Hypothesis[];
  suggested_fix: string | null;
  proposed_patch: string | null;
  generated_test: string | null;
  risk: "low" | "medium" | "high" | null;
  latest_event?: {
    trace_id?: string;
    frames?: Array<{
      filename: string;
      lineno: number;
      function: string;
      code_line?: string;
      pre_context?: string[];
      post_context?: string[];
      locals?: Record<string, any>;
    }>;
    request_context?: {
      method?: string;
      path?: string;
      headers?: Record<string, string>;
      client_ip?: string;
    };
    breadcrumbs?: Array<{
      timestamp: number;
      category: string;
      level: string;
      message: string;
    }>;
  };
}
