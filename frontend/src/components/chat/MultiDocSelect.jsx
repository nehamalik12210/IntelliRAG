import { useState, useRef, useEffect } from 'react';
import { ChevronDown, ChevronUp, Check, FileText } from 'lucide-react';

/**
 * Multi-select document dropdown.
 * - User can select 1 or more documents, or "All Documents" (default).
 * - If more than 1 doc selected, shows "X documents selected".
 * - If exactly 1 doc selected, shows its filename.
 * - If none/all selected, shows "All Documents".
 */
export default function MultiDocSelect({ documents, selectedDocIds, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  if (!documents || documents.length === 0) return null;

  const allSelected = !selectedDocIds || selectedDocIds.length === 0;
  const count = selectedDocIds ? selectedDocIds.length : 0;

  // Determine display label
  let displayLabel = 'All Documents';
  if (count === 1) {
    const doc = documents.find((d) => d.id === selectedDocIds[0]);
    displayLabel = doc ? doc.filename : '1 document selected';
  } else if (count > 1) {
    displayLabel = `${count} documents selected`;
  }

  const toggleDoc = (docId) => {
    if (!selectedDocIds || selectedDocIds.length === 0) {
      // Currently "all" — clicking one doc selects only that one
      onChange([docId]);
    } else if (selectedDocIds.includes(docId)) {
      // Deselect this doc
      const newIds = selectedDocIds.filter((id) => id !== docId);
      onChange(newIds.length > 0 ? newIds : null); // If none left, revert to "all"
    } else {
      // Add this doc
      onChange([...selectedDocIds, docId]);
    }
  };

  const selectAll = () => {
    onChange(null);
    setIsOpen(false);
  };

  return (
    <div className="custom-select-container" ref={containerRef}>
      <div
        className="custom-select-trigger"
        onClick={() => setIsOpen(!isOpen)}
      >
        <FileText size={13} style={{ flexShrink: 0, opacity: 0.7 }} />
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {displayLabel}
        </span>
        {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </div>

      {isOpen && (
        <div className="custom-select-dropdown" style={{ minWidth: '200px' }}>
          {/* "All Documents" option */}
          <div
            className={`custom-select-option ${allSelected ? 'selected' : ''}`}
            onClick={selectAll}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <span style={{
              width: '16px', height: '16px', borderRadius: '3px',
              border: `2px solid ${allSelected ? 'var(--accent-primary)' : 'var(--border)'}`,
              background: allSelected ? 'var(--accent-primary)' : 'transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              {allSelected && <Check size={10} style={{ color: 'var(--text-inverse)' }} />}
            </span>
            All Documents
          </div>

          {/* Individual documents */}
          {documents.map((doc) => {
            const isChecked = selectedDocIds && selectedDocIds.includes(doc.id);
            return (
              <div
                key={doc.id}
                className={`custom-select-option ${isChecked ? 'selected' : ''}`}
                onClick={(e) => { e.stopPropagation(); toggleDoc(doc.id); }}
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <span style={{
                  width: '16px', height: '16px', borderRadius: '3px',
                  border: `2px solid ${isChecked ? 'var(--accent-primary)' : 'var(--border)'}`,
                  background: isChecked ? 'var(--accent-primary)' : 'transparent',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  {isChecked && <Check size={10} style={{ color: 'var(--text-inverse)' }} />}
                </span>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {doc.filename}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
