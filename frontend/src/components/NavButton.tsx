'use client';

import React from 'react';

interface NavButtonProps {
    active: boolean;
    onClick: () => void;
    icon: React.ReactNode;
    label: string;
}

export const NavButton: React.FC<NavButtonProps> = ({ active, onClick, icon, label }) => (
    <button
        onClick={onClick}
        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${active
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20'
                : 'text-slate-400 hover:bg-slate-800 hover:text-white'
            }`}
    >
        {icon}
        <span className="font-medium hidden md:block">{label}</span>
        {active && <div className="ml-auto w-1.5 h-1.5 bg-white rounded-full hidden md:block" />}
    </button>
);
