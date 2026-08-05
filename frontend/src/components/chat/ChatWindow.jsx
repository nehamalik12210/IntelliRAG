import { useRef, useEffect, useState } from 'react';
import { MessageSquare } from 'lucide-react';
import MessageBubble from './MessageBubble';
import InputBar from './InputBar';
import SourcePanel from './SourcePanel';
import { useChat } from '../../hooks/useChat';
import { listDocuments } from '../../services/api';

/**
 * Main chat window — streaming messages, source panel, KB selector.
 */
export default function ChatWindow({ knowledgeBases, selectedKb, onKbChange, activeConversation, onChatUpdated }) {
  const {
    messages,
    isStreaming,
    sources,
    metadata,
    sendMessage,
    stopStreaming,
    handleFeedback,
    loadConversation,
    newChat,
  } = useChat(onChatUpdated);

  const [showSources, setShowSources] = useState(false);
  const [panelSources, setPanelSources] = useState(null);
  const [panelMetadata, setPanelMetadata] = useState(null);
  const [activeSourceIndex, setActiveSourceIndex] = useState(null);
  const messagesEndRef = useRef(null);
  const [chatDocuments, setChatDocuments] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState(null); // null = all docs

  // Fetch documents for target document filtering when kb changes
  useEffect(() => {
    if (selectedKb) {
      listDocuments(selectedKb)
        .then((data) => setChatDocuments(data.documents || []))
        .catch(console.error);
    } else {
      setChatDocuments([]);
    }
    setSelectedDocIds(null);
  }, [selectedKb]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  // Show source panel when sources arrive
  useEffect(() => {
    if (sources && sources.length > 0) {
      setPanelSources(sources);
      setPanelMetadata(metadata);
      setShowSources(true);
      setActiveSourceIndex(null);
    }
  }, [sources, metadata]);

  // Load conversation when activeConversation changes
  useEffect(() => {
    if (activeConversation) {
      loadConversation(activeConversation.id, activeConversation.messages);
    } else {
      newChat();
      setShowSources(false);
    }
  }, [activeConversation]);

  const handleSend = (text, provider, model) => {
    sendMessage(text, selectedKb, selectedDocIds, provider, model);
  };

  return (
    <div className="chat-container">
      <div className="chat-main">
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-empty-state">
              <div className="chat-empty-state-icon">
                <MessageSquare size={48} strokeWidth={1} />
              </div>
              <h3 className="chat-empty-state-title">Start a conversation</h3>
              <p className="chat-empty-state-text">
                Ask questions about your documents. Select a knowledge base to get started,
                or chat freely without one.
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                sources={msg.sources}
                onFeedback={handleFeedback}
                onSourceClick={(source, index) => {
                  setPanelSources(msg.sources);
                  setPanelMetadata(null);
                  setShowSources(true);
                  setActiveSourceIndex(index);
                }}
              />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <InputBar
          onSend={handleSend}
          isStreaming={isStreaming}
          onStop={stopStreaming}
          knowledgeBases={knowledgeBases}
          selectedKb={selectedKb}
          onKbChange={onKbChange}
          documents={chatDocuments}
          selectedDocIds={selectedDocIds}
          onDocumentChange={setSelectedDocIds}
        />
      </div>

      {showSources && panelSources && panelSources.length > 0 && (
        <SourcePanel 
          sources={panelSources} 
          metadata={panelMetadata} 
          activeSourceIndex={activeSourceIndex}
          onClose={() => setShowSources(false)} 
        />
      )}
    </div>
  );
}

