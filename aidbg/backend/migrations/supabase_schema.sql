-- ==============================================================================
-- AI Black Box Debugger (AIBD) - Supabase / PostgreSQL Database Schema
-- Run this in your Supabase SQL Editor or migration runner
-- ==============================================================================

-- Enable extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: incidents
-- Aggregates deduplicated errors by fingerprint (e.g. A7F82C)
CREATE TABLE IF NOT EXISTS incidents (
    id VARCHAR(16) PRIMARY KEY,
    error_type VARCHAR(128) NOT NULL,
    error_message TEXT,
    service VARCHAR(128) DEFAULT 'default-service',
    culprit VARCHAR(256),
    severity VARCHAR(32) DEFAULT 'HIGH',
    occurrences INTEGER DEFAULT 1,
    first_seen DOUBLE PRECISION,
    last_seen DOUBLE PRECISION,
    status VARCHAR(32) DEFAULT 'open',
    root_cause TEXT,
    confidence REAL,
    causal_chain JSONB DEFAULT '[]'::jsonb,
    evidence JSONB DEFAULT '[]'::jsonb,
    hypotheses JSONB DEFAULT '[]'::jsonb,
    suggested_fix TEXT,
    proposed_patch TEXT,
    generated_test TEXT,
    risk VARCHAR(32),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_last_seen ON incidents(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);

-- Table: events
-- Individual raw occurrences captured for an incident
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    incident_id VARCHAR(16) REFERENCES incidents(id) ON DELETE CASCADE,
    trace_id VARCHAR(64),
    span_id VARCHAR(64),
    frames JSONB DEFAULT '[]'::jsonb,
    request_context JSONB DEFAULT '{}'::jsonb,
    breadcrumbs JSONB DEFAULT '[]'::jsonb,
    system_metadata JSONB DEFAULT '{}'::jsonb,
    extra JSONB DEFAULT '{}'::jsonb,
    timestamp DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_incident_id ON events(incident_id);
CREATE INDEX IF NOT EXISTS idx_events_trace_id ON events(trace_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);

-- Enable Supabase Realtime replication on incidents
ALTER PUBLICATION supabase_realtime ADD TABLE incidents;
