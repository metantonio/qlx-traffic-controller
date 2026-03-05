'use client';

import React, { useState, useEffect, useRef } from 'react';
import { X, Send, Terminal, User, Cpu, Activity } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

export interface Message {
    role: 'user' | 'assistant' | 'system' | 'tool';
    content: string;
    tool_calls?: Record<string, unknown>[];
    tool_call_id?: string;
}

interface Process {
    state: string;
    agent_name: string;
    task: string;
    history: Message[];
}

interface AgentConversationModalProps {
    pid: string;
    onClose: () => void;
    onContinue: (pid: string, task: string, history: Message[]) => void;
}

export default function AgentConversationModal({ pid, onClose, onContinue }: AgentConversationModalProps) {
    const [procDetails, setProcDetails] = useState<Process | null>(null);
    const [loading, setLoading] = useState(true);
    const [followUp, setFollowUp] = useState('');
    const scrollRef = useRef<HTMLDivElement>(null);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

    useEffect(() => {
        fetch(`${apiUrl}/api/processes/${pid}`)
            .then(res => res.json())
            .then(data => {
                setProcDetails(data);
                setLoading(false);
            })
            .catch(err => console.error('Failed to fetch process details:', err));
    }, [pid, apiUrl]);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [procDetails]);

    const handleSend = () => {
        if (!followUp.trim() || !procDetails) return;
        onContinue(pid, followUp, procDetails.history);
        onClose();
    };

    if (loading) return null;

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={onClose}
        >
            <div
                className="bg-neutral-900/90 border border-neutral-800 w-full max-w-4xl h-[80vh] rounded-2xl flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200"
                onClick={(e) => e.stopPropagation()}
            >

                {/* Header */}
                <div className="p-4 border-b border-neutral-800 flex items-center justify-between bg-neutral-900">
                    <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${procDetails?.state === 'completed' ? 'bg-emerald-500' : 'bg-amber-500'} animate-pulse`} />
                        <div>
                            <h3 className="text-white font-semibold flex items-center gap-2">
                                Agent: {procDetails?.agent_name}
                                <span className="text-xs font-mono text-neutral-500 bg-neutral-800 px-2 py-0.5 rounded">PID: {pid}</span>
                            </h3>
                            <p className="text-xs text-neutral-400 truncate max-w-md">{procDetails?.task}</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-neutral-800 rounded-lg text-neutral-400 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Conversation Body */}
                <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-neutral-800">
                    {procDetails?.history?.map((msg: Message, idx: number) => {
                        if (msg.role === 'system' && idx === 0) return null; // Skip initial system prompt for cleaner UI

                        const isUser = msg.role === 'user';
                        const isTool = msg.role === 'tool';

                        return (
                            <div key={idx} className={`flex gap-4 ${isUser ? 'flex-row-reverse' : ''}`}>
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 
                  ${isUser ? 'bg-blue-600/20 text-blue-400' : isTool ? 'bg-neutral-800 text-neutral-400' : 'bg-emerald-600/20 text-emerald-400'}`}>
                                    {isUser ? <User size={16} /> : isTool ? <Terminal size={16} /> : <Cpu size={16} />}
                                </div>

                                <div className={`max-w-[80%] space-y-2`}>
                                    <div className={`p-4 rounded-2xl border ${isUser ? 'bg-blue-600 border-blue-500 text-white' : 'bg-neutral-800/50 border-neutral-700 text-neutral-200'}`}>
                                        <MarkdownRenderer content={msg.content} />

                                        {msg.tool_calls && msg.tool_calls.length > 0 && (
                                            <div className="mt-3 pt-3 border-t border-white/10 space-y-2">
                                                {msg.tool_calls.map((tc: Record<string, unknown>, tIdx: number) => (
                                                    <div key={tIdx} className="flex items-center gap-2 text-xs font-mono bg-black/20 p-2 rounded border border-white/5">
                                                        <Activity size={12} className="text-amber-400" />
                                                        <span className="text-amber-200">Executing:</span>
                                                        {(tc.name as string)}({JSON.stringify(tc.args)})
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Footer / Input */}
                <div className="p-4 border-t border-neutral-800 bg-neutral-900/50">
                    <div className="flex gap-4 items-center max-w-3xl mx-auto">
                        <div className="relative flex-1 group">
                            <input
                                value={followUp}
                                onChange={(e) => setFollowUp(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                                placeholder="Continue conversation with this context..."
                                className="w-full bg-neutral-800 border border-neutral-700 text-white rounded-xl py-3 px-4 outline-none focus:border-emerald-500/50 transition-all focus:ring-1 focus:ring-emerald-500/20 pr-12 group-hover:border-neutral-600"
                            />
                            <button
                                onClick={handleSend}
                                disabled={!followUp.trim()}
                                className="absolute right-2 top-1.5 p-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:hover:bg-emerald-600 text-white rounded-lg transition-all"
                            >
                                <Send size={18} />
                            </button>
                        </div>
                    </div>
                    <p className="text-[10px] text-center text-neutral-500 mt-2 uppercase tracking-widest font-medium"> Resumption Mode Active • PID: {pid} Context Linked </p>
                </div>
            </div>
        </div>
    );
}
