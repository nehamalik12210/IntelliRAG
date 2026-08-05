import { useState } from 'react';
import { Database, FileText, Plus, Trash2 } from 'lucide-react';
import { deleteKnowledgeBase } from '../../services/api';
import ConfirmDialog from '../ConfirmDialog';

/**
 * Knowledge Base card grid — lists all KBs with stats and create button.
 */
export default function KBList({ knowledgeBases, onSelect, onCreate, onKBDeleted }) {
  const [kbToDelete, setKbToDelete] = useState(null);

  const handleDeleteKBConfirm = async () => {
    if (!kbToDelete) return;
    try {
      await deleteKnowledgeBase(kbToDelete.id);
      setKbToDelete(null);
      if (onKBDeleted) onKBDeleted();
    } catch (err) {
      alert(`Delete KB failed: ${err.message}`);
    }
  };
  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Knowledge Bases</h1>
          <p className="page-subtitle">Manage your document collections</p>
        </div>
        <button className="btn btn-primary" onClick={onCreate}>
          <Plus size={16} /> New Knowledge Base
        </button>
      </div>

      {knowledgeBases.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">
            <Database size={64} strokeWidth={1} />
          </div>
          <h3 className="empty-state-title">No knowledge bases yet</h3>
          <p className="empty-state-text">
            Create your first knowledge base to start uploading documents and asking questions.
          </p>
          <button className="btn btn-primary" style={{ marginTop: '20px' }} onClick={onCreate}>
            <Plus size={16} /> Create Knowledge Base
          </button>
        </div>
      ) : (
        <div className="kb-grid">
          {knowledgeBases.map((kb) => (
            <div key={kb.id} className="kb-card" onClick={() => onSelect(kb)}>
              <button 
                className="kb-card-delete-btn" 
                onClick={(e) => { e.stopPropagation(); setKbToDelete(kb); }}
                title="Delete Knowledge Base"
              >
                <Trash2 size={16} />
              </button>
              <h3 className="kb-card-name">{kb.name}</h3>
              <p className="kb-card-desc">{kb.description || 'No description'}</p>
              <div className="kb-card-stats">
                <span className="kb-card-stat">
                  <FileText size={12} /> {kb.document_count} documents
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {kbToDelete && (
        <ConfirmDialog
          title="Delete Knowledge Base"
          message={`Are you sure you want to delete "${kbToDelete.name}"? This will permanently delete all its documents and vectors. This cannot be undone.`}
          confirmText="Delete Knowledge Base"
          onConfirm={handleDeleteKBConfirm}
          onCancel={() => setKbToDelete(null)}
        />
      )}
    </div>
  );
}
