/**
 * IntelliRAG API client
 * Handles all HTTP requests to the FastAPI backend.
 */

const API_BASE = '/api';

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  };

  // Remove Content-Type for FormData
  if (config.body instanceof FormData) {
    delete config.headers['Content-Type'];
  }

  const res = await fetch(url, config);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(res.status, data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Health ──
export const checkHealth = () => request('/health');

// ── Knowledge Bases ──
export const listKnowledgeBases = () => request('/knowledge-bases');
export const getKnowledgeBase = (id) => request(`/knowledge-bases/${id}`);
export const createKnowledgeBase = (data) =>
  request('/knowledge-bases', { method: 'POST', body: JSON.stringify(data) });
export const deleteKnowledgeBase = (id) =>
  request(`/knowledge-bases/${id}`, { method: 'DELETE' });

// ── Documents ──
export const listDocuments = (kbId) => request(`/documents/${kbId}`);
export const getDocumentStatus = (docId) => request(`/documents/${docId}/status`);
export const retryDocument = (docId) =>
  request(`/documents/${docId}/retry`, { method: 'POST' });
export const deleteDocument = (docId) =>
  request(`/documents/${docId}`, { method: 'DELETE' });

export const uploadDocument = async (kbId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('kb_id', kbId);
  return request('/documents/upload', { method: 'POST', body: formData });
};

// ── Conversations ──
export const listConversations = () => request('/conversations');
export const createConversation = (data) =>
  request('/conversations', { method: 'POST', body: JSON.stringify(data) });
export const getMessages = (conversationId) =>
  request(`/conversations/${conversationId}/messages`);
export const renameConversation = (id, title) =>
  request(`/conversations/${id}`, { method: 'PUT', body: JSON.stringify({ title }) });
export const deleteConversation = (id) =>
  request(`/conversations/${id}`, { method: 'DELETE' });

// ── Models ──
export const listModels = () => request('/models');
export const listEmbeddingModels = () => request('/models/embeddings');

// ── Chat (SSE Streaming) ──
export function streamChat(payload, onToken, onSources, onDone, onError) {
  const controller = new AbortController();

  fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: controller.signal,
  })
    .then(async (response) => {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let eventType = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6);
            try {
              const parsed = JSON.parse(data);
              switch (eventType) {
                case 'token':
                  onToken(parsed.token);
                  break;
                case 'sources':
                  onSources(parsed);
                  break;
                case 'done':
                  onDone(parsed);
                  break;
                case 'error':
                  onError(parsed.error);
                  break;
              }
            } catch (e) {
              // skip malformed JSON
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err.message);
      }
    });

  return controller;
}

// ── Feedback ──
export const submitFeedback = (messageId, feedback, comment) =>
  request('/chat/feedback', {
    method: 'POST',
    body: JSON.stringify({ message_id: messageId, feedback, comment }),
  });
