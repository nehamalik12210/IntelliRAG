import { useState } from 'react';
import { X } from 'lucide-react';

export default function FeedbackModal({ isOpen, onClose, onSubmit }) {
  const [comment, setComment] = useState('');

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop">
      <div className="modal-content feedback-modal">
        <button className="modal-close" onClick={onClose}>
          <X size={20} />
        </button>
        <h2>Provide Feedback</h2>
        <p>Why was this response not helpful?</p>
        <textarea
          autoFocus
          className="feedback-textarea"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="e.g., The answer hallucinates facts, or the sources are irrelevant..."
          rows={4}
        />
        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button 
            className="btn-primary" 
            onClick={() => {
              onSubmit(comment);
              setComment('');
            }}
          >
            Submit Feedback
          </button>
        </div>
      </div>
    </div>
  );
}
