import { useState, useEffect, useCallback, useRef } from 'react';
import {
  MessageSquare, Database, Plus, Sun, Moon, Trash2, Settings, Pencil, Check, X as XIcon, Search, Activity
} from 'lucide-react';
import ChatWindow from './components/chat/ChatWindow';
import KBList from './components/kb/KBList';
import KBDetail from './components/kb/KBDetail';
import KBCreateDialog from './components/kb/KBCreateDialog';
import SettingsPanel from './components/settings/SettingsPanel';
import EvalDashboard from './components/eval/EvalDashboard';
import {
  listKnowledgeBases, createKnowledgeBase, listDocuments,
  listConversations, getMessages, deleteConversation, renameConversation,
} from './services/api';
import './index.css';

/**
 * IntelliRAG — Main Application
 */
export default function App() {
  // Navigation state
  const [page, setPage] = useState('chat'); // chat | kb | kb-detail
  const [theme, setTheme] = useState(() =>
    localStorage.getItem('theme') || 'dark'
  );

  // Data state
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [selectedKb, setSelectedKb] = useState(null);
  const [selectedKbDetail, setSelectedKbDetail] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [showCreateKB, setShowCreateKB] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [editingConvoId, setEditingConvoId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const editInputRef = useRef(null);

  // Theme management
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'));

  // Fetch data
  const fetchKBs = useCallback(async () => {
    try {
      const data = await listKnowledgeBases();
      setKnowledgeBases(data.knowledge_bases || []);
    } catch (err) {
      console.error('Failed to fetch KBs:', err);
    }
  }, []);

  const fetchConversations = useCallback(async () => {
    try {
      const data = await listConversations();
      setConversations(data.conversations || []);
    } catch (err) {
      console.error('Failed to fetch conversations:', err);
    }
  }, []);

  const fetchDocuments = useCallback(async (kbId) => {
    try {
      const data = await listDocuments(kbId);
      setDocuments(data.documents || []);
    } catch (err) {
      console.error('Failed to fetch docs:', err);
    }
  }, []);

  useEffect(() => {
    fetchKBs();
    fetchConversations();
  }, [page, fetchKBs, fetchConversations]);

  useEffect(() => {
    if (editingConvoId && editInputRef.current) {
      editInputRef.current.focus();
    }
  }, [editingConvoId]);

  // KB handlers
  const handleCreateKB = async (data) => {
    await createKnowledgeBase(data);
    fetchKBs();
  };

  const handleSelectKBDetail = (kb) => {
    setSelectedKbDetail(kb);
    setPage('kb-detail');
    fetchDocuments(kb.id);
  };

  // Conversation handlers
  const handleSelectConversation = async (convo) => {
    if (editingConvoId === convo.id) return;
    try {
      const data = await getMessages(convo.id);
      setActiveConversation({
        id: convo.id,
        messages: (data.messages || []).map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          sources: m.sources,
          feedback: m.feedback,
        })),
      });
      setSelectedKb(convo.kb_id);
      setPage('chat');
    } catch (err) {
      console.error('Failed to load conversation:', err);
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await deleteConversation(id);
      fetchConversations();
      if (activeConversation?.id === id) {
        setActiveConversation(null);
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const startEditing = (e, convo) => {
    e.stopPropagation();
    setEditingConvoId(convo.id);
    setEditTitle(convo.title);
  };

  const handleRename = async (e, id) => {
    e.stopPropagation();
    if (!editTitle.trim()) {
      setEditingConvoId(null);
      return;
    }
    try {
      await renameConversation(id, editTitle);
      fetchConversations();
    } catch (err) {
      console.error('Failed to rename:', err);
    }
    setEditingConvoId(null);
  };

  const handleNewChat = () => {
    setActiveConversation(null);
    setPage('chat');
  };

  const filteredConversations = conversations.filter(c => 
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="app-layout">
      {/* ── Sidebar ── */}
      <nav className="sidebar">
        <div className="sidebar-header">
          <img src="/logo.png" alt="IntelliRAG Logo" style={{ width: '28px', height: '28px', marginRight: '12px', borderRadius: '4px' }} />
          <span className="sidebar-title">IntelliRAG</span>
        </div>

        <div className="sidebar-nav">
          <button
            className="nav-item"
            onClick={handleNewChat}
          >
            <Plus size={18} /> New Chat
          </button>
          <button
            className={`nav-item ${page === 'kb' || page === 'kb-detail' ? 'active' : ''}`}
            onClick={() => setPage('kb')}
          >
            <Database size={18} /> Knowledge Bases
          </button>
          <button
            className={`nav-item ${page === 'eval' ? 'active' : ''}`}
            onClick={() => setPage('eval')}
          >
            <Activity size={18} /> Evaluations
          </button>
        </div>

        <div className="sidebar-section-title">Recent Chats</div>
        
        <div style={{ padding: '0 12px 10px' }}>
          <div className="search-input-wrapper">
            <Search size={14} className="search-icon" />
            <input 
              type="text" 
              placeholder="Search chats..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="chat-search-input"
            />
          </div>
        </div>

        <div className="sidebar-conversations">
          {filteredConversations.length === 0 && conversations.length > 0 && (
            <div style={{ padding: '12px', fontSize: '13px', color: 'var(--text-tertiary)', textAlign: 'center' }}>No chats found</div>
          )}
          {filteredConversations.map((c) => (
            <div
              key={c.id}
              className={`conversation-item ${page === 'chat' && activeConversation?.id === c.id ? 'active' : ''}`}
              onClick={() => handleSelectConversation(c)}
            >
              
              {editingConvoId === c.id ? (
                <input
                  ref={editInputRef}
                  className="rename-input"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleRename(e, c.id);
                    if (e.key === 'Escape') setEditingConvoId(null);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  style={{
                    flex: 1, 
                    background: 'transparent', 
                    border: 'none', 
                    outline: 'none',
                    color: 'var(--text-primary)', 
                    padding: '0',
                    fontSize: 'inherit',
                    fontFamily: 'inherit',
                    minWidth: 0
                  }}
                />
              ) : (
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {c.title}
                </span>
              )}

              <div className="convo-actions" style={{ display: 'flex', gap: '2px' }}>
                {editingConvoId === c.id ? (
                  <>
                    <button className="btn-icon" style={{ padding: 2, opacity: 1 }} onClick={(e) => handleRename(e, c.id)}>
                      <Check size={12} color="var(--success)" />
                    </button>
                    <button className="btn-icon" style={{ padding: 2, opacity: 1 }} onClick={(e) => { e.stopPropagation(); setEditingConvoId(null); }}>
                      <XIcon size={12} />
                    </button>
                  </>
                ) : (
                  <>
                    <button className="btn-icon" style={{ padding: 2 }} onClick={(e) => startEditing(e, c)}>
                      <Pencil size={12} />
                    </button>
                    <button className="btn-icon" style={{ padding: 2 }} onClick={(e) => { e.stopPropagation(); handleDeleteConversation(c.id); }}>
                      <Trash2 size={12} />
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </nav>

      {/* ── Main Content ── */}
      <div className="main-content">
        {/* Header */}
        <header className="header">
          <div className="header-left">
            <h2 className="header-title">
              {page === 'chat' ? 'Chat' : page === 'kb' ? 'Knowledge Bases' : selectedKbDetail?.name || ''}
            </h2>
          </div>
          <div className="header-right">
            <button className="btn-icon" onClick={() => setShowSettings(true)} title="Retrieval settings">
              <Settings size={18} />
            </button>
            <div className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
              <Moon size={14} className="theme-icon moon" />
              <Sun size={14} className="theme-icon sun" />
              <div className="theme-toggle-knob" />
            </div>
          </div>
        </header>

        {/* Page Content */}
        {page === 'chat' && (
          <ChatWindow
            knowledgeBases={knowledgeBases}
            selectedKb={selectedKb}
            onKbChange={setSelectedKb}
            activeConversation={activeConversation}
            onChatUpdated={fetchConversations}
          />
        )}

        {page === 'kb' && (
          <KBList
            knowledgeBases={knowledgeBases}
            onSelect={handleSelectKBDetail}
            onCreate={() => setShowCreateKB(true)}
            onKBDeleted={fetchKBs}
          />
        )}

        {page === 'kb-detail' && selectedKbDetail && (
          <KBDetail
            kb={selectedKbDetail}
            documents={documents}
            onRefresh={() => fetchDocuments(selectedKbDetail.id)}
            onBack={() => { setPage('kb'); setSelectedKbDetail(null); }}
            onKBDeleted={() => {
              fetchKBs();
              setPage('kb');
              setSelectedKbDetail(null);
            }}
          />
        )}

        {page === 'eval' && (
          <EvalDashboard />
        )}
      </div>

      {/* ── Modals ── */}
      {showCreateKB && (
        <KBCreateDialog
          onClose={() => setShowCreateKB(false)}
          onCreate={handleCreateKB}
        />
      )}
      {showSettings && (
        <SettingsPanel onClose={() => setShowSettings(false)} />
      )}
    </div>
  );
}
