import axios, { AxiosInstance } from 'axios';

// API Base URL - empty string for production (relative path), localhost:8000 for dev
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Types
export interface Document {
    id: string;
    title: string;
    content: string;
    doc_type: string;
    status: string;
    file_path?: string;
    file_size?: number;
    word_count?: number;
    outgoing_links: string[];
    incoming_links: string[];
    tags: string[];
    summary?: string;
    created_at: string;
    updated_at: string;
    indexed_at?: string;
}

export interface DocumentCreate {
    title: string;
    content: string;
    doc_type?: string;
    tags?: string[];
    auto_index?: boolean;
}

export interface DocumentUpdate {
    title?: string;
    content?: string;
    tags?: string[];
    reindex?: boolean;
}

export interface Conversation {
    id: string;
    title: string;
    created_at: string;
    updated_at: string;
}

export interface Message {
    id: string;
    conversation_id: string;
    role: string;
    content: string;
    retrieved_chunks?: string[];
    model_used?: string;
    tokens_used?: number;
    created_at: string;
}

export interface ChatRequest {
    message: string;
    use_rag?: boolean;
    model?: string;
    stream?: boolean;
}

export interface SearchResult {
    id: string;
    content: string;
    score: number;
    metadata?: Record<string, unknown>;
    document?: Document;
}

export interface Tag {
    id: string;
    name: string;
    color?: string;
    document_count: number;
}

// Document API
export const documentApi = {
    list: async (skip = 0, limit = 50): Promise<{ documents: Document[]; total: number }> => {
        const response = await apiClient.get('/api/documents', { params: { skip, limit } });
        return response.data;
    },

    get: async (id: string): Promise<Document> => {
        const response = await apiClient.get(`/api/documents/${id}`);
        return response.data;
    },

    create: async (data: DocumentCreate): Promise<Document> => {
        const response = await apiClient.post('/api/documents', data);
        return response.data;
    },

    update: async (id: string, data: DocumentUpdate): Promise<Document> => {
        const response = await apiClient.put(`/api/documents/${id}`, data);
        return response.data;
    },

    delete: async (id: string): Promise<void> => {
        await apiClient.delete(`/api/documents/${id}`);
    },

    search: async (query: string, limit = 10): Promise<{ documents: Document[] }> => {
        const response = await apiClient.get('/api/documents/search', { params: { q: query, limit } });
        return response.data;
    },

    upload: async (file: File): Promise<Document> => {
        const formData = new FormData();
        formData.append('file', file);
        const response = await apiClient.post('/api/documents/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    },

    index: async (id: string): Promise<Document> => {
        const response = await apiClient.post(`/api/documents/${id}/index`);
        return response.data;
    },

    getByTag: async (tag: string, limit = 50): Promise<{ documents: Document[] }> => {
        const response = await apiClient.get(`/api/documents/by-tag/${tag}`, { params: { limit } });
        return response.data;
    },

    getLinks: async (id: string): Promise<{ outgoing: Document[]; incoming: Document[] }> => {
        const response = await apiClient.get(`/api/documents/${id}/links`);
        return response.data;
    },
};

// Chat API
export const chatApi = {
    // Conversations
    listConversations: async (skip = 0, limit = 20): Promise<{ conversations: Conversation[] }> => {
        const response = await apiClient.get('/api/chat/conversations', { params: { skip, limit } });
        return response.data;
    },

    getConversation: async (id: string): Promise<Conversation> => {
        const response = await apiClient.get(`/api/chat/conversations/${id}`);
        return response.data;
    },

    createConversation: async (title: string): Promise<Conversation> => {
        const response = await apiClient.post('/api/chat/conversations', { title });
        return response.data;
    },

    deleteConversation: async (id: string): Promise<void> => {
        await apiClient.delete(`/api/chat/conversations/${id}`);
    },

    // Messages
    getMessages: async (conversationId: string, limit = 50): Promise<Message[]> => {
        const response = await apiClient.get(`/api/chat/conversations/${conversationId}/messages`, {
            params: { limit },
        });
        return response.data;
    },

    sendMessage: async (conversationId: string, data: ChatRequest): Promise<{ message: Message; context_used: string[] }> => {
        const response = await apiClient.post(`/api/chat/conversations/${conversationId}/messages`, data);
        return response.data;
    },

    // Quick ask (without conversation)
    ask: async (data: ChatRequest): Promise<{ message: Message; context_used: string[] }> => {
        const response = await apiClient.post('/api/chat/ask', data);
        return response.data;
    },

    // Semantic search
    semanticSearch: async (query: string, topK = 5, includeDocuments = true): Promise<{ results: SearchResult[] }> => {
        const response = await apiClient.post('/api/chat/search', {
            query,
            top_k: topK,
            include_documents: includeDocuments,
        });
        return response.data;
    },
};

// System API
export const systemApi = {
    health: async (): Promise<{
        status: string;
        version: string;
        database: string;
        vector_store: Record<string, unknown>;
        llm: Record<string, unknown>;
    }> => {
        const response = await apiClient.get('/health');
        return response.data;
    },

    stats: async (): Promise<{
        total_documents: number;
        indexed_documents: number;
        total_chunks: number;
        total_tags: number;
    }> => {
        const response = await apiClient.get('/stats');
        return response.data;
    },

    tags: async (): Promise<{ tags: Tag[] }> => {
        const response = await apiClient.get('/tags');
        return response.data;
    },
};

// AI Tools - using chat API for AI features
export const aiApi = {
    // Generate smart tags for content
    generateTags: async (content: string): Promise<string[]> => {
        const prompt = `Read the following note content and generate 5 relevant, short keywords or tags. Output ONLY the tags separated by commas. Content: ${content}`;
        const response = await chatApi.ask({ message: prompt, use_rag: false });
        const tags = response.message.content
            .split(/[,，、\n]/)
            .map((t: string) => t.trim().replace(/^#/, ''))
            .filter((t: string) => t.length > 0 && t.length < 15);
        return tags.slice(0, 5);
    },

    // Generate summary for content
    generateSummary: async (content: string): Promise<string> => {
        const prompt = `Please summarize the following note content into one concise paragraph (max 100 words). Content: ${content}`;
        const response = await chatApi.ask({ message: prompt, use_rag: false });
        return response.message.content;
    },

    // Continue writing
    continueWriting: async (content: string): Promise<string> => {
        const prompt = `Continue writing the text below naturally. Maintain the tone and language. Provide about 2-3 sentences. Text: ${content.slice(-2000)}`;
        const response = await chatApi.ask({ message: prompt, use_rag: false });
        return response.message.content;
    },

    // Extract tasks
    extractTasks: async (content: string): Promise<string> => {
        const prompt = `Identify actionable tasks from this content. Output as Markdown checklist. Content: ${content}`;
        const response = await chatApi.ask({ message: prompt, use_rag: false });
        return response.message.content;
    },

    // Polish text
    polishText: async (content: string): Promise<string> => {
        const prompt = `Rewrite to be more professional and clear. Content: ${content}`;
        const response = await chatApi.ask({ message: prompt, use_rag: false });
        return response.message.content;
    },

    // Translate
    translate: async (content: string): Promise<string> => {
        const prompt = `Translate to English (if Chinese) or Chinese (if English). Output markdown. Content: ${content}`;
        const response = await chatApi.ask({ message: prompt, use_rag: false });
        return response.message.content;
    },

    // Generate flashcards
    generateFlashcards: async (content: string): Promise<{ front: string; back: string }[]> => {
        const prompt = `Generate 5 high-quality flashcards. Format each as "Front | Back" on separate lines. Content: ${content}`;
        const response = await chatApi.ask({ message: prompt, use_rag: false });
        const lines = response.message.content.split('\n').filter((l: string) => l.includes('|'));
        return lines.map((line: string) => {
            const [front, back] = line.split('|');
            return { front: front?.trim() || '', back: back?.trim() || '' };
        }).filter((c: { front: string; back: string }) => c.front && c.back);
    },

    // Brainstorm ideas
    brainstorm: async (content: string): Promise<{ title: string; desc: string }[]> => {
        const prompt = `Based on the following note, brainstorm 3 new related topics. Format each as "Title|Description" on separate lines. Context: ${content.slice(0, 1000)}`;
        const response = await chatApi.ask({ message: prompt, use_rag: false });
        const lines = response.message.content.split('\n').filter((l: string) => l.includes('|'));
        return lines.map((line: string) => {
            const [title, desc] = line.split('|');
            return { title: title?.trim() || '', desc: desc?.trim() || '' };
        });
    },

    // Generate quiz
    generateQuiz: async (content: string): Promise<string> => {
        const prompt = `Generate a multiple-choice question based on this note. Content: ${content}`;
        const response = await chatApi.ask({ message: prompt, use_rag: false });
        return response.message.content;
    },

    // Critical analysis
    criticalAnalysis: async (content: string): Promise<string> => {
        const prompt = `Act as a critical thinking professor. Analyze the following text deeply.
Identify:
1. Logical fallacies or weak arguments.
2. Missing evidence or perspectives.
3. Potential biases.
4. Suggestions for improvement.

Be constructive but strict.

Text:
${content}`;
        const response = await chatApi.ask({ message: prompt, use_rag: false });
        return response.message.content;
    },

    // Analyze graph relationships
    analyzeGraph: async (notesSummary: string): Promise<{ source: string; target: string }[]> => {
        const prompt = `Analyze these notes and identify up to 8 strong semantic relationships. Return ONLY pairs as "id1|id2" on separate lines. Notes: ${notesSummary}`;
        const response = await chatApi.ask({ message: prompt, use_rag: false });
        const pairs = response.message.content.match(/[a-zA-Z0-9-]+\|[a-zA-Z0-9-]+/g);
        if (pairs) {
            return pairs.map((pair: string) => {
                const [source, target] = pair.split('|');
                return { source, target };
            });
        }
        return [];
    },
};

export default apiClient;
