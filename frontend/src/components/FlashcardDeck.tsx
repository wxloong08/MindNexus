'use client';

import React, { useState } from 'react';
import { ArrowLeft, ArrowRight } from 'lucide-react';

interface Flashcard {
    front: string;
    back: string;
}

interface FlashcardDeckProps {
    cards: Flashcard[];
}

export const FlashcardDeck: React.FC<FlashcardDeckProps> = ({ cards }) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isFlipped, setIsFlipped] = useState(false);

    const nextCard = () => {
        setIsFlipped(false);
        setTimeout(() => setCurrentIndex((prev) => (prev + 1) % cards.length), 200);
    };

    const prevCard = () => {
        setIsFlipped(false);
        setTimeout(() => setCurrentIndex((prev) => (prev - 1 + cards.length) % cards.length), 200);
    };

    if (cards.length === 0) {
        return <div className="h-40 flex items-center justify-center text-slate-400">没有闪卡</div>;
    }

    return (
        <div className="flex flex-col items-center">
            <div
                className="w-full h-64 relative perspective cursor-pointer group"
                onClick={() => setIsFlipped(!isFlipped)}
            >
                <div
                    className={`w-full h-full duration-500 preserve-3d absolute ${isFlipped ? 'rotate-y-180' : ''}`}
                >
                    {/* Front */}
                    <div className="absolute backface-hidden w-full h-full bg-slate-800 border border-slate-700 rounded-xl p-8 flex flex-col items-center justify-center text-center shadow-lg group-hover:border-slate-600 transition-colors">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">
                            Front (问题)
                        </span>
                        <h3 className="text-xl font-medium text-white">{cards[currentIndex].front}</h3>
                        <p className="absolute bottom-4 text-xs text-slate-500">点击翻转</p>
                    </div>
                    {/* Back */}
                    <div className="absolute backface-hidden rotate-y-180 w-full h-full bg-indigo-900 border border-indigo-700 rounded-xl p-8 flex flex-col items-center justify-center text-center shadow-lg">
                        <span className="text-xs font-bold text-indigo-300 uppercase tracking-widest mb-4">
                            Back (答案)
                        </span>
                        <p className="text-lg text-white leading-relaxed">{cards[currentIndex].back}</p>
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-6 mt-6">
                <button
                    onClick={prevCard}
                    className="p-2 rounded-full hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                >
                    <ArrowLeft />
                </button>
                <span className="text-sm font-mono text-slate-400">
                    {currentIndex + 1} / {cards.length}
                </span>
                <button
                    onClick={nextCard}
                    className="p-2 rounded-full hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                >
                    <ArrowRight />
                </button>
            </div>
        </div>
    );
};
