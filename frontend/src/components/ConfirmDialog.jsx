import React from 'react';

/**
 * A reusable modal dialog for confirming destructive actions.
 */
export default function ConfirmDialog({ title, message, onConfirm, onCancel, confirmText = "Confirm", isDestructive = true }) {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">{title}</h2>
        <div style={{ marginBottom: '24px', color: 'var(--text-secondary)' }}>
          {message}
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button 
            type="button" 
            className={`btn ${isDestructive ? 'btn-danger' : 'btn-primary'}`} 
            onClick={onConfirm}
            style={isDestructive ? { backgroundColor: '#ef4444', color: '#fff', border: 'none' } : {}}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
