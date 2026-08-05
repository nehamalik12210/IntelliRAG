import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { ThumbsUp, ThumbsDown, FileText, Copy, Check } from 'lucide-react';
import FeedbackModal from './FeedbackModal';

/**
 * Individual chat message bubble with markdown rendering,
 * syntax-highlighted code blocks, source citation chips, and feedback buttons.
 */
export default function MessageBubble({ message, sources, onFeedback, onSourceClick }) {
  const isUser = message.role === 'user';
  const isError = message.isError;
  const [copiedBlock, setCopiedBlock] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleCopy = (code, index) => {
    navigator.clipboard.writeText(code);
    setCopiedBlock(index);
    setTimeout(() => setCopiedBlock(null), 2000);
  };

  // Custom code block renderer with syntax highlighting
  let codeBlockIndex = 0;
  const components = {
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      const code = String(children).replace(/\n$/, '');
      const blockIdx = codeBlockIndex++;

      if (!inline && (match || code.includes('\n'))) {
        const language = match ? match[1] : 'text';
        return (
          <div className="code-block-wrapper">
            <div className="code-block-header">
              <span className="code-block-lang">{language}</span>
              <button
                className="code-copy-btn"
                onClick={() => handleCopy(code, blockIdx)}
                title="Copy code"
              >
                {copiedBlock === blockIdx ? <Check size={13} /> : <Copy size={13} />}
                {copiedBlock === blockIdx ? 'Copied' : 'Copy'}
              </button>
            </div>
            <SyntaxHighlighter
              style={oneDark}
              language={language}
              PreTag="div"
              customStyle={{
                margin: 0,
                borderRadius: '0 0 8px 8px',
                fontSize: '13px',
                background: '#1e1e1e',
              }}
              {...props}
            >
              {code}
            </SyntaxHighlighter>
          </div>
        );
      }
      return (
        <code className="inline-code" {...props}>
          {children}
        </code>
      );
    },
  };

  return (
    <div className={`message ${isUser ? 'user-message' : 'assistant-message'}`}>
      <div className={`message-avatar ${message.role}`}>
        {isUser ? 'U' : <img src="/logo.png" alt="AI" style={{ width: '100%', height: '100%', borderRadius: 'inherit', objectFit: 'cover' }} />}
      </div>
      <div className="message-body">
        <div className="message-content" style={isError ? { color: 'var(--error)' } : undefined}>
          {message.isStreaming && !message.content ? (
            <div className="typing-indicator">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          ) : (
            <div className={`markdown-wrapper ${message.isStreaming ? 'streaming' : ''}`}>
              <ReactMarkdown components={isUser ? undefined : components}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Source citation chips */}
        {!isUser && sources && sources.length > 0 && (
          <div className="message-sources">
            {sources.map((source, i) => (
              <button
                key={i}
                className="source-chip"
                onClick={() => onSourceClick && onSourceClick(source, i)}
                title={`${source.filename} - Page ${source.page_number}`}
              >
                <FileText size={11} />
                {source.filename}
                {source.page_number > 0 && ` p.${source.page_number}`}
              </button>
            ))}
          </div>
        )}

        {/* Feedback buttons */}
        {!isUser && !message.isStreaming && message.content && (
          <div className="message-actions">
            <button
              className={`feedback-btn ${message.feedback === 'thumbs_up' ? 'active' : ''}`}
              onClick={() => onFeedback(message.id, message.feedback === 'thumbs_up' ? null : 'thumbs_up')}
              title="Good response"
            >
              <ThumbsUp size={14} />
            </button>
            <button
              className={`feedback-btn ${message.feedback === 'thumbs_down' ? 'active' : ''}`}
              onClick={() => {
                if (message.feedback === 'thumbs_down') {
                  onFeedback(message.id, null);
                } else {
                  setIsModalOpen(true);
                }
              }}
              title="Bad response"
            >
              <ThumbsDown size={14} />
            </button>
          </div>
        )}
      </div>

      <FeedbackModal 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={(comment) => {
          onFeedback(message.id, 'thumbs_down', comment);
          setIsModalOpen(false);
        }}
      />
    </div>
  );
}
