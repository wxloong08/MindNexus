'use client';

import React, { useEffect } from 'react';
import { FileText, Loader, Network } from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { aiApi } from '@/lib/api';
import { Sidebar, TopBar, NoteList, NoteEditor, ChatPanel, KnowledgeGraph, SettingsModal } from '@/components';

export default function Home() {
  const {
    activeTab,
    filteredNotes,
    selectedNoteId,
    aiLinks,
    setAiLinks,
    isAnalyzingGraph,
    setIsAnalyzingGraph,
    setSelectedNoteId,
    setActiveTab,
    syncNotesFromBackend,
  } = useAppStore();

  // Load notes from backend on initial mount
  useEffect(() => {
    syncNotesFromBackend().catch(console.error);
  }, [syncNotesFromBackend]);

  // Use filtered notes for knowledge graph
  const notes = filteredNotes();

  const handleAnalyzeGraph = async () => {
    if (notes.length < 2) return;
    setIsAnalyzingGraph(true);
    try {
      const notesSummary = notes
        .map((n) => `ID: ${n.id} | Title: ${n.title} | Content Snippet: ${n.content.slice(0, 100)}...`)
        .join('\n');
      const links = await aiApi.analyzeGraph(notesSummary);
      setAiLinks(links.map((l) => ({ ...l, type: 'ai' as const })));
    } catch (e) {
      console.error(e);
    } finally {
      setIsAnalyzingGraph(false);
    }
  };

  const handleNodeClick = (id: string) => {
    setSelectedNoteId(id);
    setActiveTab('notes');
  };

  return (
    <div className="flex h-screen w-full bg-slate-50 text-slate-800 font-sans overflow-hidden">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Top Bar */}
        <TopBar />

        {/* Dynamic Content */}
        <main className="flex-1 overflow-hidden relative bg-slate-50/50">
          {/* Notes Tab */}
          {activeTab === 'notes' && (
            <div className="flex h-full">
              {/* Note List */}
              <div
                className={`${selectedNoteId ? 'hidden md:flex' : 'flex'
                  } w-full md:w-80 flex-col border-r border-slate-200 bg-white h-full`}
              >
                <NoteList />
              </div>

              {/* Editor */}
              {selectedNoteId ? (
                <NoteEditor />
              ) : (
                <div className="hidden md:flex flex-1 flex-col items-center justify-center text-slate-300">
                  <FileText size={64} className="mb-4 opacity-50" />
                  <p className="text-lg font-medium">选择或创建一个笔记</p>
                </div>
              )}
            </div>
          )}

          {/* Graph Tab - now uses filtered notes */}
          {activeTab === 'graph' && (
            <div className="relative w-full h-full">
              <KnowledgeGraph notes={notes} aiLinks={aiLinks} onNodeClick={handleNodeClick} />
              <button
                onClick={handleAnalyzeGraph}
                disabled={isAnalyzingGraph}
                className="absolute bottom-6 right-6 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full shadow-xl flex items-center gap-2 transition-all transform hover:scale-105 disabled:opacity-70 disabled:cursor-wait"
              >
                {isAnalyzingGraph ? (
                  <Loader size={20} className="animate-spin" />
                ) : (
                  <Network size={20} />
                )}
                {isAnalyzingGraph ? 'AI 分析图谱中...' : '✨ AI 语义关联'}
              </button>
            </div>
          )}

          {/* Chat Tab */}
          {activeTab === 'chat' && <ChatPanel />}
        </main>
      </div>

      {/* Settings Modal */}
      <SettingsModal />
    </div>
  );
}
