"use client";

import React, { useState, useEffect } from "react";
import { X, Sparkles, Download, Check, Info, Search, Code, Database, BarChart, Globe } from "lucide-react";

interface SkillsStoreModalProps {
    isOpen: boolean;
    onClose: () => void;
    onChanged: () => void;
}

const IconMap: Record<string, React.ElementType> = {
    Search,
    Code,
    Database,
    BarChart,
    Globe,
    Sparkles
};

export default function SkillsStoreModal({ isOpen, onClose, onChanged }: SkillsStoreModalProps) {
    const [skills, setSkills] = useState<Record<string, any>>({});
    const [existingAgents, setExistingAgents] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [isFetchingMore, setIsFetchingMore] = useState(false);
    const [installingId, setInstallingId] = useState<string | null>(null);
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    const fetchData = React.useCallback(async (p: number = 1) => {
        if (p === 1) setLoading(true);
        else setIsFetchingMore(true);

        try {
            const [storeRes, agentsRes] = await Promise.all([
                fetch(`${apiUrl}/api/store/skills?page=${p}&page_size=16`),
                p === 1 ? fetch(`${apiUrl}/api/agents/custom`) : Promise.resolve(null)
            ]);
            
            const storeData = await storeRes.json();
            const newSkills = storeData.items || {};
            
            setSkills(prev => p === 1 ? newSkills : { ...prev, ...newSkills });
            
            if (agentsRes) {
                setExistingAgents(await agentsRes.json());
            }

            // Check if we have more pages
            if (storeData.pages) {
                setHasMore(p < storeData.pages);
            } else {
                setHasMore(false);
            }
        } catch (err) {
            console.error("Failed to fetch skills data:", err);
            setHasMore(false);
        } finally {
            setLoading(false);
            setIsFetchingMore(false);
        }
    }, [apiUrl]);

    useEffect(() => {
        if (isOpen) {
            setPage(1);
            fetchData(1);
        }
    }, [isOpen, fetchData]);

    const handleLoadMore = () => {
        const nextPage = page + 1;
        setPage(nextPage);
        fetchData(nextPage);
    };

    const handleInstall = async (id: string, skill: any) => {
        setInstallingId(id);
        try {
            // For ClawHub skills, we might need to derive fields from metadata if missing
            const payload = {
                id: id,
                name: skill.name,
                description: skill.description,
                system_prompt: skill.system_prompt || `You are ${skill.name}. ${skill.description}`,
                mcp_servers: skill.mcp_servers || [],
                static_tools: skill.static_tools || []
            };

            const res = await fetch(`${apiUrl}/api/agents/custom`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                // Refresh agents list
                const agentsRes = await fetch(`${apiUrl}/api/agents/custom`);
                setExistingAgents(await agentsRes.json());
                onChanged();
            }
        } catch (err) {
            console.error("Failed to install skill:", err);
        } finally {
            setInstallingId(null);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-md p-4" onClick={onClose}>
            <div className="bg-neutral-900 border border-neutral-800 w-full max-w-3xl rounded-3xl overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-200" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="p-6 border-b border-neutral-800 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-purple-500/10 rounded-xl">
                            <Sparkles className="w-5 h-5 text-purple-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Skill Store</h2>
                            <p className="text-xs text-neutral-500 uppercase tracking-widest font-mono">Agent Templates & Specialized Personas</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-neutral-800 rounded-xl text-neutral-400 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <div className="p-6 max-h-[70vh] overflow-y-auto custom-scrollbar">
                    {loading ? (
                        <div className="py-20 text-center text-neutral-600 animate-pulse font-mono uppercase tracking-widest text-xs">
                            Accessing Template Registry...
                        </div>
                    ) : (
                        <div className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {Object.entries(skills).map(([id, skill]) => {
                                    const isInstalled = existingAgents.some(a => a.id === id);
                                    const Icon = IconMap[skill.icon] || Sparkles;

                                    return (
                                        <div key={id} className="group p-5 bg-neutral-800/20 border border-neutral-800/50 rounded-2xl flex flex-col gap-4 hover:border-purple-500/30 transition-all hover:bg-neutral-800/40">
                                            <div className="flex items-start justify-between">
                                                <div className="p-3 bg-neutral-900 rounded-xl border border-neutral-800 group-hover:border-purple-500/20 transition-colors">
                                                    <Icon className="w-5 h-5 text-purple-400" />
                                                </div>
                                                {isInstalled ? (
                                                    <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-500 text-[10px] font-bold uppercase tracking-widest rounded-full border border-emerald-500/20">
                                                        <Check size={10} /> Active
                                                    </div>
                                                ) : (
                                                    <button
                                                        onClick={() => handleInstall(id, skill)}
                                                        disabled={installingId === id}
                                                        className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-[10px] font-bold uppercase tracking-widest rounded-xl transition-all shadow-lg shadow-purple-500/10 disabled:opacity-50"
                                                    >
                                                        <Download size={12} /> {installingId === id ? 'Installing...' : 'Install'}
                                                    </button>
                                                )}
                                            </div>
                                            <div>
                                                <h3 className="font-bold text-neutral-100 text-lg">{skill.name}</h3>
                                                <p className="text-xs text-neutral-500 mt-1 leading-relaxed line-clamp-2">{skill.description}</p>
                                            </div>

                                            <div className="flex flex-wrap gap-1.5 pt-2">
                                                {(skill.mcp_servers || []).map((s: string) => (
                                                    <span key={s} className="px-2 py-0.5 bg-neutral-900 text-[9px] text-neutral-400 font-mono rounded border border-neutral-800">
                                                        @{s}
                                                    </span>
                                                ))}
                                                {(skill.static_tools || []).map((t: string) => (
                                                    <span key={t} className="px-2 py-0.5 bg-blue-500/5 text-[9px] text-blue-400/70 font-mono rounded border border-blue-500/10">
                                                        {t}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {hasMore && (
                                <div className="flex justify-center pt-4">
                                    <button
                                        onClick={handleLoadMore}
                                        disabled={isFetchingMore}
                                        className="px-6 py-3 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-bold uppercase tracking-widest rounded-2xl border border-neutral-700 transition-all disabled:opacity-50"
                                    >
                                        {isFetchingMore ? 'Loading more...' : 'Load More Skills'}
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div className="p-5 border-t border-neutral-800 bg-neutral-950/50 flex items-center gap-3">
                    <Info className="w-4 h-4 text-neutral-500" />
                    <p className="text-[10px] text-neutral-500 font-medium">
                        Skills are fetched live from ClawHub.ai. Installing a skill creates a pre-configured Custom Agent.
                    </p>
                </div>
            </div>
        </div>
    );
}
