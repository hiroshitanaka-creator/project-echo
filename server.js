const http = require('http');
const { spawnSync } = require('child_process');

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let settled = false;
    let raw = '';
    const cleanup = () => {
      req.off('data', onData);
      req.off('end', onEnd);
      req.off('error', onError);
    };
    const finishError = (message) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(new Error(message));
    };
    const finishOk = (payload) => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(payload);
    };
    const onData = (chunk) => {
      if (settled) return;
      raw += chunk;
      if (raw.length > 1024 * 1024) {
        // Stop reading additional body bytes once size cap is exceeded.
        req.pause();
        raw = '';
        finishError('payload_too_large');
      }
    };
    const onEnd = () => {
      if (settled) return;
      if (!raw) {
        finishOk({});
        return;
      }
      try {
        finishOk(JSON.parse(raw));
      } catch (_err) {
        finishError('invalid_json');
      }
    };
    const onError = (_err) => {
      if (settled) return;
      finishError('invalid_request_stream');
    };
    req.on('data', onData);
    req.on('end', onEnd);
    req.on('error', onError);
  });
}

function json(res, statusCode, payload) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(payload));
}

function runPythonSchemaProbe() {
  const code = [
    'import json',
    'from pathlib import Path',
    'import sys',
    'sys.path.insert(0, str(Path.cwd() / "src"))',
    'from po_echo.voice_orchestration import VOICE_INPUT_SCHEMA, VOICE_OUTPUT_SCHEMA, inventory_voice_stack',
    'print(json.dumps({"input_schema": VOICE_INPUT_SCHEMA, "output_schema": VOICE_OUTPUT_SCHEMA, "inventory": inventory_voice_stack()}, ensure_ascii=False))',
  ].join('; ');

  return spawnSync('python3', ['-c', code], {
    cwd: process.cwd(),
    encoding: 'utf-8',
    env: process.env,
    timeout: 5000,
  });
}

const schemaDebugDetailEnabled = process.env.VOICE_SCHEMA_DEBUG_DETAIL === '1';
let schemaCache = null;
let schemaCacheError = null;

function getSchemaCached() {
  if (schemaCache) {
    return schemaCache;
  }
  if (schemaCacheError) {
    throw schemaCacheError;
  }

  const out = runPythonSchemaProbe();
  if (out.status !== 0) {
    const err = new Error('python_schema_probe_failed');
    if (schemaDebugDetailEnabled) {
      err.debugDetail = (out.stderr || '').trim();
    }
    schemaCacheError = err;
    throw err;
  }

  try {
    schemaCache = JSON.parse((out.stdout || '').trim());
    return schemaCache;
  } catch (_err) {
    const err = new Error('python_schema_probe_invalid_json');
    schemaCacheError = err;
    throw err;
  }
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'GET' && req.url === '/') {
    return json(res, 200, {
      service: 'project-echo-gateway',
      status: 'limited_gateway',
      capabilities: [
        'GET /health',
        'GET /api/voice/schema (canonical Python schema)',
        'POST /api/voice/run (truthful limitation response until external trust/session service is provisioned)',
      ],
      responsibility_boundary: 'Python modules remain canonical source of security/policy decisions.',
    });
  }

  if (req.method === 'GET' && req.url === '/health') {
    return json(res, 200, {
      ok: true,
      service: 'project-echo-gateway',
      now_utc: new Date().toISOString(),
    });
  }

  if (req.method === 'GET' && req.url === '/api/voice/schema') {
    try {
      return json(res, 200, getSchemaCached());
    } catch (err) {
      const response = {
        error: 'schema_unavailable',
      };
      if (schemaDebugDetailEnabled && err && err.debugDetail) {
        response.detail = err.debugDetail;
      }
      return json(res, 503, {
        ...response,
      });
    }
  }

  if (req.method === 'POST' && req.url === '/api/voice/run') {
    try {
      await readJsonBody(req);
    } catch (err) {
      if (err && err.message === 'payload_too_large') {
        return json(res, 413, {
          error: 'invalid_request',
          reason: 'payload_too_large',
        });
      }
      return json(res, 400, {
        error: 'invalid_request',
        reason: err && typeof err.message === 'string' ? err.message : 'invalid_request',
      });
    }

    return json(res, 501, {
      error: 'not_implemented',
      reason:
        'This gateway does not execute voice flow directly until a persistent trusted-device registry and session store are provisioned.',
      canonical_path: 'Use Python canonical flow (po_echo.voice_orchestration.run_voice_flow) behind trusted infrastructure.',
    });
  }

  return json(res, 404, { error: 'not_found' });
});

const port = process.env.PORT || 8080;

server.listen(port, '0.0.0.0', () => {
  // eslint-disable-next-line no-console
  console.log('Server is running on port ' + port);
});
