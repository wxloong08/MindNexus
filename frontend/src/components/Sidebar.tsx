'use client';

import React from 'react';
import { Brain, FileText, Share2, MessageSquare, Settings } from 'lucide-react';
import { NavButton } from './NavButton';
import { useAppStore } from '@/lib/store';

export const Sidebar: React.FC = () => {
    const { activeTab, setActiveTab, setShowSettings } = useAppStore();

    return (
        <div className="w-16 md:w-64 bg-slate-900 text-white flex flex-col flex-shrink-0 transition-all duration-300">
            {/* Logo */}
            <div className="p-4 flex items-center justify-center md:justify-start gap-3 border-b border-slate-700">
                <Brain className="w-8 h-8 text-blue-400" />
                <span className="text-xl font-bold hidden md:block tracking-tight">MindNexus</span>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-6 flex flex-col gap-2 px-2">
                <NavButton
                    active={activeTab === 'notes'}
                    onClick={() => setActiveTab('notes')}
                    icon={<FileText size={20} />}
                    label="我的笔记"
                />
                <NavButton
                    active={activeTab === 'graph'}
                    onClick={() => setActiveTab('graph')}
                    icon={<Share2 size={20} />}
                    label="知识图谱"
                />
                <NavButton
                    active={activeTab === 'chat'}
                    onClick={() => setActiveTab('chat')}
                    icon={<MessageSquare size={20} />}
                    label="AI 助手 (RAG)"
                />
            </nav>

            {/* Settings */}
            <div className="p-4 border-t border-slate-700">
                <div
                    onClick={() => setShowSettings(true)}
                    className="flex items-center gap-3 text-slate-400 hover:text-white cursor-pointer transition-colors p-2 rounded-lg hover:bg-slate-800"
                >
                    <Settings size={20} />
                    <span className="hidden md:block">设置</span>
                </div>
            </div>
        </div>
    );
};
