/**
 * Knowledge Assistant - Frontend Application
 * A modern single-page application for knowledge management
 */

// ============== API Client ==============
const API_BASE = '/api';

class ApiClient {
    async request(method, endpoint, data = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        if (response.status === 204) {
            return null;
        }
        
        return response.json();
    }
    
    // Documents
    async getDocuments(skip = 0, limit = 50) {
        return this.request('GET', `/documents?skip=${skip}&limit=${limit}`);
    }
    
    async getDocument(id) {
        return this.request('GET', `/documents/${id}`);
    }
    
    async createDocument(data) {
        return this.request('POST', '/documents', data);
    }
    
    async updateDocument(id, data) {
        return this.request('PUT', `/documents/${id}`, data);
    }
    
    async deleteDocument(id) {
        return this.request('DELETE', `/documents/${id}`);
    }
    
    async searchDocuments(query) {
        return this.request('GET', `/documents/search?q=${encodeURIComponent(query)}`);
    }
    
    async uploadDocument(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE}/documents/upload`, {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
            throw new Error(error.detail);
        }
        
        return response.json();
    }
    
    // Chat
    async getConversations() {
        return this.request('GET', '/chat/conversations');
    }
    
    async createConversation(title = null) {
        return this.request('POST', '/chat/conversations', { title });
    }
    
    async deleteConversation(id) {
        return this.request('DELETE', `/chat/conversations/${id}`);
    }
    
    async getMessages(conversationId) {
        return this.request('GET', `/chat/conversations/${conversationId}/messages`);
    }
    
    async sendMessage(conversationId, message, useRag = true, model = null) {
        return this.request('POST', `/chat/conversations/${conversationId}/messages`, {
            message,
            use_rag: useRag,
            model,
            stream: false,
        });
    }
    
    // Streaming chat
    streamMessage(conversationId, message, useRag = true, onToken, onContext, onDone, onError) {
        const url = `${API_BASE}/chat/conversations/${conversationId}/messages/stream`;
        
        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, use_rag: useRag, stream: true }),
        }).then(response => {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            function processLine(line) {
                if (line.startsWith('event:')) {
                    return; // Skip event type lines
                }
                if (line.startsWith('data:')) {
                    const data = line.slice(5).trim();
                    if (data) {
                        try {
                            // Check if it's a JSON object or plain string
                            if (data.startsWith('{') || data.startsWith('[')) {
                                const parsed = JSON.parse(data);
                                if (parsed.chunks) {
                                    onContext(parsed.chunks);
                                } else if (parsed.message_id) {
                                    onDone(parsed);
                                } else if (parsed.detail) {
                                    onError(new Error(parsed.detail));
                                }
                            } else {
                                // Plain token
                                onToken(data);
                            }
                        } catch (e) {
                            // Treat as plain token
                            onToken(data);
                        }
                    }
                }
            }
            
            function read() {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        if (buffer) {
                            buffer.split('\n').forEach(processLine);
                        }
                        return;
                    }
                    
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    lines.forEach(processLine);
                    
                    read();
                }).catch(onError);
            }
            
            read();
        }).catch(onError);
    }
    
    // Search
    async semanticSearch(query, topK = 10) {
        return this.request('POST', '/chat/search', {
            query,
            top_k: topK,
            include_documents: true,
        });
    }
    
    // Quick ask
    async quickAsk(message, useRag = true) {
        return this.request('POST', '/chat/ask', {
            message,
            use_rag: useRag,
        });
    }
    
    // System
    async getStats() {
        return this.request('GET', '/../stats');
    }
    
    async getTags() {
        return this.request('GET', '/../tags');
    }
}

const api = new ApiClient();

// ============== State Management ==============
const state = {
    currentView: 'documents',
    documents: [],
    currentDocument: null,
    conversations: [],
    currentConversation: null,
    messages: [],
    tags: [],
    stats: null,
    isEditing: false,
};

// ============== UI Helpers ==============
function $(selector) {
    return document.querySelector(selector);
}

function $$(selector) {
    return document.querySelectorAll(selector);
}

function showToast(message, type = 'info') {
    const container = $('#toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============== View Management ==============
function switchView(viewName) {
    state.currentView = viewName;
    
    // Update nav
    $$('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === viewName);
    });
    
    // Update views
    $$('.view').forEach(view => {
        view.classList.toggle('active', view.id === `view-${viewName}`);
    });
    
    // Load view data
    switch (viewName) {
        case 'documents':
            loadDocuments();
            break;
        case 'chat':
            loadConversations();
            break;
        case 'search':
            break;
        case 'graph':
            break;
    }
}

// ============== Documents ==============
async function loadDocuments() {
    try {
        const response = await api.getDocuments();
        state.documents = response.documents;
        renderDocuments();
    } catch (error) {
        showToast('Failed to load documents: ' + error.message, 'error');
    }
}

function renderDocuments() {
    const grid = $('#documents-grid');
    
    if (state.documents.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📄</div>
                <h3>No documents yet</h3>
                <p>Create your first document or upload files to get started.</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = state.documents.map(doc => `
        <div class="document-card" data-id="${doc.id}">
            <div class="card-header">
                <h3 class="card-title">${escapeHtml(doc.title)}</h3>
                <span class="card-status status-${doc.status}">${doc.status}</span>
            </div>
            <div class="card-body">
                <p class="card-preview">${escapeHtml(doc.summary || doc.content.slice(0, 150))}...</p>
            </div>
            <div class="card-footer">
                <div class="card-tags">
                    ${doc.tags.slice(0, 3).map(tag => `<span class="tag">#${escapeHtml(tag)}</span>`).join('')}
                </div>
                <span class="card-date">${formatDate(doc.updated_at)}</span>
            </div>
        </div>
    `).join('');
    
    // Add click handlers
    $$('.document-card').forEach(card => {
        card.addEventListener('click', () => openDocument(card.dataset.id));
    });
}

async function openDocument(id) {
    try {
        const doc = await api.getDocument(id);
        state.currentDocument = doc;
        showDocumentView(doc);
    } catch (error) {
        showToast('Failed to load document: ' + error.message, 'error');
    }
}

function showDocumentView(doc) {
    $('#view-doc-title').textContent = doc.title;
    $('#view-doc-metadata').innerHTML = `
        <div class="metadata-item">
            <span class="label">Status:</span>
            <span class="status-${doc.status}">${doc.status}</span>
        </div>
        <div class="metadata-item">
            <span class="label">Words:</span>
            <span>${doc.word_count}</span>
        </div>
        <div class="metadata-item">
            <span class="label">Updated:</span>
            <span>${formatDate(doc.updated_at)}</span>
        </div>
        <div class="metadata-item">
            <span class="label">Tags:</span>
            <span>${doc.tags.map(t => `<span class="tag">#${escapeHtml(t)}</span>`).join(' ')}</span>
        </div>
    `;
    
    // Render markdown
    const html = marked.parse(doc.content);
    $('#view-doc-content').innerHTML = html;
    
    // Highlight code blocks
    $$('#view-doc-content pre code').forEach(block => {
        hljs.highlightElement(block);
    });
    
    $('#doc-view-modal').classList.add('active');
}

function openEditor(doc = null) {
    state.isEditing = !!doc;
    state.currentDocument = doc;
    
    $('#doc-title').value = doc?.title || '';
    $('#doc-content').value = doc?.content || '';
    $('#doc-tags').value = doc?.tags?.join(', ') || '';
    
    $('#editor-modal').classList.add('active');
    $('#doc-title').focus();
}

async function saveDocument() {
    const title = $('#doc-title').value.trim();
    const content = $('#doc-content').value.trim();
    const tags = $('#doc-tags').value.split(',').map(t => t.trim()).filter(t => t);
    
    if (!title) {
        showToast('Title is required', 'error');
        return;
    }
    
    try {
        if (state.isEditing && state.currentDocument) {
            await api.updateDocument(state.currentDocument.id, { title, content, tags });
            showToast('Document updated successfully', 'success');
        } else {
            await api.createDocument({ title, content, tags });
            showToast('Document created successfully', 'success');
        }
        
        closeModal('editor-modal');
        loadDocuments();
        loadStats();
    } catch (error) {
        showToast('Failed to save document: ' + error.message, 'error');
    }
}

async function deleteDocument() {
    if (!state.currentDocument) return;
    
    if (!confirm('Are you sure you want to delete this document?')) {
        return;
    }
    
    try {
        await api.deleteDocument(state.currentDocument.id);
        showToast('Document deleted', 'success');
        closeModal('doc-view-modal');
        loadDocuments();
        loadStats();
    } catch (error) {
        showToast('Failed to delete document: ' + error.message, 'error');
    }
}

// ============== File Upload ==============
function setupUpload() {
    const uploadArea = $('#upload-area');
    const fileInput = $('#file-input');
    
    uploadArea.addEventListener('click', () => fileInput.click());
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    
    fileInput.addEventListener('change', () => {
        handleFiles(fileInput.files);
    });
}

async function handleFiles(files) {
    const progress = $('#upload-progress');
    const status = $('#upload-status');
    const fill = $('#progress-fill');
    
    progress.style.display = 'block';
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        status.textContent = `Uploading ${file.name}...`;
        fill.style.width = `${((i + 0.5) / files.length) * 100}%`;
        
        try {
            await api.uploadDocument(file);
            showToast(`Uploaded: ${file.name}`, 'success');
        } catch (error) {
            showToast(`Failed to upload ${file.name}: ${error.message}`, 'error');
        }
        
        fill.style.width = `${((i + 1) / files.length) * 100}%`;
    }
    
    progress.style.display = 'none';
    closeModal('upload-modal');
    loadDocuments();
    loadStats();
}

// ============== Chat ==============
async function loadConversations() {
    try {
        const response = await api.getConversations();
        state.conversations = response.conversations;
        
        if (state.conversations.length > 0 && !state.currentConversation) {
            await selectConversation(state.conversations[0].id);
        }
    } catch (error) {
        console.error('Failed to load conversations:', error);
    }
}

async function createNewChat() {
    try {
        const conv = await api.createConversation();
        state.currentConversation = conv;
        state.messages = [];
        renderMessages();
        showToast('New chat created', 'success');
    } catch (error) {
        showToast('Failed to create chat: ' + error.message, 'error');
    }
}

async function selectConversation(id) {
    try {
        state.currentConversation = state.conversations.find(c => c.id === id);
        const messages = await api.getMessages(id);
        state.messages = messages;
        renderMessages();
    } catch (error) {
        showToast('Failed to load messages: ' + error.message, 'error');
    }
}

function renderMessages() {
    const container = $('#chat-messages');
    
    if (state.messages.length === 0) {
        container.innerHTML = `
            <div class="welcome-message">
                <h3>👋 Welcome to Knowledge Assistant</h3>
                <p>Ask questions about your documents. I'll search your knowledge base and provide relevant answers.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = state.messages.map(msg => `
        <div class="message message-${msg.role}">
            <div class="message-avatar">${msg.role === 'user' ? '👤' : '🤖'}</div>
            <div class="message-content">
                ${msg.role === 'assistant' ? marked.parse(msg.content) : escapeHtml(msg.content)}
            </div>
        </div>
    `).join('');
    
    // Highlight code blocks
    $$('#chat-messages pre code').forEach(block => {
        hljs.highlightElement(block);
    });
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

async function sendChatMessage() {
    const input = $('#chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Create conversation if needed
    if (!state.currentConversation) {
        await createNewChat();
    }
    
    // Add user message to UI
    state.messages.push({ role: 'user', content: message });
    renderMessages();
    input.value = '';
    
    const useRag = $('#toggle-rag').checked;
    const contextPreview = $('#context-preview');
    const contextItems = $('#context-items');
    
    // Create assistant message placeholder
    const assistantMsg = { role: 'assistant', content: '' };
    state.messages.push(assistantMsg);
    renderMessages();
    
    // Stream response
    api.streamMessage(
        state.currentConversation.id,
        message,
        useRag,
        // onToken
        (token) => {
            assistantMsg.content += token;
            const lastMsgEl = $('#chat-messages .message:last-child .message-content');
            if (lastMsgEl) {
                lastMsgEl.innerHTML = marked.parse(assistantMsg.content);
            }
            $('#chat-messages').scrollTop = $('#chat-messages').scrollHeight;
        },
        // onContext
        (chunks) => {
            if (chunks && chunks.length > 0) {
                contextPreview.style.display = 'block';
                contextItems.innerHTML = chunks.map(c => `
                    <div class="context-item" title="${escapeHtml(c.content)}">
                        <span class="context-score">${(c.score * 100).toFixed(0)}%</span>
                        <span class="context-text">${escapeHtml(c.content.slice(0, 100))}...</span>
                    </div>
                `).join('');
            }
        },
        // onDone
        (data) => {
            // Highlight code blocks in final response
            $$('#chat-messages pre code').forEach(block => {
                hljs.highlightElement(block);
            });
            setTimeout(() => {
                contextPreview.style.display = 'none';
            }, 3000);
        },
        // onError
        (error) => {
            assistantMsg.content = `Error: ${error.message}`;
            renderMessages();
            showToast('Chat error: ' + error.message, 'error');
        }
    );
}

// ============== Semantic Search ==============
async function performSearch() {
    const query = $('#semantic-search-input').value.trim();
    if (!query) return;
    
    try {
        const response = await api.semanticSearch(query);
        renderSearchResults(response);
    } catch (error) {
        showToast('Search failed: ' + error.message, 'error');
    }
}

function renderSearchResults(response) {
    const container = $('#search-results');
    
    if (response.results.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No results found for "${escapeHtml(response.query)}"</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = response.results.map(result => `
        <div class="search-result" data-doc-id="${result.document?.id || ''}">
            <div class="result-header">
                <span class="result-score">${(result.score * 100).toFixed(1)}% match</span>
                ${result.document ? `<span class="result-doc">${escapeHtml(result.document.title)}</span>` : ''}
            </div>
            <div class="result-content">${escapeHtml(result.content)}</div>
        </div>
    `).join('');
    
    // Add click handlers
    $$('.search-result[data-doc-id]').forEach(el => {
        if (el.dataset.docId) {
            el.addEventListener('click', () => openDocument(el.dataset.docId));
        }
    });
}

// ============== Tags & Stats ==============
async function loadStats() {
    try {
        const response = await fetch('/stats');
        if (response.ok) {
            const stats = await response.json();
            state.stats = stats;
            renderStats();
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function renderStats() {
    if (!state.stats) return;
    
    $('#stats').innerHTML = `
        <span>${state.stats.total_documents} documents</span>
        <span>${state.stats.total_chunks} chunks</span>
    `;
}

async function loadTags() {
    try {
        const response = await fetch('/tags');
        if (response.ok) {
            const data = await response.json();
            state.tags = data.tags;
            renderTags();
        }
    } catch (error) {
        console.error('Failed to load tags:', error);
    }
}

function renderTags() {
    const container = $('#tags-list');
    container.innerHTML = state.tags.slice(0, 10).map(tag => `
        <button class="tag-item" data-tag="${escapeHtml(tag.name)}">
            #${escapeHtml(tag.name)} <span class="tag-count">${tag.document_count}</span>
        </button>
    `).join('');
    
    $$('.tag-item').forEach(el => {
        el.addEventListener('click', () => filterByTag(el.dataset.tag));
    });
}

async function filterByTag(tag) {
    try {
        const response = await api.request('GET', `/documents/by-tag/${encodeURIComponent(tag)}`);
        state.documents = response.documents;
        renderDocuments();
        switchView('documents');
        showToast(`Showing documents tagged #${tag}`, 'info');
    } catch (error) {
        showToast('Failed to filter by tag: ' + error.message, 'error');
    }
}

// ============== Search in Sidebar ==============
let searchTimeout = null;

function setupSidebarSearch() {
    const input = $('#search-input');
    
    input.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(async () => {
            const query = input.value.trim();
            if (query.length < 2) {
                loadDocuments();
                return;
            }
            
            try {
                const response = await api.searchDocuments(query);
                state.documents = response.documents;
                renderDocuments();
            } catch (error) {
                console.error('Search failed:', error);
            }
        }, 300);
    });
}

// ============== Modals ==============
function closeModal(modalId) {
    $(`#${modalId}`).classList.remove('active');
}

function setupModals() {
    // Close on backdrop click
    $$('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
    
    // Close buttons
    $$('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').classList.remove('active');
        });
    });
    
    // Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            $$('.modal.active').forEach(m => m.classList.remove('active'));
        }
    });
}

// ============== Editor ==============
function setupEditor() {
    const toolbar = $$('.toolbar-btn');
    const content = $('#doc-content');
    const preview = $('#doc-preview');
    
    toolbar.forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            
            switch (action) {
                case 'bold':
                    insertMarkdown('**', '**');
                    break;
                case 'italic':
                    insertMarkdown('*', '*');
                    break;
                case 'heading':
                    insertMarkdown('## ', '');
                    break;
                case 'link':
                    insertMarkdown('[', '](url)');
                    break;
                case 'code':
                    insertMarkdown('```\n', '\n```');
                    break;
                case 'preview':
                    togglePreview();
                    break;
            }
        });
    });
    
    function insertMarkdown(before, after) {
        const start = content.selectionStart;
        const end = content.selectionEnd;
        const text = content.value;
        const selected = text.substring(start, end);
        
        content.value = text.substring(0, start) + before + selected + after + text.substring(end);
        content.focus();
        content.setSelectionRange(start + before.length, start + before.length + selected.length);
    }
    
    function togglePreview() {
        const isPreview = preview.style.display !== 'none';
        
        if (isPreview) {
            preview.style.display = 'none';
            content.style.display = 'block';
        } else {
            preview.innerHTML = marked.parse(content.value);
            $$('#doc-preview pre code').forEach(block => {
                hljs.highlightElement(block);
            });
            preview.style.display = 'block';
            content.style.display = 'none';
        }
    }
}

// ============== Initialization ==============
function init() {
    // Setup event listeners
    setupModals();
    setupUpload();
    setupEditor();
    setupSidebarSearch();
    
    // Navigation
    $$('.nav-item').forEach(item => {
        item.addEventListener('click', () => switchView(item.dataset.view));
    });
    
    // Document actions
    $('#btn-new-doc').addEventListener('click', () => openEditor());
    $('#btn-upload').addEventListener('click', () => $('#upload-modal').classList.add('active'));
    $('#btn-save-doc').addEventListener('click', saveDocument);
    $('#btn-cancel-doc').addEventListener('click', () => closeModal('editor-modal'));
    $('#btn-edit-doc').addEventListener('click', () => {
        closeModal('doc-view-modal');
        openEditor(state.currentDocument);
    });
    $('#btn-delete-doc').addEventListener('click', deleteDocument);
    
    // Chat actions
    $('#btn-new-chat').addEventListener('click', createNewChat);
    $('#btn-send').addEventListener('click', sendChatMessage);
    $('#chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    
    // Search
    $('#btn-search').addEventListener('click', performSearch);
    $('#semantic-search-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') performSearch();
    });
    
    // Auto-resize chat input
    $('#chat-input').addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 150) + 'px';
    });
    
    // Load initial data
    loadDocuments();
    loadStats();
    loadTags();
}

// Start the app
document.addEventListener('DOMContentLoaded', init);
