'use client';

import React from 'react';
import { File } from 'lucide-react';
import { useAppStore } from '@/lib/store';

export const NoteList: React.FC = () => {
    const {
        filteredNotes,
        selectedNoteId,
        setSelectedNoteId,
        setViewMode,
        setSuggestedTags,
        setBrainstormIdeas,
        setFlashcards,
        setShowFlashcards,
    } = useAppStore();

    const notes = filteredNotes();

    const handleNoteClick = (noteId: string) => {
        setSelectedNoteId(noteId);
        setSuggestedTags([]);
        setViewMode('edit');  // Default to edit mode for immediate title editing
        setBrainstormIdeas([]);
        setFlashcards([]);
        setShowFlashcards(false);
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="p-4 border-b border-slate-100 flex justify-between items-center">
                <span className="font-semibold text-slate-500 text-sm">{notes.length} 篇笔记</span>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto">
                {notes.map((note) => (
                    <div
                        key={note.id}
                        onClick={() => handleNoteClick(note.id)}
                        className={`p-4 border-b border-slate-100 cursor-pointer transition-colors hover:bg-slate-50 ${selectedNoteId === note.id
                            ? 'bg-blue-50 border-l-4 border-l-blue-500'
                            : 'border-l-4 border-l-transparent'
                            }`}
                    >
                        <div className="flex items-start justify-between mb-1">
                            <h3 className="font-medium text-slate-800 truncate pr-2">
                                {note.title || '未命名'}
                            </h3>
                            {note.type === 'pdf' && (
                                <File size={14} className="text-red-400 flex-shrink-0 mt-1" />
                            )}
                        </div>
                        <p className="text-xs text-slate-400 mb-2 line-clamp-2">
                            {note.content ? note.content.replace(/[#*`]/g, '') : '无内容...'}
                        </p>
                        <div className="flex flex-wrap gap-1">
                            {note.tags.map((tag) => (
                                <span
                                    key={tag}
                                    className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded-md"
                                >
                                    #{tag}
                                </span>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
