import { useState, useCallback, useRef } from 'react';
import { streamChat, submitFeedback } from '../services/api';

/**
 * Chat state management hook with SSE streaming support.
 */
export function useChat(onChatUpdated) {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sources, setSources] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const controllerRef = useRef(null);

  const sendMessage = useCallback((text, kbId, documentIds, provider, model) => {
    // Add user message
    const userMsg = { id: Date.now().toString(), role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);
    setSources([]);

    // Prepare assistant message placeholder
    const assistantId = (Date.now() + 1).toString();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: 'assistant', content: '', isStreaming: true },
    ]);

    const payload = {
      message: text,
      conversation_id: conversationId,
      kb_id: kbId || null,
      document_ids: documentIds || null,
      provider: provider || null,
      model: model || null,
    };

    controllerRef.current = streamChat(
      payload,
      // onToken
      (token) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: m.content + token } : m
          )
        );
      },
      // onSources
      (sourcesData) => {
        setSources(sourcesData);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, sources: sourcesData } : m
          )
        );
      },
      // onDone
      (done) => {
        setIsStreaming(false);
        setConversationId(done.conversation_id);
        setMetadata(done);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, id: done.message_id, isStreaming: false }
              : m
          )
        );
        if (onChatUpdated) onChatUpdated();
      },
      // onError
      (error) => {
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: `Error: ${error}`, isStreaming: false, isError: true }
              : m
          )
        );
      }
    );
  }, [conversationId]);

  const stopStreaming = useCallback(() => {
    if (controllerRef.current) {
      controllerRef.current.abort();
      controllerRef.current = null;
    }
    setIsStreaming(false);
    setMessages((prev) =>
      prev.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m))
    );
  }, []);

  const handleFeedback = useCallback(async (messageId, feedback, comment) => {
    try {
      await submitFeedback(messageId, feedback, comment);
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, feedback } : m))
      );
    } catch (err) {
      console.error('Feedback failed:', err);
    }
  }, []);

  const loadConversation = useCallback((convoId, existingMessages) => {
    setConversationId(convoId);
    setMessages(existingMessages || []);
    setSources([]);
  }, []);

  const newChat = useCallback(() => {
    setConversationId(null);
    setMessages([]);
    setSources([]);
    setMetadata(null);
  }, []);

  return {
    messages,
    isStreaming,
    sources,
    conversationId,
    metadata,
    sendMessage,
    stopStreaming,
    handleFeedback,
    loadConversation,
    newChat,
  };
}
