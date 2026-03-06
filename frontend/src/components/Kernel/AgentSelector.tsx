"use client";

import React, { useState, useEffect, useCallback } from "react";
import { User, Settings, ChevronDown, Plus, Sparkles, Cpu } from "lucide-react";
import CustomAgentManagerModal from "./CustomAgentManagerModal";

export interface CustomAgent {
    id: string;
    name: string;
    description: string;
    system_prompt?: string;
    mcp_servers: string[];
    static_tools: string[];
    provider?: string;
    model?: string;
}

interface AgentSelectorProps {
    onSelect: (agent: CustomAgent | null) => void;
    currentAgentId: string | null;
}

export default function AgentSelector({ onSelect, currentAgentId }: AgentSelectorProps) {
    const [agents, setAgents] = useState<CustomAgent[]>([]);
    const [isOpen, setIsOpen] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    const fetchAgents = useCallback(async () => {
        try {
            const res = await fetch(`${apiUrl}/api/agents/custom`);
            const data = await res.json();
            setAgents(data);
        } catch (err) {
            console.error("Failed to fetch custom agents:", err);
        }
    }, [apiUrl]);

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            if (isMounted) await fetchAgents();
        };
        load();
        return () => { isMounted = false; };
    }, [fetchAgents]);

    const selectedAgent = agents.find(a => a.id === currentAgentId) || null;

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-3 px-4 py-2 bg-neutral-900 border border-neutral-800 rounded-2xl hover:border-neutral-700 transition-all group min-w-[200px]"
            >
                <div className="p-1.5 bg-blue-500/10 rounded-lg group-hover:bg-blue-500/20 transition-colors">
                    <User className="w-4 h-4 text-blue-400" />
                </div>
                <div className="flex flex-col items-start flex-grow text-left">
                    <span className="text-[10px] text-neutral-500 uppercase font-black tracking-widest leading-none mb-1">Active Persona</span>
                    <span className="text-sm font-bold text-neutral-200 truncate max-w-[120px]">
                        {selectedAgent ? selectedAgent.name : "Kernel Default"}
                    </span>
                </div>
                <ChevronDown className={`w-4 h-4 text-neutral-500 transition-transform ${isOpen ? "rotate-180" : ""}`} />
            </button>

            {isOpen && (
                <>
                    <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
                    <div className="absolute top-full mt-2 left-0 w-[280px] bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                        <div className="p-2 border-b border-neutral-800 bg-neutral-950/30">
                            <div className="flex items-center justify-between px-2 py-1">
                                <span className="text-[10px] text-neutral-500 uppercase font-black tracking-widest">Available Personalities</span>
                                <button
                                    onClick={() => { setIsModalOpen(true); setIsOpen(false); }}
                                    className="p-1 hover:bg-neutral-800 rounded-lg text-blue-400 transition-colors"
                                    title="Create Custom Persona"
                                >
                                    <Plus size={14} />
                                </button>
                            </div>
                        </div>

                        <div className="max-h-[300px] overflow-y-auto p-1 custom-scrollbar">
                            {/* Default Option */}
                            <button
                                onClick={() => { onSelect(null); setIsOpen(false); }}
                                className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all text-left ${!currentAgentId ? "bg-blue-500/10 text-blue-100" : "hover:bg-neutral-800/50 text-neutral-400 hover:text-neutral-200"}`}
                            >
                                <div className={`p-2 rounded-lg ${!currentAgentId ? "bg-blue-500/20" : "bg-neutral-800"}`}>
                                    <Cpu size={16} />
                                </div>
                                <div>
                                    <div className="text-sm font-bold">Kernel Default</div>
                                    <div className="text-[10px] opacity-60">System-wide standard capability</div>
                                </div>
                            </button>

                            {agents.map(agent => (
                                <button
                                    key={agent.id}
                                    onClick={() => { onSelect(agent); setIsOpen(false); }}
                                    className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all text-left ${currentAgentId === agent.id ? "bg-purple-500/10 text-purple-100" : "hover:bg-neutral-800/50 text-neutral-400 hover:text-neutral-200"}`}
                                >
                                    <div className={`p-2 rounded-lg ${currentAgentId === agent.id ? "bg-purple-500/20" : "bg-neutral-800"}`}>
                                        <Sparkles size={16} />
                                    </div>
                                    <div className="flex-grow min-w-0">
                                        <div className="text-sm font-bold truncate">{agent.name}</div>
                                        <div className="text-[10px] opacity-60 truncate">{agent.description}</div>
                                    </div>
                                </button>
                            ))}
                        </div>

                        <div className="p-2 border-t border-neutral-800 bg-neutral-950/30">
                            <button
                                onClick={() => { setIsModalOpen(true); setIsOpen(false); }}
                                className="w-full flex items-center justify-center gap-2 py-2 text-[10px] text-neutral-500 hover:text-blue-400 transition-colors font-black uppercase tracking-widest"
                            >
                                <Settings size={12} />
                                Configure Personas
                            </button>
                        </div>
                    </div>
                </>
            )}

            <CustomAgentManagerModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onChanged={fetchAgents}
            />
        </div>
    );
}
