'use client';

import React from 'react';

interface SimpleMarkdownProps {
    content: string;
}

export const SimpleMarkdown: React.FC<SimpleMarkdownProps> = ({ content }) => {
    if (!content) return <p className="text-slate-400 italic">无内容</p>;

    const lines = content.split('\n');
    const elements: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeBlockContent: string[] = [];

    const parseInline = (text: string, keyPrefix: string): React.ReactNode[] => {
        const parts = text.split(/(\*\*.*?\*\*|`.*?`|\[.*?\])/g);
        return parts.map((part, idx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
                return (
                    <strong key={`${keyPrefix}-${idx}`} className="font-bold text-slate-900">
                        {part.slice(2, -2)}
                    </strong>
                );
            }
            if (part.startsWith('`') && part.endsWith('`')) {
                return (
                    <code
                        key={`${keyPrefix}-${idx}`}
                        className="bg-slate-100 text-red-500 px-1 py-0.5 rounded font-mono text-sm border border-slate-200"
                    >
                        {part.slice(1, -1)}
                    </code>
                );
            }
            return part;
        });
    };

    lines.forEach((line, i) => {
        // Code Block handling
        if (line.trim().startsWith('```')) {
            if (inCodeBlock) {
                // End of block
                elements.push(
                    <pre
                        key={`code-${i}`}
                        className="bg-slate-800 text-blue-100 p-4 rounded-lg my-4 overflow-x-auto font-mono text-sm border border-slate-700 shadow-sm"
                    >
                        <code>{codeBlockContent.join('\n')}</code>
                    </pre>
                );
                codeBlockContent = [];
                inCodeBlock = false;
            } else {
                // Start of block
                inCodeBlock = true;
            }
            return;
        }
        if (inCodeBlock) {
            codeBlockContent.push(line);
            return;
        }

        // Image handling
        if (line.trim().startsWith('![') && line.includes('](')) {
            const altText = line.substring(2, line.indexOf(']'));
            const url = line.substring(line.indexOf('](') + 2, line.lastIndexOf(')'));
            elements.push(
                <div key={i} className="my-4 rounded-xl overflow-hidden shadow-md">
                    <img src={url} alt={altText} className="w-full h-auto object-cover" />
                </div>
            );
            return;
        }

        // Headers
        if (line.startsWith('# ')) {
            elements.push(
                <h1 key={i} className="text-3xl font-bold text-slate-900 mb-4 mt-8 pb-2 border-b border-slate-100">
                    {line.substring(2)}
                </h1>
            );
            return;
        }
        if (line.startsWith('## ')) {
            elements.push(
                <h2 key={i} className="text-2xl font-bold text-slate-800 mb-3 mt-6">
                    {line.substring(3)}
                </h2>
            );
            return;
        }
        if (line.startsWith('### ')) {
            elements.push(
                <h3 key={i} className="text-xl font-bold text-slate-800 mb-2 mt-5">
                    {line.substring(4)}
                </h3>
            );
            return;
        }

        // Blockquotes
        if (line.startsWith('> ')) {
            const isAISummary = line.includes('AI 摘要') || line.includes('灵感来源');
            elements.push(
                <blockquote
                    key={i}
                    className={`border-l-4 ${isAISummary ? 'border-purple-500 bg-purple-50' : 'border-slate-300 bg-slate-50'
                        } pl-4 py-3 pr-4 italic text-slate-700 my-4 rounded-r`}
                >
                    {line.substring(2)}
                </blockquote>
            );
            return;
        }

        // Unordered Lists
        if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
            const listContent = line.trim().substring(2);
            elements.push(
                <li key={i} className="ml-6 list-disc mb-1 text-slate-700">
                    {parseInline(listContent, `li-${i}`)}
                </li>
            );
            return;
        }

        // Ordered Lists
        if (line.trim().match(/^\d+\. /)) {
            const match = line.trim().match(/^(\d+)\. (.*)$/);
            if (match) {
                const [, num, content] = match;
                elements.push(
                    <div key={i} className="ml-6 mb-1 text-slate-700 flex gap-2">
                        <span className="font-mono text-slate-400 font-bold select-none">{num}.</span>
                        <span>{parseInline(content, `ol-${i}`)}</span>
                    </div>
                );
            }
            return;
        }

        // Empty lines
        if (line.trim() === '') {
            elements.push(<div key={i} className="h-2" />);
            return;
        }

        // Regular Paragraphs
        elements.push(
            <p key={i} className="mb-2 leading-7 text-slate-700">
                {parseInline(line, `p-${i}`)}
            </p>
        );
    });

    return <div className="markdown-body w-full h-full overflow-y-auto pr-2 pb-10">{elements}</div>;
};
