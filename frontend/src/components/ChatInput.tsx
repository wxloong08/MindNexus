'use client';

import React, { useState } from 'react';
import { ChevronRight } from 'lucide-react';

interface ChatInputProps {
    onSend: (text: string) => void;
    disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled = false }) => {
    const [text, setText] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (text.trim() && !disabled) {
            onSend(text);
            setText('');
        }
    };

    return (
        <form onSubmit={handleSubmit} className="relative">
            <input
                type="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="询问关于您的笔记、文档或创意..."
                className="w-full bg-slate-50 border border-slate-200 text-slate-800 rounded-xl px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                disabled={disabled}
            />
            <button
                type="submit"
                disabled={!text.trim() || disabled}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
                <ChevronRight size={18} />
            </button>
        </form>
    );
};
