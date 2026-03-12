"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Search, Command, Zap, ArrowRight } from 'lucide-react';

interface CommandBarProps {
    onSpawnAgent: (task: string) => void;
    onViewChange: (view: 'dashboard' | 'extensions' | 'history') => void;
    pendingCount?: number;
}

export default function CommandBar({ onSpawnAgent, onViewChange, pendingCount = 0 }: CommandBarProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [query, setQuery] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                setIsOpen(true);
            }
            if (e.key === 'Escape') {
                setIsOpen(false);
            }
        };

        window.addEventListener('keydown', handleKeyDown as any);
        return () => window.removeEventListener('keydown', handleKeyDown as any);
    }, []);

    useEffect(() => {
        if (isOpen) {
            setTimeout(() => inputRef.current?.focus(), 10);
        }
    }, [isOpen]);

    const handleAction = (type: 'nav' | 'task', value: string) => {
        if (type === 'nav') {
            onViewChange(value as any);
        } else {
            onSpawnAgent(value);
        }
        setIsOpen(false);
        setQuery('');
    };

    if (!isOpen) return (
        <button 
            onClick={() => setIsOpen(true)}
            className="fixed bottom-8 left-1/2 -translate-x-1/2 px-4 py-2 bg-neutral-900/80 border border-neutral-800 rounded-2xl backdrop-blur-xl text-neutral-500 hover:text-white hover:border-neutral-700 transition-all shadow-2xl flex items-center gap-4 group z-30"
        >
            <div className="flex items-center gap-1.5 relative">
                <Command size={14} />
                <span className="text-[10px] font-black uppercase tracking-widest">Command Center</span>
                {pendingCount > 0 && (
                    <span className="absolute -top-3 -right-3 flex h-4 w-4 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white animate-bounce shadow-lg shadow-blue-500/50">
                        {pendingCount}
                    </span>
                )}
            </div>
            <div className="h-4 w-px bg-neutral-800" />
            <span className="text-[10px] font-mono opacity-40 group-hover:opacity-100 transition-opacity">Press ⌘K to activate</span>
        </button>
    );

    return (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] px-4 backdrop-blur-sm bg-black/40 animate-in fade-in duration-200">
            <div className="fixed inset-0" onClick={() => setIsOpen(false)} />
            
            <div className="w-full max-w-2xl glass-glow rounded-3xl overflow-hidden animate-in slide-in-from-top-4 duration-300 relative z-10 shadow-2xl border-blue-500/20">
                <div className="p-6 flex items-center gap-4 border-b border-neutral-800">
                    <Search className="text-blue-500" size={20} />
                    <input
                        ref={inputRef}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Type a command or task..."
                        className="flex-1 bg-transparent border-none outline-none text-white text-lg placeholder:text-neutral-700 font-medium"
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && query.trim()) {
                                handleAction('task', query);
                            }
                        }}
                    />
                    <div className="flex items-center gap-2 px-2 py-1 bg-neutral-800 rounded-lg text-[10px] font-mono text-neutral-500">
                        ESC to close
                    </div>
                </div>

                <div className="p-2 space-y-1">
                    <div className="px-4 py-2 text-[10px] font-black text-neutral-600 uppercase tracking-widest">Navigation</div>
                    {[
                        { id: 'dashboard', label: 'Dashboard Control', icon: Zap },
                        { id: 'history', label: 'Thread Logs', icon: Search },
                        { id: 'extensions', label: 'Skill Store', icon: ArrowRight },
                    ].map(item => (
                        <button
                            key={item.id}
                            onClick={() => handleAction('nav', item.id)}
                            className="w-full flex items-center justify-between p-3 rounded-xl hover:bg-white/5 transition-all text-neutral-400 hover:text-white group"
                        >
                            <div className="flex items-center gap-3">
                                <item.icon size={16} />
                                <span className="text-sm font-bold">{item.label}</span>
                            </div>
                            <span className="text-[10px] font-mono opacity-0 group-hover:opacity-100 uppercase">Go to</span>
                        </button>
                    ))}
                    
                    <div className="mt-4 px-4 py-2 text-[10px] font-black text-neutral-600 uppercase tracking-widest">Quick Actions</div>
                    <button
                        onClick={() => handleAction('task', 'Analyze current system state')}
                        className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-blue-500/10 text-neutral-400 hover:text-blue-200 transition-all text-left"
                    >
                        <Zap size={16} className="text-blue-500" />
                        <div>
                            <div className="text-sm font-bold">System Self-Audit</div>
                            <div className="text-[10px] opacity-60 italic whitespace-nowrap overflow-hidden text-ellipsis">Spawn agent to analyze local context & memory</div>
                        </div>
                    </button>
                </div>
            </div>
        </div>
    );
}
