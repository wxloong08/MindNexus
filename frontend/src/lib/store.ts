import { create } from 'zustand';
import { Document, documentApi, chatApi, Message } from './api';

// Note type matching MindNexus.jsx
export interface Note {
    id: string;
    title: string;
    content: string;
    tags: string[];
    type: 'markdown' | 'pdf' | 'text';
    createdAt: string;
}

// Chat message type
export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    sources?: string[];
    suggestions?: string[];
}

// AI Link for knowledge graph
export interface AiLink {
    source: string;
    target: string;
    type: 'ai';
}

// Flashcard type
export interface Flashcard {
    front: string;
    back: string;
}

// Brainstorm idea type
export interface BrainstormIdea {
    title: string;
    desc: string;
}

interface AppState {
    // Tab state
    activeTab: 'notes' | 'graph' | 'chat';
    setActiveTab: (tab: 'notes' | 'graph' | 'chat') => void;

    // Notes state
    notes: Note[];
    selectedNoteId: string | null;
    searchQuery: string;
    viewMode: 'edit' | 'preview';

    setNotes: (notes: Note[]) => void;
    setSelectedNoteId: (id: string | null) => void;
    setSearchQuery: (query: string) => void;
    setViewMode: (mode: 'edit' | 'preview') => void;

    // Note operations
    createNote: (title?: string, content?: string) => void;
    updateNote: (id: string, updates: Partial<Note>) => void;
    deleteNote: (id: string) => void;

    // Chat state
    messages: ChatMessage[];
    isTyping: boolean;
    conversationId: string | null;

    setMessages: (messages: ChatMessage[]) => void;
    addMessage: (message: ChatMessage) => void;
    setIsTyping: (isTyping: boolean) => void;
    setConversationId: (id: string | null) => void;

    // AI feature states
    suggestedTags: string[];
    isSuggestingTags: boolean;
    isSummarizing: boolean;
    isContinuing: boolean;
    isExtractingTasks: boolean;
    isPolishing: boolean;
    isTranslating: boolean;
    isGeneratingImage: boolean;
    isCritiquing: boolean;
    isAnalyzingGraph: boolean;
    isBrainstorming: boolean;
    isGeneratingFlashcards: boolean;

    setSuggestedTags: (tags: string[]) => void;
    setIsSuggestingTags: (loading: boolean) => void;
    setIsSummarizing: (loading: boolean) => void;
    setIsContinuing: (loading: boolean) => void;
    setIsExtractingTasks: (loading: boolean) => void;
    setIsPolishing: (loading: boolean) => void;
    setIsTranslating: (loading: boolean) => void;
    setIsGeneratingImage: (loading: boolean) => void;
    setIsCritiquing: (loading: boolean) => void;
    setIsAnalyzingGraph: (loading: boolean) => void;
    setIsBrainstorming: (loading: boolean) => void;
    setIsGeneratingFlashcards: (loading: boolean) => void;

    // Knowledge graph AI links
    aiLinks: AiLink[];
    setAiLinks: (links: AiLink[]) => void;

    // Brainstorm ideas
    brainstormIdeas: BrainstormIdea[];
    setBrainstormIdeas: (ideas: BrainstormIdea[]) => void;

    // Flashcards
    flashcards: Flashcard[];
    showFlashcards: boolean;
    setFlashcards: (cards: Flashcard[]) => void;
    setShowFlashcards: (show: boolean) => void;

    // Settings modal
    showSettings: boolean;
    setShowSettings: (show: boolean) => void;
    resetToInitial: () => void;

    // Computed values
    filteredNotes: () => Note[];
    filteredMessages: () => ChatMessage[];
    activeNote: () => Note | undefined;

    // Sync with backend
    syncNotesFromBackend: () => Promise<void>;
    saveNoteToBackend: (note: Note) => Promise<void>;
}

// Generate unique ID (only called on client side actions)
const generateId = () => Math.random().toString(36).substr(2, 9);

// Initial notes with FIXED timestamps to avoid hydration mismatch
const INITIAL_NOTES: Note[] = [
    {
        id: '1',
        title: '关于 React Hooks 的学习',
        content: '# React Hooks 学习笔记\n\nReact Hooks 是 React 16.8 的新增特性。它可以让你在不编写 class 的情况下使用 state 以及其他的 React 特性。\n\n## 常用 Hooks\n\n- **useState**: 用于管理组件状态\n- **useEffect**: 用于处理副作用\n- **useContext**: 用于跨组件共享状态\n\n> 自定义 Hooks 可以复用状态逻辑，这是非常强大的功能。\n\n```javascript\nconst [count, setCount] = useState(0);\n```',
        tags: ['React', 'Frontend', 'JavaScript'],
        type: 'markdown',
        createdAt: '2024-12-01T10:00:00.000Z',
    },
    {
        id: '2',
        title: '2024年人工智能趋势报告',
        content: '# 2024 AI 趋势\n\n报告指出，大语言模型 (LLM) 将继续主导 AI 领域。\n\n## 核心技术\n\n1. **RAG (检索增强生成)**: 解决了幻觉问题，成为企业落地的首选。\n2. **多模态模型**: 处理图像、视频是重点发展方向。\n3. **Agent (智能体)**: 将具备更强的规划能力。',
        tags: ['AI', 'LLM', 'RAG', 'Report'],
        type: 'pdf',
        createdAt: '2024-12-10T14:30:00.000Z',
    },
    {
        id: '3',
        title: '知识图谱基础',
        content: '# 知识图谱 (Knowledge Graph)\n\n这是一种用图模型来描述真实世界中万物之间关系的技术。\n\n- **节点**: 代表实体\n- **边**: 代表关系\n\n它在搜索引擎、推荐系统中有广泛应用。结合 `LLM` 可以增强推理能力。',
        tags: ['AI', 'Graph', 'Data'],
        type: 'markdown',
        createdAt: '2024-12-15T09:00:00.000Z',
    },
    {
        id: '4',
        title: '项目 Alpha 架构设计',
        content: '# 系统架构\n\n系统采用微服务架构。\n\n## 技术栈\n\n- 前端: **Next.js**\n- 后端: **Python FastAPI**\n- 数据库: PostgreSQL (关系型) + Neo4j (图数据库)',
        tags: ['Project', 'Architecture', 'Backend', 'Frontend'],
        type: 'markdown',
        createdAt: '2024-12-20T16:00:00.000Z',
    },
];

const INITIAL_MESSAGE: ChatMessage = {
    role: 'assistant',
    content: '你好！我是你的个人知识助手 MindNexus。我已连接到 AI 模型。你可以问我关于你笔记中的任何问题，让我在聊天中考考你，或者帮你总结文档。',
};

export const useAppStore = create<AppState>((set, get) => ({
    // Tab state
    activeTab: 'notes',
    setActiveTab: (tab) => set({ activeTab: tab }),

    // Notes state
    notes: INITIAL_NOTES,
    selectedNoteId: null,
    searchQuery: '',
    viewMode: 'edit',

    setNotes: (notes) => set({ notes }),
    setSelectedNoteId: (id) => set({ selectedNoteId: id }),
    setSearchQuery: (query) => set({ searchQuery: query }),
    setViewMode: (mode) => set({ viewMode: mode }),

    // Note operations
    createNote: (title = '未命名笔记', content = '') => {
        const newNote: Note = {
            id: generateId(),
            title,
            content,
            tags: [],
            type: 'markdown',
            createdAt: new Date().toISOString(),
        };
        set((state) => ({
            notes: [newNote, ...state.notes],
            selectedNoteId: newNote.id,
            activeTab: 'notes',
            viewMode: 'edit',
            suggestedTags: [],
            brainstormIdeas: [],
            flashcards: [],
            showFlashcards: false,
        }));
    },

    updateNote: (id, updates) => {
        set((state) => ({
            notes: state.notes.map((n) => (n.id === id ? { ...n, ...updates } : n)),
        }));
    },

    deleteNote: (id) => {
        set((state) => ({
            notes: state.notes.filter((n) => n.id !== id),
            selectedNoteId: state.selectedNoteId === id ? null : state.selectedNoteId,
        }));
    },

    // Chat state
    messages: [INITIAL_MESSAGE],
    isTyping: false,
    conversationId: null,

    setMessages: (messages) => set({ messages }),
    addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
    setIsTyping: (isTyping) => set({ isTyping }),
    setConversationId: (id) => set({ conversationId: id }),

    // AI feature states
    suggestedTags: [],
    isSuggestingTags: false,
    isSummarizing: false,
    isContinuing: false,
    isExtractingTasks: false,
    isPolishing: false,
    isTranslating: false,
    isGeneratingImage: false,
    isCritiquing: false,
    isAnalyzingGraph: false,
    isBrainstorming: false,
    isGeneratingFlashcards: false,

    setSuggestedTags: (tags) => set({ suggestedTags: tags }),
    setIsSuggestingTags: (loading) => set({ isSuggestingTags: loading }),
    setIsSummarizing: (loading) => set({ isSummarizing: loading }),
    setIsContinuing: (loading) => set({ isContinuing: loading }),
    setIsExtractingTasks: (loading) => set({ isExtractingTasks: loading }),
    setIsPolishing: (loading) => set({ isPolishing: loading }),
    setIsTranslating: (loading) => set({ isTranslating: loading }),
    setIsGeneratingImage: (loading) => set({ isGeneratingImage: loading }),
    setIsCritiquing: (loading) => set({ isCritiquing: loading }),
    setIsAnalyzingGraph: (loading) => set({ isAnalyzingGraph: loading }),
    setIsBrainstorming: (loading) => set({ isBrainstorming: loading }),
    setIsGeneratingFlashcards: (loading) => set({ isGeneratingFlashcards: loading }),

    // Knowledge graph AI links
    aiLinks: [],
    setAiLinks: (links) => set({ aiLinks: links }),

    // Brainstorm ideas
    brainstormIdeas: [],
    setBrainstormIdeas: (ideas) => set({ brainstormIdeas: ideas }),

    // Flashcards
    flashcards: [],
    showFlashcards: false,
    setFlashcards: (cards) => set({ flashcards: cards }),
    setShowFlashcards: (show) => set({ showFlashcards: show }),

    // Settings modal
    showSettings: false,
    setShowSettings: (show) => set({ showSettings: show }),
    resetToInitial: () => {
        set({
            notes: INITIAL_NOTES,
            selectedNoteId: null,
            messages: [INITIAL_MESSAGE],
            showSettings: false,
            aiLinks: [],
            brainstormIdeas: [],
            flashcards: [],
            showFlashcards: false,
            suggestedTags: [],
        });
    },

    // Computed values
    filteredNotes: () => {
        const { notes, searchQuery } = get();
        if (!searchQuery) return notes;
        const query = searchQuery.toLowerCase();
        return notes.filter(
            (note) =>
                note.title.toLowerCase().includes(query) ||
                note.content.toLowerCase().includes(query) ||
                note.tags.some((tag) => tag.toLowerCase().includes(query))
        );
    },

    // Filtered messages for chat search - shows Q&A pairs together
    filteredMessages: () => {
        const { messages, searchQuery } = get();
        if (!searchQuery) return messages;
        const query = searchQuery.toLowerCase();

        // Build a set of indices that match or are adjacent to matches (for Q&A pairs)
        const matchIndices = new Set<number>();

        messages.forEach((msg, idx) => {
            const matches =
                msg.content.toLowerCase().includes(query) ||
                (msg.sources && msg.sources.some((s) => s.toLowerCase().includes(query)));

            if (matches) {
                matchIndices.add(idx);
                // If user message matches, also include the next assistant message
                if (msg.role === 'user' && idx + 1 < messages.length) {
                    matchIndices.add(idx + 1);
                }
                // If assistant message matches, also include the previous user message
                if (msg.role === 'assistant' && idx > 0 && messages[idx - 1].role === 'user') {
                    matchIndices.add(idx - 1);
                }
            }
        });

        return messages.filter((_, idx) => matchIndices.has(idx));
    },

    activeNote: () => {
        const { notes, selectedNoteId } = get();
        return notes.find((n) => n.id === selectedNoteId);
    },

    // Sync with backend
    syncNotesFromBackend: async () => {
        try {
            const response = await documentApi.list(0, 100);
            const notes: Note[] = response.documents.map((doc) => ({
                id: doc.id,
                title: doc.title,
                content: doc.content,
                tags: doc.tags,
                type: doc.doc_type === 'pdf' ? 'pdf' : 'markdown',
                createdAt: doc.created_at,
            }));
            set({ notes });
        } catch (error) {
            console.error('Failed to sync notes from backend:', error);
        }
    },

    saveNoteToBackend: async (note: Note) => {
        try {
            // Check if note exists in backend
            const existing = await documentApi.get(note.id).catch(() => null);
            if (existing) {
                await documentApi.update(note.id, {
                    title: note.title,
                    content: note.content,
                    tags: note.tags,
                });
            } else {
                await documentApi.create({
                    title: note.title,
                    content: note.content,
                    doc_type: note.type === 'pdf' ? 'pdf' : 'markdown',
                    tags: note.tags,
                    auto_index: true,
                });
            }
        } catch (error) {
            console.error('Failed to save note to backend:', error);
        }
    },
}));
