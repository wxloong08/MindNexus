'use client';

import React, { useRef, useState, useEffect } from 'react';
import { FileText, Hash } from 'lucide-react';
import { Note, AiLink } from '@/lib/store';

interface GraphNode extends Note {
    x: number;
    y: number;
    radius: number;
    vx?: number;
    vy?: number;
}

interface GraphLink {
    source: string;
    target: string;
    strength: number;
    type: 'tag' | 'ai';
}

interface KnowledgeGraphProps {
    notes: Note[];
    aiLinks?: AiLink[];
    onNodeClick: (id: string) => void;
}

export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
    notes,
    aiLinks = [],
    onNodeClick,
}) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [nodes, setNodes] = useState<GraphNode[]>([]);
    const [links, setLinks] = useState<GraphLink[]>([]);

    // Initialize graph data
    useEffect(() => {
        const width = containerRef.current?.clientWidth || 800;
        const height = containerRef.current?.clientHeight || 600;

        // Create nodes
        const newNodes: GraphNode[] = notes.map((note) => ({
            ...note,
            x: width / 2 + (Math.random() - 0.5) * 300,
            y: height / 2 + (Math.random() - 0.5) * 300,
            radius: 20 + note.tags.length * 2, // More tags = larger node
        }));

        // Create links based on shared tags
        const tagLinks: GraphLink[] = [];
        for (let i = 0; i < newNodes.length; i++) {
            for (let j = i + 1; j < newNodes.length; j++) {
                const source = newNodes[i];
                const target = newNodes[j];
                const sharedTags = source.tags.filter((t) => target.tags.includes(t));

                if (sharedTags.length > 0) {
                    tagLinks.push({
                        source: source.id,
                        target: target.id,
                        strength: sharedTags.length,
                        type: 'tag',
                    });
                }
            }
        }

        // Merge AI-discovered links
        const validAiLinks: GraphLink[] = aiLinks
            .filter(
                (l) =>
                    newNodes.find((n) => n.id === l.source) && newNodes.find((n) => n.id === l.target)
            )
            .map((l) => ({ ...l, strength: 2, type: 'ai' as const }));

        setNodes(newNodes);
        setLinks([...tagLinks, ...validAiLinks]);
    }, [notes, aiLinks]);

    // Simple force-directed simulation
    useEffect(() => {
        let animationFrameId: number;
        let frameCount = 0;
        const maxFrames = 100; // Stop after ~3 seconds at 60fps

        const tick = () => {
            if (frameCount >= maxFrames) return;

            const width = containerRef.current?.clientWidth || 800;
            const height = containerRef.current?.clientHeight || 600;

            setNodes((prevNodes) => {
                const nextNodes = prevNodes.map((node) => ({ ...node, vx: 0, vy: 0 }));

                // 1. Repulsion force
                for (let i = 0; i < nextNodes.length; i++) {
                    for (let j = i + 1; j < nextNodes.length; j++) {
                        const dx = nextNodes[i].x - nextNodes[j].x;
                        const dy = nextNodes[i].y - nextNodes[j].y;
                        const distance = Math.sqrt(dx * dx + dy * dy) || 1;
                        if (distance < 200) {
                            const force = 1000 / (distance * distance);
                            const fx = (dx / distance) * force;
                            const fy = (dy / distance) * force;
                            nextNodes[i].vx! += fx;
                            nextNodes[i].vy! += fy;
                            nextNodes[j].vx! -= fx;
                            nextNodes[j].vy! -= fy;
                        }
                    }
                }

                // 2. Spring force for links
                links.forEach((link) => {
                    const source = nextNodes.find((n) => n.id === link.source);
                    const target = nextNodes.find((n) => n.id === link.target);
                    if (source && target) {
                        const dx = target.x - source.x;
                        const dy = target.y - source.y;
                        const distance = Math.sqrt(dx * dx + dy * dy) || 1;
                        const force = (distance - 150) * 0.005;
                        const fx = (dx / distance) * force;
                        const fy = (dy / distance) * force;
                        source.vx! += fx;
                        source.vy! += fy;
                        target.vx! -= fx;
                        target.vy! -= fy;
                    }
                });

                // 3. Center gravity
                nextNodes.forEach((node) => {
                    node.vx! += (width / 2 - node.x) * 0.005;
                    node.vy! += (height / 2 - node.y) * 0.005;
                });

                // Apply velocity
                return nextNodes.map((node) => ({
                    ...node,
                    x: node.x + (node.vx || 0),
                    y: node.y + (node.vy || 0),
                }));
            });

            frameCount++;
            animationFrameId = requestAnimationFrame(tick);
        };

        tick();

        return () => {
            cancelAnimationFrame(animationFrameId);
        };
    }, [links]);

    return (
        <div
            ref={containerRef}
            className="w-full h-full bg-slate-50 relative overflow-hidden flex items-center justify-center"
        >
            <svg className="w-full h-full absolute top-0 left-0 pointer-events-none">
                {links.map((link, i) => {
                    const source = nodes.find((n) => n.id === link.source);
                    const target = nodes.find((n) => n.id === link.target);
                    if (!source || !target) return null;
                    return (
                        <line
                            key={i}
                            x1={source.x}
                            y1={source.y}
                            x2={target.x}
                            y2={target.y}
                            stroke={link.type === 'ai' ? '#818cf8' : '#CBD5E1'}
                            strokeWidth={link.strength}
                            strokeDasharray={link.type === 'ai' ? '5,5' : '0'}
                            className={link.type === 'ai' ? 'animate-pulse' : ''}
                        />
                    );
                })}
            </svg>

            {/* Legend */}
            <div className="absolute top-4 right-4 z-10 bg-white/80 backdrop-blur p-2 rounded-lg text-xs text-slate-500 shadow-sm border border-slate-200">
                <div className="flex items-center gap-2 mb-1">
                    <div className="w-2 h-2 rounded-full bg-blue-500"></div> Markdown
                </div>
                <div className="flex items-center gap-2 mb-1">
                    <div className="w-2 h-2 rounded-full bg-red-400"></div> PDF 文档
                </div>
                <div className="border-t my-1"></div>
                <div className="flex items-center gap-2 mb-1">
                    <div className="w-4 h-0.5 bg-slate-300"></div> 标签关联
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-4 h-0.5 border-t-2 border-dashed border-indigo-400"></div> AI 语义关联
                </div>
            </div>

            {/* Nodes */}
            {nodes.map((node) => (
                <div
                    key={node.id}
                    onClick={() => onNodeClick(node.id)}
                    className="absolute cursor-pointer transform -translate-x-1/2 -translate-y-1/2 group flex flex-col items-center justify-center transition-transform hover:scale-110 z-10"
                    style={{ left: node.x, top: node.y }}
                >
                    <div
                        className={`rounded-full flex items-center justify-center shadow-md border-4 border-white transition-all group-hover:shadow-xl ${node.type === 'pdf' ? 'bg-red-50 text-red-500' : 'bg-blue-50 text-blue-500'
                            }`}
                        style={{ width: node.radius * 2, height: node.radius * 2 }}
                    >
                        {node.type === 'pdf' ? <FileText size={node.radius} /> : <Hash size={node.radius} />}
                    </div>
                    <span className="mt-2 text-xs font-semibold text-slate-700 bg-white/90 px-2 py-0.5 rounded shadow-sm whitespace-nowrap opacity-70 group-hover:opacity-100">
                        {node.title}
                    </span>
                </div>
            ))}
        </div>
    );
};
