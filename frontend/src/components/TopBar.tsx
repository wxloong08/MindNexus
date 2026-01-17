'use client';

import React, { useRef } from 'react';
import { Search, Upload, Plus } from 'lucide-react';
import { useAppStore } from '@/lib/store';

export const TopBar: React.FC = () => {
    const { searchQuery, setSearchQuery, createNote, setViewMode, activeTab } = useAppStore();
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            // Simulate PDF parsing (in real app, would call backend)
            setTimeout(() => {
                createNote(
                    file.name,
                    `# ${file.name}\n\n[系统提示：这是一个模拟的 PDF 解析内容]\n\n文件 ${file.name} 已被系统处理。内容包含关于该文档主题的详细描述...`
                );
                setViewMode('preview');
            }, 800);
        }
    };

    // Hide search and actions in chat tab (AI Assistant)
    if (activeTab === 'chat') {
        return (
            <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-center px-6 flex-shrink-0">
                <h1 className="text-lg font-semibold text-slate-700">AI 助手</h1>
            </header>
        );
    }

    return (
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 flex-shrink-0">
            {/* Search */}
            <div className="flex items-center bg-slate-100 rounded-full px-4 py-2 w-full max-w-md">
                <Search className="w-5 h-5 text-slate-400" />
                <input
                    type="text"
                    placeholder="搜索笔记、标签或询问 AI..."
                    className="bg-transparent border-none outline-none ml-2 w-full text-slate-700 placeholder-slate-400"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
                {/* Import PDF */}
                <label className="flex items-center gap-2 px-3 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 cursor-pointer transition-colors text-sm font-medium">
                    <Upload size={16} />
                    <span className="hidden sm:inline">导入 PDF</span>
                    <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        accept=".pdf,.md,.txt"
                        onChange={handleFileUpload}
                    />
                </label>

                {/* New Note */}
                <button
                    onClick={() => createNote()}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 shadow-md transition-all transform active:scale-95"
                >
                    <Plus size={18} />
                    <span className="hidden sm:inline">新建笔记</span>
                </button>
            </div>
        </header>
    );
};
