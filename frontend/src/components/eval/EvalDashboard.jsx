import { useState, useEffect } from 'react';
import { Activity, ThumbsDown, ThumbsUp, MessageSquare, AlertTriangle } from 'lucide-react';

export default function EvalDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/eval/stats')
      .then(res => res.json())
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load eval stats:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="eval-dashboard" style={{ padding: '24px' }}>
        <p>Loading evaluation statistics...</p>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="eval-dashboard" style={{ padding: '24px' }}>
        <p>Failed to load evaluation statistics.</p>
      </div>
    );
  }

  return (
    <div className="eval-dashboard">
      <h1 style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Activity size={28} style={{ color: 'var(--accent-primary)' }}/> Evaluation Dashboard
      </h1>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '40px' }}>
        <div style={{ padding: '24px', backgroundColor: 'var(--bg-sidebar)', borderRadius: '12px', border: '1px solid var(--border)' }}>
          <h3 style={{ margin: '0 0 8px 0', color: 'var(--text-secondary)', fontSize: '14px' }}>Faithfulness Score</h3>
          <div style={{ fontSize: '32px', fontWeight: '700', color: stats.metrics.faithfulness > 0.8 ? 'var(--success)' : 'var(--warning)' }}>
            {(stats.metrics.faithfulness * 100).toFixed(1)}%
          </div>
          <p style={{ margin: '8px 0 0 0', fontSize: '12px', color: 'var(--text-tertiary)' }}>Based on {stats.metrics.total_evaluated} eval runs</p>
        </div>

        <div style={{ padding: '24px', backgroundColor: 'var(--bg-sidebar)', borderRadius: '12px', border: '1px solid var(--border)' }}>
          <h3 style={{ margin: '0 0 8px 0', color: 'var(--text-secondary)', fontSize: '14px' }}>Answer Relevancy</h3>
          <div style={{ fontSize: '32px', fontWeight: '700', color: stats.metrics.answer_relevancy > 0.8 ? 'var(--success)' : 'var(--warning)' }}>
            {(stats.metrics.answer_relevancy * 100).toFixed(1)}%
          </div>
          <p style={{ margin: '8px 0 0 0', fontSize: '12px', color: 'var(--text-tertiary)' }}>Measures how well answers address queries</p>
        </div>

        <div style={{ padding: '24px', backgroundColor: 'var(--bg-sidebar)', borderRadius: '12px', border: '1px solid var(--border)' }}>
          <h3 style={{ margin: '0 0 8px 0', color: 'var(--text-secondary)', fontSize: '14px' }}>User Feedback</h3>
          <div style={{ display: 'flex', gap: '24px', marginTop: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '24px', fontWeight: '600', color: 'var(--success)' }}>
              <ThumbsUp size={20} /> {stats.feedback.thumbs_up}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '24px', fontWeight: '600', color: 'var(--error)' }}>
              <ThumbsDown size={20} /> {stats.feedback.thumbs_down}
            </div>
          </div>
        </div>
      </div>

      <h2 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <MessageSquare size={20} /> Recent Negative Feedback
      </h2>
      
      {stats.feedback.recent_comments.length === 0 ? (
        <div style={{ padding: '32px', textAlign: 'center', backgroundColor: 'var(--bg-sidebar)', borderRadius: '12px', color: 'var(--text-tertiary)' }}>
          No negative feedback comments yet! 🎉
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {stats.feedback.recent_comments.map((item, idx) => (
            <div key={idx} style={{ padding: '20px', backgroundColor: 'var(--bg-sidebar)', borderRadius: '12px', borderLeft: '4px solid var(--error)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>{new Date(item.created_at).toLocaleString()}</span>
              </div>
              <div style={{ marginBottom: '12px', color: 'var(--text-secondary)', fontSize: '14px', fontStyle: 'italic' }}>
                "{item.message}"
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', color: 'var(--text-primary)' }}>
                <AlertTriangle size={16} style={{ color: 'var(--error)', marginTop: '2px', flexShrink: 0 }} />
                <span>{item.comment}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
