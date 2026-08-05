import { useState, useEffect } from 'react';
import { Settings, X, Zap, Search, BarChart3 } from 'lucide-react';

/**
 * Retrieval settings panel — configure fusion method, weights, top-k, reranker.
 */
export default function SettingsPanel({ onClose }) {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await fetch('/api/settings/retrieval');
      const data = await res.json();
      setSettings(data);
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = async (key, value) => {
    setSaving(true);
    try {
      const res = await fetch('/api/settings/retrieval', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [key]: value }),
      });
      const data = await res.json();
      setSettings(data);
    } catch (err) {
      console.error('Failed to update settings:', err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '550px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <h2 className="modal-title" style={{ margin: 0 }}>
            <Settings size={20} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
            Retrieval Settings
          </h2>
          <button className="btn-icon" onClick={onClose}><X size={18} /></button>
        </div>

        {settings && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Fusion Method */}
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">
                <Search size={13} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                Fusion Method
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                {['rrf', 'weighted_sum', 'dense_only'].map((method) => (
                  <button
                    key={method}
                    className={`btn ${settings.fusion_method === method ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => updateSetting('fusion_method', method)}
                    style={{ flex: 1, justifyContent: 'center', textTransform: 'uppercase', fontSize: 'var(--fs-xs)' }}
                  >
                    {method.replace('_', ' ')}
                  </button>
                ))}
              </div>
              <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-tertiary)', marginTop: '6px' }}>
                {settings.fusion_method === 'rrf' && 'Reciprocal Rank Fusion — Qdrant native, no tuning needed.'}
                {settings.fusion_method === 'weighted_sum' && 'Manual weighted combination — use the slider below to tune.'}
                {settings.fusion_method === 'dense_only' && 'Semantic search only — no sparse/keyword matching.'}
              </p>
            </div>

            {/* Weight slider (only for weighted_sum) */}
            {settings.fusion_method === 'weighted_sum' && (
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">
                  Dense/Sparse Weight: {settings.hybrid_search_weight.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0" max="1" step="0.05"
                  value={settings.hybrid_search_weight}
                  onChange={(e) => updateSetting('hybrid_search_weight', parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--fs-xs)', color: 'var(--text-tertiary)' }}>
                  <span>Pure Sparse (keyword)</span>
                  <span>Pure Dense (semantic)</span>
                </div>
              </div>
            )}

            {/* Top-K */}
            <div style={{ display: 'flex', gap: '16px' }}>
              <div className="form-group" style={{ margin: 0, flex: 1 }}>
                <label className="form-label">
                  <BarChart3 size={13} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                  Retrieval Top-K
                </label>
                <input
                  className="input"
                  type="number" min="1" max="100"
                  value={settings.top_k_retrieval}
                  onChange={(e) => updateSetting('top_k_retrieval', parseInt(e.target.value))}
                />
                <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                  Candidates from vector search
                </p>
              </div>
              <div className="form-group" style={{ margin: 0, flex: 1 }}>
                <label className="form-label">Rerank Top-K</label>
                <input
                  className="input"
                  type="number" min="1" max="50"
                  value={settings.top_k_rerank}
                  onChange={(e) => updateSetting('top_k_rerank', parseInt(e.target.value))}
                />
                <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                  Final results after reranking
                </p>
              </div>
            </div>

            {/* Reranker toggle */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 16px', background: 'var(--bg-glass)',
              borderRadius: 'var(--border-radius-sm)', border: '1px solid var(--border-color)',
            }}>
              <div>
                <div style={{ fontWeight: 500, fontSize: 'var(--fs-base)' }}>
                  <Zap size={14} style={{ marginRight: '6px', verticalAlign: 'middle', color: 'var(--accent-secondary)' }} />
                  Cross-Encoder Reranker
                </div>
                <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-tertiary)', marginTop: '2px' }}>
                  {settings.reranker_model}
                </div>
              </div>
              <button
                className={`btn ${settings.reranker_enabled ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => updateSetting('reranker_enabled', !settings.reranker_enabled)}
                style={{ minWidth: '60px', justifyContent: 'center' }}
              >
                {settings.reranker_enabled ? 'ON' : 'OFF'}
              </button>
            </div>

            {/* Cache stats */}
            {settings.reranker_cache && (
              <div style={{
                fontSize: 'var(--fs-xs)', color: 'var(--text-tertiary)',
                padding: '8px 12px', background: 'var(--bg-glass)',
                borderRadius: 'var(--border-radius-sm)',
              }}>
                Reranker cache: {settings.reranker_cache.currsize}/{settings.reranker_cache.maxsize} entries ·
                {' '}{settings.reranker_cache.hits} hits / {settings.reranker_cache.misses} misses
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
