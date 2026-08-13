/**
 * M4.2 Phase J: single centralized fetch client for the PULLI backend.
 * No component should call fetch() directly for backend requests --
 * everything routes through here, per the task's explicit
 * "do not scatter fetch() calls" rule.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 30000;

/** @param {string} kind @param {string} message @param {number} [status] @returns {import('./types').ApiError} */
function apiError(kind, message, status) {
  return { kind, message, status };
}

/**
 * @param {string} path
 * @param {RequestInit} options
 * @returns {Promise<{data: any, error: null} | {data: null, error: import('./types').ApiError}>}
 */
async function request(path, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal });
    clearTimeout(timeoutId);

    let body;
    try {
      body = await res.json();
    } catch {
      return { data: null, error: apiError('unknown', 'Backend returned a non-JSON response', res.status) };
    }

    if (!res.ok) {
      if (res.status === 503) {
        return { data: null, error: apiError('model_unavailable', body.error || 'Model unavailable', res.status) };
      }
      if (res.status === 400) {
        return { data: null, error: apiError('invalid_image', body.error || 'Invalid request', res.status) };
      }
      return { data: null, error: apiError('unknown', body.error || `Request failed (${res.status})`, res.status) };
    }

    return { data: body, error: null };
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      return { data: null, error: apiError('timeout', `Request timed out after ${DEFAULT_TIMEOUT_MS}ms`) };
    }
    return { data: null, error: apiError('backend_unavailable', 'Could not reach the PULLI backend. Is the API server running?') };
  }
}

/** @returns {Promise<{data: any, error: null} | {data: null, error: import('./types').ApiError}>} */
export function getHealth() {
  return request('/api/v1/health');
}

/** @returns {Promise<{data: any, error: null} | {data: null, error: import('./types').ApiError}>} */
export function getModelInfo() {
  return request('/api/v1/model');
}

/**
 * @param {File} imageFile
 * @param {import('./types').DetectorName} detector
 * @returns {Promise<{data: import('./types').DetectResult, error: null} | {data: null, error: import('./types').ApiError}>}
 */
export function detect(imageFile, detector = 'classical') {
  const form = new FormData();
  form.append('image', imageFile);
  form.append('detector', detector);
  return request('/api/v1/detect', { method: 'POST', body: form });
}

/**
 * @param {File} imageFile
 * @param {import('./types').DetectorName} detector
 * @returns {Promise<{data: import('./types').AnalyzeResult, error: null} | {data: null, error: import('./types').ApiError}>}
 */
export function analyze(imageFile, detector = 'classical') {
  const form = new FormData();
  form.append('image', imageFile);
  form.append('detector', detector);
  return request('/api/v1/analyze', { method: 'POST', body: form });
}

/**
 * @param {File} imageFile
 * @param {import('./types').DetectorName} detector
 */
export function reconstruct(imageFile, detector = 'classical') {
  const form = new FormData();
  form.append('image', imageFile);
  form.append('detector', detector);
  return request('/api/v1/reconstruct', { method: 'POST', body: form });
}

/**
 * @param {File} imageFile
 * @returns {Promise<{data: import('./types').CompareResult, error: null} | {data: null, error: import('./types').ApiError}>}
 */
export function compareDetectors(imageFile) {
  const form = new FormData();
  form.append('image', imageFile);
  return request('/api/v1/compare-detectors', { method: 'POST', body: form });
}
