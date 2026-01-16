'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
    Edit3,
    Check,
    Save,
    Eye,
    Loader,
    ImageIcon,
    ShieldAlert,
    Lightbulb,
    Plus,
    X,
    Sparkles,
    PenTool,
    Cpu,
    ListChecks,
    Wand2,
    Languages,
    GalleryVerticalEnd,
    Trash2,
} from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { aiApi } from '@/lib/api';
import { SimpleMarkdown } from './SimpleMarkdown';
import { FlashcardDeck } from './FlashcardDeck';

export const NoteEditor: React.FC = () => {
    const {
        viewMode,
        setViewMode,
        updateNote,
        deleteNote,
        // AI states
        suggestedTags,
        setSuggestedTags,
        isSuggestingTags,
        setIsSuggestingTags,
        isSummarizing,
        setIsSummarizing,
        isContinuing,
        setIsContinuing,
        isExtractingTasks,
        setIsExtractingTasks,
        isPolishing,
        setIsPolishing,
        isTranslating,
        setIsTranslating,
        isGeneratingImage,
        setIsGeneratingImage,
        isCritiquing,
        setIsCritiquing,
        isBrainstorming,
        setIsBrainstorming,
        isGeneratingFlashcards,
        setIsGeneratingFlashcards,
        // Flashcards
        flashcards,
        setFlashcards,
        showFlashcards,
        setShowFlashcards,
        // Brainstorm
        brainstormIdeas,
        setBrainstormIdeas,
        // Note
        activeNote,
        createNote,
        setActiveTab,
        addMessage,
        setIsTyping,
        // Persistence
        saveNoteToBackend,
    } = useAppStore();

    // Save status: 'saved' | 'saving' | 'unsaved'
    const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved');
    const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const note = activeNote();

    if (!note) {
        return (
            <div className="hidden md:flex flex-1 flex-col items-center justify-center text-slate-300">
                <Edit3 size={64} className="mb-4 opacity-50" />
                <p className="text-lg font-medium">选择或创建一个笔记</p>
            </div>
        );
    }

    // Manual save function
    const handleSave = useCallback(async () => {
        if (!note) return;
        setSaveStatus('saving');
        try {
            await saveNoteToBackend(note);
            setSaveStatus('saved');
        } catch (e) {
            console.error('Save failed:', e);
            setSaveStatus('unsaved');
        }
    }, [note, saveNoteToBackend]);

    // Ctrl+S handler - prevents browser "Save As" and triggers save
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                handleSave();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleSave]);

    // Auto-save: 2 seconds after last change (Obsidian-style)
    useEffect(() => {
        if (note && saveStatus === 'unsaved') {
            if (saveTimeoutRef.current) {
                clearTimeout(saveTimeoutRef.current);
            }
            saveTimeoutRef.current = setTimeout(() => {
                handleSave();
            }, 2000);
        }

        return () => {
            if (saveTimeoutRef.current) {
                clearTimeout(saveTimeoutRef.current);
            }
        };
    }, [note?.content, note?.title, note?.tags, saveStatus, handleSave]);

    // AI Handlers
    const handleGenerateSmartTags = async () => {
        if (!note.content) return;
        setIsSuggestingTags(true);
        setSuggestedTags([]);
        try {
            const tags = await aiApi.generateTags(note.content);
            setSuggestedTags(tags);
        } catch (e) {
            console.error(e);
        } finally {
            setIsSuggestingTags(false);
        }
    };

    const handleGenerateSummary = async () => {
        if (!note.content) return;
        setIsSummarizing(true);
        try {
            const summary = await aiApi.generateSummary(note.content);
            const newContent = note.content + `\n\n> ✨ **AI 摘要**: ${summary}`;
            updateNote(note.id, { content: newContent });
        } catch (e) {
            console.error(e);
        } finally {
            setIsSummarizing(false);
        }
    };

    const handleContinueWriting = async () => {
        if (!note.content) return;
        setIsContinuing(true);
        try {
            const continuation = await aiApi.continueWriting(note.content);
            const separator = note.content.endsWith('\n') ? '' : '\n';
            updateNote(note.id, { content: note.content + separator + continuation });
        } catch (e) {
            console.error(e);
        } finally {
            setIsContinuing(false);
        }
    };

    const handleExtractTasks = async () => {
        if (!note.content) return;
        setIsExtractingTasks(true);
        try {
            const tasks = await aiApi.extractTasks(note.content);
            const newContent = note.content + `\n\n## ✅ 待办事项\n${tasks}`;
            updateNote(note.id, { content: newContent });
        } catch (e) {
            console.error(e);
        } finally {
            setIsExtractingTasks(false);
        }
    };

    const handlePolish = async () => {
        if (!note.content) return;
        setIsPolishing(true);
        try {
            const polished = await aiApi.polishText(note.content);
            const newContent = note.content + `\n\n---\n\n### ✨ 润色版本\n${polished}`;
            updateNote(note.id, { content: newContent });
        } catch (e) {
            console.error(e);
        } finally {
            setIsPolishing(false);
        }
    };

    const handleTranslate = async () => {
        if (!note.content) return;
        setIsTranslating(true);
        try {
            const translation = await aiApi.translate(note.content);
            const newContent = note.content + `\n\n---\n\n### 🌐 译文\n${translation}`;
            updateNote(note.id, { content: newContent });
        } catch (e) {
            console.error(e);
        } finally {
            setIsTranslating(false);
        }
    };

    const handleGenerateFlashcards = async () => {
        if (!note.content) return;
        setIsGeneratingFlashcards(true);
        setFlashcards([]);
        setShowFlashcards(true);
        try {
            const cards = await aiApi.generateFlashcards(note.content);
            setFlashcards(cards);
        } catch (e) {
            console.error('Flashcards failed', e);
            setShowFlashcards(false);
        } finally {
            setIsGeneratingFlashcards(false);
        }
    };

    const handleBrainstorm = async () => {
        if (!note.content) return;
        setIsBrainstorming(true);
        setBrainstormIdeas([]);
        try {
            const ideas = await aiApi.brainstorm(note.content);
            setBrainstormIdeas(ideas);
        } catch (e) {
            console.error(e);
        } finally {
            setIsBrainstorming(false);
        }
    };

    const handleCritique = async () => {
        if (!note.content) return;
        setActiveTab('chat');
        addMessage({ role: 'user', content: `请批判性地分析我的笔记："${note.title}"` });
        setIsCritiquing(true);
        setIsTyping(true);
        try {
            const critique = await aiApi.criticalAnalysis(note.content);
            addMessage({
                role: 'assistant',
                content: `🧐 **深度批判分析**\n\n${critique}`,
                sources: [note.title],
            });
        } catch (e) {
            console.error(e);
        } finally {
            setIsCritiquing(false);
            setIsTyping(false);
        }
    };

    const handleGenerateCover = async () => {
        if (!note.content) return;
        setIsGeneratingImage(true);
        try {
            // In a real app, this would generate an image
            // For now, we'll add a placeholder
            const markdownImage = `![AI Cover](https://picsum.photos/seed/${note.id}/800/400)\n\n`;
            updateNote(note.id, { content: markdownImage + note.content });
            setViewMode('preview');
        } catch (e) {
            console.error('Image Gen Error', e);
        } finally {
            setIsGeneratingImage(false);
        }
    };

    const handleAddTag = () => {
        const newTag = prompt('输入新标签:');
        if (newTag && !note.tags.includes(newTag)) {
            updateNote(note.id, { tags: [...note.tags, newTag] });
        }
    };

    const handleRemoveTag = (tag: string) => {
        updateNote(note.id, { tags: note.tags.filter((t) => t !== tag) });
    };

    const handleAddSuggestedTag = (tag: string) => {
        if (!note.tags.includes(tag)) {
            updateNote(note.id, { tags: [...note.tags, tag] });
        }
        setSuggestedTags(suggestedTags.filter((t) => t !== tag));
    };

    // Obsidian-style: Auto-sync title from first H1 heading in content
    const handleContentChange = (newContent: string) => {
        const updates: { content: string; title?: string } = { content: newContent };

        // Extract title from first H1 (# Title) - always sync like Obsidian
        const firstLine = newContent.split('\n')[0];
        if (firstLine.startsWith('# ')) {
            const extractedTitle = firstLine.replace(/^#\s+/, '').trim();
            if (extractedTitle) {
                updates.title = extractedTitle;
            }
        }

        updateNote(note.id, updates);
        setSaveStatus('unsaved');  // Triggers auto-save after 2 seconds
    };

    return (
        <div className="flex-1 flex flex-col bg-white h-full relative animate-in fade-in duration-300">
            <div className="p-6 flex-1 overflow-y-auto relative">
                {/* Note Title & Tools */}
                <div className="flex justify-between items-start mb-6 gap-4">
                    <input
                        type="text"
                        value={note.title}
                        onChange={(e) => updateNote(note.id, { title: e.target.value })}
                        className="text-3xl font-bold w-full outline-none text-slate-800 placeholder-slate-300 bg-transparent"
                        placeholder="笔记标题"
                    />
                    <div className="flex gap-2 flex-shrink-0">
                        {/* View Mode Toggle */}
                        <div className="bg-slate-100 p-1 rounded-lg flex items-center">
                            <button
                                onClick={() => setViewMode('edit')}
                                className={`p-2 rounded-md transition-all ${viewMode === 'edit'
                                    ? 'bg-white shadow text-blue-600'
                                    : 'text-slate-400 hover:text-slate-600'
                                    }`}
                                title="编辑模式"
                            >
                                <Edit3 size={18} />
                            </button>
                            <button
                                onClick={() => setViewMode('preview')}
                                className={`p-2 rounded-md transition-all ${viewMode === 'preview'
                                    ? 'bg-white shadow text-blue-600'
                                    : 'text-slate-400 hover:text-slate-600'
                                    }`}
                                title="预览模式"
                            >
                                <Eye size={18} />
                            </button>
                        </div>

                        {/* Cover Button */}
                        <button
                            onClick={handleGenerateCover}
                            disabled={isGeneratingImage || !note.content}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors ${isGeneratingImage
                                ? 'bg-pink-50 text-pink-400'
                                : 'bg-pink-50 text-pink-600 hover:bg-pink-100'
                                }`}
                            title="生成封面图片"
                        >
                            {isGeneratingImage ? (
                                <Loader size={16} className="animate-spin" />
                            ) : (
                                <ImageIcon size={16} />
                            )}
                            <span className="hidden sm:inline">封面</span>
                        </button>

                        {/* Critique Button */}
                        <button
                            onClick={handleCritique}
                            disabled={isCritiquing || !note.content}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors ${isCritiquing
                                ? 'bg-red-50 text-red-400'
                                : 'bg-red-50 text-red-600 hover:bg-red-100'
                                }`}
                            title="AI 深度批判"
                        >
                            {isCritiquing ? (
                                <Loader size={16} className="animate-spin" />
                            ) : (
                                <ShieldAlert size={16} />
                            )}
                            <span className="hidden sm:inline">批判</span>
                        </button>

                        {/* Brainstorm Button */}
                        <button
                            onClick={handleBrainstorm}
                            disabled={isBrainstorming || !note.content}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors ${isBrainstorming
                                ? 'bg-yellow-50 text-yellow-400'
                                : 'bg-yellow-50 text-yellow-600 hover:bg-yellow-100'
                                }`}
                            title="基于此笔记生成新灵感"
                        >
                            {isBrainstorming ? (
                                <Loader size={16} className="animate-spin" />
                            ) : (
                                <Lightbulb size={16} />
                            )}
                            <span className="hidden sm:inline">灵感</span>
                        </button>
                    </div>
                </div>

                {/* Flashcard Viewer Overlay */}
                {showFlashcards && (
                    <div className="mb-6 bg-slate-900 rounded-xl p-6 text-white relative animate-in fade-in zoom-in-95">
                        <div className="flex justify-between items-center mb-4">
                            <h4 className="text-lg font-bold flex items-center gap-2">
                                <GalleryVerticalEnd size={20} className="text-green-400" />
                                知识闪卡 ({flashcards.length})
                            </h4>
                            <X
                                size={20}
                                className="text-slate-400 cursor-pointer hover:text-white"
                                onClick={() => setShowFlashcards(false)}
                            />
                        </div>

                        {isGeneratingFlashcards ? (
                            <div className="h-40 flex items-center justify-center text-slate-400 gap-3">
                                <Loader className="animate-spin" /> 正在生成闪卡...
                            </div>
                        ) : flashcards.length > 0 ? (
                            <FlashcardDeck cards={flashcards} />
                        ) : (
                            <div className="h-40 flex items-center justify-center text-slate-400">
                                生成失败，请重试。
                            </div>
                        )}
                    </div>
                )}

                {/* Brainstorming Results Area */}
                {brainstormIdeas.length > 0 && (
                    <div className="mb-6 bg-yellow-50 border border-yellow-100 rounded-xl p-4 animate-in fade-in slide-in-from-top-2">
                        <div className="flex justify-between items-center mb-3">
                            <h4 className="text-sm font-bold text-yellow-800 flex items-center gap-2">
                                <Sparkles size={14} /> AI 灵感推荐
                            </h4>
                            <X
                                size={14}
                                className="text-yellow-400 cursor-pointer hover:text-yellow-600"
                                onClick={() => setBrainstormIdeas([])}
                            />
                        </div>
                        <div className="grid grid-cols-1 gap-2">
                            {brainstormIdeas.map((idea, idx) => (
                                <div
                                    key={idx}
                                    className="bg-white p-3 rounded-lg border border-yellow-100 shadow-sm flex justify-between items-center group hover:shadow-md transition-all"
                                >
                                    <div>
                                        <p className="font-semibold text-slate-800 text-sm">{idea.title}</p>
                                        <p className="text-xs text-slate-500">{idea.desc}</p>
                                    </div>
                                    <button
                                        onClick={() =>
                                            createNote(
                                                idea.title,
                                                `# ${idea.title}\n\n> 灵感来源：[${note.title}]\n\n${idea.desc}`
                                            )
                                        }
                                        className="opacity-0 group-hover:opacity-100 px-3 py-1 bg-blue-50 text-blue-600 text-xs rounded-full hover:bg-blue-100 transition-all font-medium"
                                    >
                                        创建笔记
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Tags */}
                <div className="flex flex-wrap gap-2 mb-6 items-center">
                    {note.tags.map((tag) => (
                        <span
                            key={tag}
                            className="px-3 py-1 bg-blue-100 text-blue-600 rounded-full text-sm font-medium flex items-center gap-1"
                        >
                            #{tag}
                            <X
                                size={12}
                                className="cursor-pointer hover:text-blue-800"
                                onClick={() => handleRemoveTag(tag)}
                            />
                        </span>
                    ))}

                    <button
                        className="px-3 py-1 border border-dashed border-slate-300 text-slate-400 rounded-full text-sm hover:border-blue-300 hover:text-blue-500 flex items-center gap-1"
                        onClick={handleAddTag}
                    >
                        <Plus size={12} /> 添加标签
                    </button>

                    {/* Smart Tags Button */}
                    <div className="relative group">
                        <button
                            className={`px-3 py-1 bg-purple-50 text-purple-600 rounded-full text-sm hover:bg-purple-100 flex items-center gap-1 transition-all ${isSuggestingTags ? 'opacity-70 cursor-wait' : ''
                                }`}
                            onClick={handleGenerateSmartTags}
                            disabled={isSuggestingTags || !note.content}
                        >
                            {isSuggestingTags ? (
                                <Loader size={12} className="animate-spin" />
                            ) : (
                                <Sparkles size={12} />
                            )}
                            {isSuggestingTags ? '生成中...' : '智能推荐'}
                        </button>

                        {/* Suggested Tags Dropdown */}
                        {suggestedTags.length > 0 && (
                            <div className="absolute top-full mt-2 left-0 bg-white shadow-xl border border-purple-100 p-3 rounded-lg w-56 z-20 animate-in fade-in zoom-in-95 duration-200">
                                <div className="flex justify-between items-center mb-2">
                                    <p className="text-xs text-purple-600 font-semibold uppercase flex items-center gap-1">
                                        <Sparkles size={10} /> AI 推荐
                                    </p>
                                    <X
                                        size={12}
                                        className="cursor-pointer text-slate-400 hover:text-slate-600"
                                        onClick={() => setSuggestedTags([])}
                                    />
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                    {suggestedTags.map((tag) => (
                                        <button
                                            key={tag}
                                            onClick={() => handleAddSuggestedTag(tag)}
                                            className="text-xs bg-purple-50 hover:bg-purple-100 text-purple-700 px-2 py-1 rounded transition-colors"
                                        >
                                            + {tag}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Editor / Preview Area */}
                <div className="relative w-full h-[calc(100%-150px)]">
                    {viewMode === 'edit' ? (
                        <>
                            <textarea
                                value={note.content}
                                onChange={(e) => handleContentChange(e.target.value)}
                                className="w-full h-full resize-none outline-none text-lg text-slate-700 leading-relaxed font-mono p-1"
                                placeholder="开始输入内容... (支持 Markdown)"
                            />
                            {note.content.length > 20 && (
                                <button
                                    onClick={handleContinueWriting}
                                    disabled={isContinuing}
                                    className={`absolute bottom-4 right-4 flex items-center gap-2 px-3 py-1.5 bg-white/90 backdrop-blur border border-purple-200 text-purple-600 rounded-full shadow-sm hover:bg-purple-50 hover:shadow-md transition-all text-xs font-medium z-10 ${isContinuing ? 'opacity-70' : ''
                                        }`}
                                >
                                    {isContinuing ? (
                                        <Loader size={12} className="animate-spin" />
                                    ) : (
                                        <PenTool size={12} />
                                    )}
                                    {isContinuing ? '续写中...' : '✨ 续写'}
                                </button>
                            )}
                        </>
                    ) : (
                        <SimpleMarkdown content={note.content} />
                    )}
                </div>
            </div>

            {/* Editor Footer / AI Tools */}
            <div className="h-16 border-t border-slate-100 px-6 flex items-center justify-between bg-white">
                <div className="flex gap-2 items-center overflow-x-auto no-scrollbar">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-2">
                        AI 工具箱:
                    </span>

                    {/* Summary */}
                    <button
                        onClick={handleGenerateSummary}
                        disabled={isSummarizing || !note.content}
                        className={`text-sm flex flex-shrink-0 items-center gap-1 px-3 py-1.5 rounded-md transition-all ${isSummarizing
                            ? 'bg-purple-50 text-purple-400'
                            : 'text-slate-600 hover:bg-slate-100 hover:text-purple-600'
                            }`}
                        title="生成摘要"
                    >
                        {isSummarizing ? <Loader size={16} className="animate-spin" /> : <Cpu size={16} />}
                        <span className="hidden lg:inline">摘要</span>
                    </button>

                    {/* Tasks */}
                    <button
                        onClick={handleExtractTasks}
                        disabled={isExtractingTasks || !note.content}
                        className={`text-sm flex flex-shrink-0 items-center gap-1 px-3 py-1.5 rounded-md transition-all ${isExtractingTasks
                            ? 'bg-green-50 text-green-400'
                            : 'text-slate-600 hover:bg-slate-100 hover:text-green-600'
                            }`}
                        title="提取待办事项"
                    >
                        {isExtractingTasks ? (
                            <Loader size={16} className="animate-spin" />
                        ) : (
                            <ListChecks size={16} />
                        )}
                        <span className="hidden lg:inline">待办</span>
                    </button>

                    {/* Polish */}
                    <button
                        onClick={handlePolish}
                        disabled={isPolishing || !note.content}
                        className={`text-sm flex flex-shrink-0 items-center gap-1 px-3 py-1.5 rounded-md transition-all ${isPolishing
                            ? 'bg-pink-50 text-pink-400'
                            : 'text-slate-600 hover:bg-slate-100 hover:text-pink-600'
                            }`}
                        title="润色文本"
                    >
                        {isPolishing ? <Loader size={16} className="animate-spin" /> : <Wand2 size={16} />}
                        <span className="hidden lg:inline">润色</span>
                    </button>

                    {/* Translate */}
                    <button
                        onClick={handleTranslate}
                        disabled={isTranslating || !note.content}
                        className={`text-sm flex flex-shrink-0 items-center gap-1 px-3 py-1.5 rounded-md transition-all ${isTranslating
                            ? 'bg-orange-50 text-orange-400'
                            : 'text-slate-600 hover:bg-slate-100 hover:text-orange-600'
                            }`}
                        title="翻译"
                    >
                        {isTranslating ? (
                            <Loader size={16} className="animate-spin" />
                        ) : (
                            <Languages size={16} />
                        )}
                        <span className="hidden lg:inline">翻译</span>
                    </button>

                    {/* Flashcards */}
                    <button
                        onClick={handleGenerateFlashcards}
                        disabled={isGeneratingFlashcards || !note.content}
                        className={`text-sm flex flex-shrink-0 items-center gap-1 px-3 py-1.5 rounded-md transition-all ${isGeneratingFlashcards
                            ? 'bg-cyan-50 text-cyan-400'
                            : 'text-slate-600 hover:bg-slate-100 hover:text-cyan-600'
                            }`}
                        title="生成闪卡"
                    >
                        {isGeneratingFlashcards ? (
                            <Loader size={16} className="animate-spin" />
                        ) : (
                            <GalleryVerticalEnd size={16} />
                        )}
                        <span className="hidden lg:inline">闪卡</span>
                    </button>
                </div>

                <div className="flex gap-3 pl-2 border-l border-slate-100 items-center">
                    {/* Save Status Indicator */}
                    <div className={`flex items-center gap-1.5 text-xs font-medium transition-colors ${saveStatus === 'saved' ? 'text-green-600' :
                            saveStatus === 'saving' ? 'text-blue-600' : 'text-amber-600'
                        }`}>
                        {saveStatus === 'saved' && <Check size={14} />}
                        {saveStatus === 'saving' && <Loader size={14} className="animate-spin" />}
                        {saveStatus === 'unsaved' && <Save size={14} />}
                        <span className="hidden sm:inline">
                            {saveStatus === 'saved' ? '已保存' :
                                saveStatus === 'saving' ? '保存中...' : '待保存'}
                        </span>
                    </div>

                    <button
                        onClick={() => deleteNote(note.id)}
                        className="text-slate-400 hover:text-red-500 transition-colors p-2"
                    >
                        <Trash2 size={18} />
                    </button>
                </div>
            </div>
        </div>
    );
};
