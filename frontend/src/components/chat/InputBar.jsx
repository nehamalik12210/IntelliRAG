import { useState, useRef, useEffect } from 'react';
import { Send, Square, Cpu } from 'lucide-react';
import CustomSelect from './CustomSelect';
import MultiDocSelect from './MultiDocSelect';
import { listModels } from '../../services/api';

/**
 * Chat input bar with auto-resizing textarea, KB selector, multi-doc selector, model selector, and send/stop buttons.
 */
export default function InputBar({ onSend, isStreaming, onStop, knowledgeBases, selectedKb, onKbChange, documents, selectedDocIds, onDocumentChange }) {
  const [text, setText] = useState('');
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, [text]);

  // Fetch available models on mount
  useEffect(() => {
    listModels()
      .then((data) => {
        setModels(data.models || []);
      })
      .catch(() => {});
  }, []);

  const handleSend = () => {
    if (!text.trim() || isStreaming) return;
    const [provider, model] = selectedModel ? selectedModel.split('/') : [null, null];
    onSend(text.trim(), provider, model);
    setText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input-area">
      <div className="chat-input-wrapper">
        <textarea
          ref={textareaRef}
          className="chat-input"
          placeholder="Ask a question about your documents..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={isStreaming}
        />
        {isStreaming ? (
          <button className="send-btn" onClick={onStop} title="Stop generating">
            <Square size={16} />
          </button>
        ) : (
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!text.trim()}
            title="Send message"
          >
            <Send size={16} />
          </button>
        )}
      </div>
      <div className="chat-input-meta">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {knowledgeBases && knowledgeBases.length > 0 ? (
            <CustomSelect
              options={knowledgeBases.map((kb) => ({ value: kb.id, label: kb.name }))}
              value={selectedKb || ''}
              onChange={(val) => {
                onKbChange(val || null);
                onDocumentChange(null);
              }}
              placeholder="No knowledge base"
            />
          ) : (
            <span>No knowledge bases created yet</span>
          )}
          
          {selectedKb && documents && documents.length > 0 && (
            <MultiDocSelect
              documents={documents}
              selectedDocIds={selectedDocIds}
              onChange={onDocumentChange}
            />
          )}
          {models.length > 0 && (
            <CustomSelect
              options={models.map((m) => ({ value: `${m.provider}/${m.id}`, label: `${m.name}` }))}
              value={selectedModel}
              onChange={setSelectedModel}
              placeholder="Default model"
              icon={<Cpu size={13} />}
            />
          )}
        </div>
        <span>Press Enter to send, Shift+Enter for new line</span>
      </div>
    </div>
  );
}

