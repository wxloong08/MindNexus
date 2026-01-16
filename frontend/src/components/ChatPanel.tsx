'use client';

import React from 'react';
import { FileText, ArrowRight } from 'lucide-react';
import { useAppStore, ChatMessage } from '@/lib/store';
import { ChatInput } from './ChatInput';
import { chatApi } from '@/lib/api';

export const ChatPanel: React.FC = () => {
    const { filteredMessages, isTyping, addMessage, setIsTyping, notes } = useAppStore();

    const messages = filteredMessages();

    const handleSendMessage = async (text: string) => {
        const newUserMsg: ChatMessage = { role: 'user', content: text };
        addMessage(newUserMsg);
        setIsTyping(true);

        const query = text.toLowerCase();

        // Local retrieval logic (simplified RAG)
        const relevantNotes = notes
            .map((note) => {
                let score = 0;
                const noteText = (note.title + '\n' + note.content + '\n' + note.tags.join(' ')).toLowerCase();

                // Strong match
                if (query.includes(note.title.toLowerCase()) || note.title.toLowerCase().includes(query)) {
                    score += 10;
                }
                note.tags.forEach((tag) => {
                    if (query.includes(tag.toLowerCase())) score += 5;
                });

                // Weak match: N-gram for Chinese
                if (/[\u4e00-\u9fa5]/.test(query)) {
                    let hitCount = 0;
                    for (let i = 0; i < query.length - 1; i++) {
                        const bigram = query.substring(i, i + 2);
                        if (!['是什么', '怎么', '如何', '这个', '那个'].includes(bigram)) {
                            if (noteText.includes(bigram)) hitCount++;
                        }
                    }
                    if (hitCount > 0) score += hitCount * 2;
                }

                // Space-separated keywords
                const spaceKeywords = query.split(' ').filter((w) => w.trim().length > 1);
                spaceKeywords.forEach((kw) => {
                    if (noteText.includes(kw)) score += 3;
                });

                return { ...note, score };
            })
            .filter((n) => n.score > 0)
            .sort((a, b) => b.score - a.score)
            .slice(0, 5);

        // Build context
        const sources = relevantNotes.map((n) => n.title);
        const contextText = relevantNotes
            .map((n) => `Title: ${n.title}\nContent: ${n.content}\nTags: ${n.tags.join(', ')}`)
            .join('\n\n---\n\n');

        try {
            // Call backend RAG
            const response = await chatApi.ask({
                message: contextText
                    ? `Context:\n${contextText}\n\nUser Question: ${text}\n\nInstructions: Answer based on the context. Respond in Chinese. At the end, suggest 3 follow-up questions in format:\n<<<SUGGESTIONS>>>\nQuestion 1\nQuestion 2\nQuestion 3`
                    : text,
                use_rag: true,
            });

            let content = response.message.content;
            let suggestions: string[] = [];

            // Parse suggestions
            if (content.includes('<<<SUGGESTIONS>>>')) {
                const parts = content.split('<<<SUGGESTIONS>>>');
                content = parts[0].trim();
                const suggestionsText = parts[1]?.trim() || '';
                suggestions = suggestionsText.split('\n').filter((s) => s.trim().length > 0);
            }

            addMessage({
                role: 'assistant',
                content: content,
                sources: contextText ? sources : [],
                suggestions: suggestions,
            });
        } catch (error) {
            console.error('Chat error:', error);
            addMessage({
                role: 'assistant',
                content: '抱歉，连接 AI 服务时出现错误。',
                sources: [],
            });
        } finally {
            setIsTyping(false);
        }
    };

    const handleSuggestionClick = (suggestion: string) => {
        handleSendMessage(suggestion);
    };

    return (
        <div className="flex flex-col h-full max-w-4xl mx-auto bg-white shadow-sm border-x border-slate-100">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                    >
                        <div
                            className={`max-w-[80%] rounded-2xl p-4 shadow-sm ${msg.role === 'user'
                                    ? 'bg-blue-600 text-white rounded-br-none'
                                    : 'bg-slate-100 text-slate-800 rounded-bl-none'
                                }`}
                        >
                            {msg.content.startsWith('data:image') ? (
                                <img src={msg.content} alt="AI Generated" className="rounded-lg max-w-full" />
                            ) : (
                                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                            )}

                            {msg.sources && msg.sources.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-slate-200/50">
                                    <p className="text-xs font-semibold mb-1 opacity-70 flex items-center gap-1">
                                        <FileText size={10} /> 上下文来源:
                                    </p>
                                    <div className="flex flex-wrap gap-2">
                                        {msg.sources.map((src, i) => (
                                            <span
                                                key={i}
                                                className="text-xs bg-black/5 px-1.5 py-0.5 rounded cursor-pointer hover:bg-black/10 transition-colors"
                                            >
                                                {src}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* AI Smart Suggestions */}
                        {msg.suggestions && msg.suggestions.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-2 animate-in fade-in slide-in-from-top-2">
                                {msg.suggestions.map((sugg, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleSuggestionClick(sugg)}
                                        className="text-xs bg-blue-50 text-blue-600 border border-blue-100 hover:bg-blue-100 hover:border-blue-200 px-3 py-1.5 rounded-full transition-all flex items-center gap-1"
                                    >
                                        {sugg} <ArrowRight size={10} />
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                ))}

                {/* Typing indicator */}
                {isTyping && (
                    <div className="flex justify-start">
                        <div className="bg-slate-100 rounded-2xl p-4 rounded-bl-none flex items-center gap-2">
                            <div
                                className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                                style={{ animationDelay: '0ms' }}
                            />
                            <div
                                className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                                style={{ animationDelay: '150ms' }}
                            />
                            <div
                                className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                                style={{ animationDelay: '300ms' }}
                            />
                        </div>
                    </div>
                )}
            </div>

            {/* Input */}
            <div className="p-4 border-t border-slate-100">
                <ChatInput onSend={handleSendMessage} disabled={isTyping} />
            </div>
        </div>
    );
};
