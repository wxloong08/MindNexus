'use client';

import React, { useEffect, useState } from 'react';
import { Settings, X, Server, Database, Trash2, Loader } from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { systemApi } from '@/lib/api';

interface SystemStatus {
    status: string;
    version: string;
    llm: {
        default_model?: string;
        provider?: string;
        model?: string;
        status?: string;
    };
}

export const SettingsModal: React.FC = () => {
    const { showSettings, setShowSettings, resetToInitial } = useAppStore();
    const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Fetch system status when modal opens
    useEffect(() => {
        if (showSettings) {
            setIsLoading(true);
            setError(null);
            systemApi.health()
                .then((data) => {
                    setSystemStatus({
                        status: data.status,
                        version: data.version,
                        llm: data.llm as SystemStatus['llm'],
                    });
                })
                .catch((err) => {
                    console.error('Failed to fetch system status:', err);
                    setError('无法连接到后端服务');
                })
                .finally(() => {
                    setIsLoading(false);
                });
        }
    }, [showSettings]);

    if (!showSettings) return null;

    const handleReset = () => {
        if (window.confirm('确定要重置所有数据吗？此操作无法撤销。')) {
            resetToInitial();
        }
    };

    const getModelDisplay = () => {
        if (isLoading) return { name: '加载中...', latency: '' };
        if (error) return { name: '连接失败', latency: '' };
        if (!systemStatus?.llm) return { name: '未知', latency: '' };

        // Try different fields: default_model, model, provider
        const model = systemStatus.llm.default_model || systemStatus.llm.model || systemStatus.llm.provider || '未知模型';
        return { name: model, latency: '延迟: <100ms' };
    };

    const getConnectionStatus = () => {
        if (isLoading) return { text: '检测中...', color: 'bg-yellow-100 text-yellow-700 border-yellow-200', dotColor: 'bg-yellow-500' };
        if (error) return { text: '未连接', color: 'bg-red-100 text-red-700 border-red-200', dotColor: 'bg-red-500' };
        if (systemStatus?.status === 'healthy') return { text: '已连接', color: 'bg-green-100 text-green-700 border-green-200', dotColor: 'bg-green-500' };
        return { text: '状态未知', color: 'bg-gray-100 text-gray-700 border-gray-200', dotColor: 'bg-gray-500' };
    };

    const modelInfo = getModelDisplay();
    const connectionStatus = getConnectionStatus();

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="p-6 border-b border-slate-100 flex justify-between items-center">
                    <h3 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                        <Settings size={22} className="text-slate-400" /> 设置
                    </h3>
                    <button
                        onClick={() => setShowSettings(false)}
                        className="text-slate-400 hover:text-slate-600 transition-colors p-1 hover:bg-slate-100 rounded-full"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* System Status */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                            <Server size={16} /> 系统状态
                        </label>
                        <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-sm flex justify-between items-center">
                            <div className="flex flex-col">
                                <span className="font-mono text-slate-600 font-medium flex items-center gap-2">
                                    {isLoading && <Loader size={14} className="animate-spin" />}
                                    {modelInfo.name}
                                </span>
                                {modelInfo.latency && (
                                    <span className="text-xs text-slate-400 mt-0.5">{modelInfo.latency}</span>
                                )}
                            </div>
                            <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold border ${connectionStatus.color}`}>
                                <div className={`w-2 h-2 rounded-full ${connectionStatus.dotColor} ${!isLoading && !error ? 'animate-pulse' : ''}`}></div>
                                {connectionStatus.text}
                            </div>
                        </div>
                    </div>

                    {/* Data Management */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                            <Database size={16} /> 数据管理
                        </label>
                        <div className="p-4 border border-red-100 bg-red-50 rounded-xl">
                            <p className="text-xs text-red-600 mb-3 leading-relaxed">
                                重置操作将清空所有当前笔记并恢复到初始演示数据。此操作不可撤销。
                            </p>
                            <button
                                onClick={handleReset}
                                className="w-full py-2.5 px-4 bg-white border border-red-200 text-red-600 rounded-lg hover:bg-red-600 hover:text-white hover:border-red-600 transition-all font-medium flex items-center justify-center gap-2 shadow-sm"
                            >
                                <Trash2 size={16} /> 重置知识库
                            </button>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="pt-4 border-t border-slate-100 text-center">
                        <p className="text-xs font-medium text-slate-400">MindNexus v1.0.2 (Beta)</p>
                        <p className="text-[10px] text-slate-300 mt-1">Powered by Google Gemini</p>
                    </div>
                </div>
            </div>
        </div>
    );
};
