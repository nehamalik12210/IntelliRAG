import { useState, useRef, useEffect } from 'react';
import { Upload, FileText, Trash2, RotateCw, X } from 'lucide-react';
import { uploadDocument, deleteDocument, retryDocument, deleteKnowledgeBase } from '../../services/api';
import ConfirmDialog from '../ConfirmDialog';

/**
 * Knowledge Base detail view — document list, upload zone, and status management.
 */
export default function KBDetail({ kb, documents, onRefresh, onBack, onKBDeleted }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showKBDeleteConfirm, setShowKBDeleteConfirm] = useState(false);
  const [docToDelete, setDocToDelete] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const isProcessing = documents?.some(doc => 
      ['queued', 'parsing', 'chunking', 'embedding', 'persisting'].includes(doc.status)
    );

    let intervalId;
    if (isProcessing) {
      intervalId = setInterval(() => {
        onRefresh();
      }, 2000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [documents, onRefresh]);

  const handleDrop = async (e) => {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files);
    await uploadFiles(files);
  };

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files);
    await uploadFiles(files);
    e.target.value = '';
  };

  const uploadFiles = async (files) => {
    setUploading(true);
    try {
      for (const file of files) {
        await uploadDocument(kb.id, file);
      }
      onRefresh();
    } catch (err) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDocConfirm = async () => {
    if (!docToDelete) return;
    try {
      await deleteDocument(docToDelete);
      setDocToDelete(null);
      onRefresh();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleDeleteKBConfirm = async () => {
    try {
      await deleteKnowledgeBase(kb.id);
      setShowKBDeleteConfirm(false);
      if (onKBDeleted) onKBDeleted();
    } catch (err) {
      alert(`Delete KB failed: ${err.message}`);
    }
  };

  const handleRetry = async (docId) => {
    try {
      await retryDocument(docId);
      onRefresh();
    } catch (err) {
      alert(`Retry failed: ${err.message}`);
    }
  };

  const getStatusBadge = (status) => {
    const labels = {
      ready: 'Ready',
      error: 'Error',
      queued: 'Queued',
      parsing: 'Parsing',
      chunking: 'Chunking',
      persisting: 'Persisting',
      embedding: 'Embedding',
    };
    const cls = ['ready'].includes(status) ? 'ready'
      : status === 'error' ? 'error'
      : status;
    return <span className={`status-badge ${cls}`}>{labels[status] || status}</span>;
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <button className="btn btn-ghost" onClick={onBack} style={{ marginBottom: '8px' }}>
              ← Back to Knowledge Bases
            </button>
            <h1 className="page-title">{kb.name}</h1>
            <p className="page-subtitle">
              {kb.description || 'No description'}
            </p>
          </div>
          <button 
            className="btn btn-ghost" 
            onClick={() => setShowKBDeleteConfirm(true)}
            style={{ color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Trash2 size={16} /> Delete KB
          </button>
        </div>
      </div>

      {/* Upload Zone */}
      <div
        className={`upload-zone ${dragging ? 'dragging' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="upload-zone-icon">
          <Upload size={48} strokeWidth={1} />
        </div>
        <p className="upload-zone-text">
          {uploading ? 'Uploading...' : 'Drop files here or click to upload'}
        </p>
        <p className="upload-zone-subtext">
          PDF, DOCX, TXT, MD, CSV, PPTX, HTML (Max {kb.max_file_size || 50}MB)
        </p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.md,.csv,.pptx,.html,.htm"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
      </div>

      {/* Document List */}
      {documents && documents.length > 0 && (
        <>
          <h3 style={{ margin: '32px 0 16px', fontSize: 'var(--fs-md)', fontWeight: 600 }}>
            Documents ({documents.length})
          </h3>
          <div className="doc-list">
            {documents.map((doc) => (
              <div key={doc.id} className="doc-item">
                <div className="doc-header">
                  <div className="doc-icon">
                    <FileText size={20} />
                  </div>
                  <div className="doc-info">
                    <div className="doc-name" title={doc.filename}>{doc.filename}</div>
                    <div className="doc-meta">
                      {formatSize(doc.file_size)} · {doc.chunk_count} chunks
                      {doc.error_message && (
                        <div style={{ color: 'var(--error)', marginTop: '4px' }}>
                          {doc.error_message}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {['parsing', 'chunking', 'persisting', 'embedding'].includes(doc.status) && (
                  <div className="progress-bar" style={{ width: '120px', marginLeft: '24px' }}>
                    <div
                      className="progress-fill"
                      style={{ width: doc.chunk_count > 0 ? `${(doc.progress / doc.chunk_count) * 100}%` : '30%' }}
                    />
                  </div>
                )}

                <div className="doc-actions">
                  {getStatusBadge(doc.status)}
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {doc.status === 'error' && (
                      <button className="btn-icon" onClick={() => handleRetry(doc.id)} title="Retry">
                        <RotateCw size={16} />
                      </button>
                    )}
                    <button className="btn-icon" onClick={() => setDocToDelete(doc.id)} title="Delete">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
      {/* Modals */}
      {showKBDeleteConfirm && (
        <ConfirmDialog
          title="Delete Knowledge Base"
          message={`Are you sure you want to delete "${kb.name}"? This will permanently delete all its documents and vectors. This cannot be undone.`}
          confirmText="Delete Knowledge Base"
          onConfirm={handleDeleteKBConfirm}
          onCancel={() => setShowKBDeleteConfirm(false)}
        />
      )}

      {docToDelete && (
        <ConfirmDialog
          title="Delete Document"
          message="Are you sure you want to delete this document? This cannot be undone."
          confirmText="Delete Document"
          onConfirm={handleDeleteDocConfirm}
          onCancel={() => setDocToDelete(null)}
        />
      )}
    </div>
  );
}
