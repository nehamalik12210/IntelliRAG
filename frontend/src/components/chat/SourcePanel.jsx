import { useState, useEffect, useRef } from 'react';
import { X, FileText, ChevronDown, ChevronUp, Zap, Clock } from 'lucide-react';

/**
 * Enhanced Source Panel — shows retrieved chunks with expandable full text,
 * score visualizations, retrieval method indicator, and latency.
 */
export default function SourcePanel({ sources, metadata, activeSourceIndex, onClose }) {
  const [expanded, setExpanded] = useState({});
  const [highlightedIndex, setHighlightedIndex] = useState(null);
  const cardRefs = useRef({});

  useEffect(() => {
    if (activeSourceIndex !== null && activeSourceIndex !== undefined) {
      // Auto-expand the clicked source
      setExpanded((prev) => ({ ...prev, [activeSourceIndex]: true }));
      
      // Temporarily highlight it
      setHighlightedIndex(activeSourceIndex);
      const timer = setTimeout(() => setHighlightedIndex(null), 2000);

      // Scroll to it
      if (cardRefs.current[activeSourceIndex]) {
        cardRefs.current[activeSourceIndex].scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }
      return () => clearTimeout(timer);
    }
  }, [activeSourceIndex]);

  if (!sources || sources.length === 0) return null;

  const toggleExpand = (i) => {
    setExpanded((prev) => ({ ...prev, [i]: !prev[i] }));
  };

  return (
    <div className="source-panel">
      <div className="source-panel-header">
        <span className="source-panel-title">Sources ({sources.length})</span>
        <button className="btn-icon" onClick={onClose}>
          <X size={18} />
        </button>
      </div>

      {/* Retrieval metadata */}
      {metadata && (
        <div style={{
          display: 'flex', gap: '12px', flexWrap: 'wrap',
          padding: '8px 12px', background: 'var(--bg-glass)',
          borderRadius: 'var(--border-radius-sm)', fontSize: 'var(--fs-xs)',
          color: 'var(--text-secondary)',
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Zap size={11} />
            {metadata.retrieval_method || 'unknown'}
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={11} />
            {metadata.retrieval_latency_ms || 0}ms
          </span>
          <span>{metadata.chunks_retrieved || 0} chunks retrieved</span>
        </div>
      )}

      {sources.map((source, i) => (
        <div 
          key={i} 
          ref={(el) => (cardRefs.current[i] = el)}
          className={`source-card ${highlightedIndex === i ? 'highlighted' : ''}`}
        >
          <div
            className="source-card-header"
            style={{ cursor: 'pointer' }}
            onClick={() => toggleExpand(i)}
          >
            <FileText size={14} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
            <span className="source-card-filename" style={{ flex: 1 }}>{source.filename}</span>
            {source.page_number > 0 && (
              <span className="source-card-page">Page {source.page_number}</span>
            )}
            {expanded[i] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>

          {/* Score bar */}
          <div style={{ margin: '8px 0 4px' }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between',
              fontSize: 'var(--fs-xs)', color: 'var(--text-tertiary)', marginBottom: '4px',
            }}>
              <span>Relevance</span>
              <span>{(source.relevance_score * 100).toFixed(1)}%</span>
            </div>
            <div style={{
              height: '4px', background: 'var(--bg-input)',
              borderRadius: '2px', overflow: 'hidden',
            }}>
              <div style={{
                height: '100%', borderRadius: '2px',
                width: `${Math.min(source.relevance_score * 100, 100)}%`,
                background: source.relevance_score > 0.7
                  ? 'var(--success)' : source.relevance_score > 0.4
                  ? 'var(--warning)' : 'var(--error)',
                transition: 'width 0.3s ease',
              }} />
            </div>
          </div>

          {/* Expandable content */}
          <div className="source-card-content" style={{
            maxHeight: expanded[i] ? '500px' : '60px',
            overflow: 'hidden',
            transition: 'max-height 0.3s ease',
          }}>
            {source.content_preview}
          </div>

          {!expanded[i] && source.content_preview && source.content_preview.length > 100 && (
            <button
              onClick={() => toggleExpand(i)}
              style={{
                background: 'none', border: 'none', color: 'var(--accent-primary)',
                fontSize: 'var(--fs-xs)', cursor: 'pointer', padding: '4px 0',
              }}
            >
              Show more
            </button>
          )}

          {/* Reranker score if available */}
          {source.rerank_score !== undefined && (
            <div className="source-card-score" style={{ marginTop: '6px' }}>
              Reranker: {(source.rerank_score * 100).toFixed(1)}% · Original: {(source.original_score * 100).toFixed(1)}%
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
