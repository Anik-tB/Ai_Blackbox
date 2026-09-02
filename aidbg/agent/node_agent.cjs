/**
 * AI Black Box Debugger (AIBD) - Zero-Dependency Node.js Observability Agent.
 * Compatible with Node.js 14+, Express, Fastify, Next.js, and pure Node.js scripts.
 * Fail-open architecture: Never crashes or degrades the host application.
 */

const http = require('http');
const https = require('https');
const path = require('path');
const os = require('os');
const fs = require('fs');

const ENDPOINT = process.env.AIDBG_ENDPOINT || 'http://127.0.0.1:8765/api/v1/incidents/ingest';
const SERVICE = process.env.AIDBG_SERVICE || 'node-service';
const SENSITIVE_KEYS = ['password', 'token', 'secret', 'authorization', 'cookie', 'api_key', 'jwt', 'bearer'];

// Ring buffer for chronological breadcrumbs
const breadcrumbs = [];
const MAX_BREADCRUMBS = 30;

function addBreadcrumb(category, message, level = 'info') {
  breadcrumbs.push({
    timestamp: Date.now() / 1000,
    category,
    level,
    message: String(message).slice(0, 500)
  });
  if (breadcrumbs.length > MAX_BREADCRUMBS) {
    breadcrumbs.shift();
  }
}

// Secret sanitizer
function sanitizeValue(key, val) {
  if (typeof val === 'string') {
    const lk = key.toLowerCase();
    for (const sk of SENSITIVE_KEYS) {
      if (lk.includes(sk)) return '[REDACTED]';
    }
  } else if (val && typeof val === 'object') {
    return sanitizeObject(val);
  }
  return val;
}

function sanitizeObject(obj, depth = 0) {
  if (!obj || typeof obj !== 'object' || depth > 4) return obj;
  if (Array.isArray(obj)) return obj.map(item => sanitizeObject(item, depth + 1));
  const clean = {};
  for (const [k, v] of Object.entries(obj)) {
    clean[k] = sanitizeValue(k, v);
  }
  return clean;
}

// Stack trace parser
function parseStackTrace(error) {
  if (!error || !error.stack) return [];
  const lines = error.stack.split('\n');
  const frames = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    // Format: at functionName (filename:line:col) or at filename:line:col
    const match = line.match(/^at\s+(?:([^\s(]+)\s+\(([^:]+):(\d+):(\d+)\)|([^:]+):(\d+):(\d+))$/);
    if (match) {
      const fn = match[1] || '<anonymous>';
      const file = match[2] || match[5];
      const lineno = parseInt(match[3] || match[6], 10);
      let code_line = '';

      // Skip internal node: modules for code reading
      if (file && !file.startsWith('node:') && fs.existsSync(file)) {
        try {
          const srcLines = fs.readFileSync(file, 'utf8').split('\n');
          if (lineno > 0 && lineno <= srcLines.length) {
            code_line = srcLines[lineno - 1].trim();
          }
        } catch {}
      }

      frames.push({
        filename: file,
        lineno,
        function: fn,
        code_line
      });
    }
  }
  return frames;
}

// Fail-open dispatch
function sendPayload(payload) {
  try {
    const urlObj = new URL(ENDPOINT);
    const postData = JSON.stringify(payload);
    const transport = urlObj.protocol === 'https:' ? https : http;

    const req = transport.request({
      hostname: urlObj.hostname,
      port: urlObj.port || (urlObj.protocol === 'https:' ? 443 : 80),
      path: urlObj.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      },
      timeout: 3000
    }, () => {});

    req.on('error', () => {
      // Fail-open: silently ignore transport errors
    });

    req.write(postData);
    req.end();
  } catch {}
}

let lastCaptured = { msg: '', time: 0 };

function captureException(error, context = {}) {
  try {
    if (!error) return;
    const now = Date.now();
    const errMsg = error.message || String(error);

    // Deduplicate rapid identical exceptions
    if (lastCaptured.msg === errMsg && now - lastCaptured.time < 500) {
      return;
    }
    lastCaptured = { msg: errMsg, time: now };

    const frames = parseStackTrace(error);
    const errType = error.name || 'Error';
    const culprit = frames.length > 0 ? `${frames[frames.length - 1].filename}:${frames[frames.length - 1].lineno}` : 'unknown';

    const payload = {
      error_type: errType,
      error_message: errMsg,
      frames,
      culprit,
      tags: {
        service: SERVICE,
        language: 'javascript',
        runtime: 'node',
        version: process.version,
        platform: process.platform
      },
      breadcrumbs: [...breadcrumbs],
      request: sanitizeObject(context.request || {}),
      timestamp: now / 1000
    };

    sendPayload(payload);
  } catch {}
}

// Hook 1: Uncaught Exceptions
process.on('uncaughtException', (err) => {
  console.error(err && err.stack ? err.stack : err);
  captureException(err, { source: 'uncaughtException' });
  setTimeout(() => {
    process.exit(1);
  }, 300);
});

// Hook 2: Unhandled Promise Rejections
process.on('unhandledRejection', (reason) => {
  const err = reason instanceof Error ? reason : new Error(String(reason));
  err.name = err.name || 'UnhandledPromiseRejection';
  captureException(err, { source: 'unhandledRejection' });
});

// Hook 3: HTTP Server & Express Request Interception
const originalCreateServer = http.createServer;
http.createServer = function(...args) {
  const server = originalCreateServer.apply(this, args);
  server.on('request', (req, res) => {
    const reqInfo = {
      method: req.method,
      url: req.url,
      headers: sanitizeObject(req.headers)
    };
    addBreadcrumb('http.request', `${req.method} ${req.url}`);

    // Intercept response errors
    res.on('finish', () => {
      if (res.statusCode >= 500) {
        addBreadcrumb('http.response', `HTTP ${res.statusCode} for ${req.method} ${req.url}`, 'error');
      }
    });
  });
  return server;
};

// Express error middleware export
module.exports = {
  captureException,
  addBreadcrumb,
  aidbgMiddleware: (err, req, res, next) => {
    captureException(err, {
      request: {
        method: req.method,
        url: req.url,
        query: req.query,
        body: req.body,
        headers: req.headers
      }
    });
    next(err);
  }
};
