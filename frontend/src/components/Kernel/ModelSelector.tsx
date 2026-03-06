"use client";

import React, { useEffect, useState, useCallback } from "react";
import { ChevronDown, Cpu, Globe, Zap } from "lucide-react";

interface LLMProviderInfo {
    provider: string;
    name: string;
    models: string[];
    configured: boolean;
    error?: string;
}

interface ModelSelectorProps {
    onSelect: (provider: string, model: string) => void;
    currentProvider: string;
    currentModel: string;
}

export default function ModelSelector({ onSelect, currentProvider, currentModel }: ModelSelectorProps) {
    const [providers, setProviders] = useState<LLMProviderInfo[]>([]);
    const [isOpen, setIsOpen] = useState(false);

    // Memoize onSelect to avoid unnecessary re-renders if it changes
    const handleSelect = useCallback((p: string, m: string) => {
        onSelect(p, m);
    }, [onSelect]);

    useEffect(() => {
        const fetchModels = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
                const res = await fetch(`${apiUrl}/api/llm/models`);
                const data = await res.json();
                setProviders(data);
            } catch (err) {
                console.error("Failed to fetch LLM models:", err);
            }
        };
        fetchModels();
    }, []); // Run ONLY once on mount

    // Separate effect for initial selection to avoid loop
    useEffect(() => {
        if (!currentProvider && providers.length > 0 && providers[0].models.length > 0) {
            handleSelect(providers[0].provider, providers[0].models[0]);
        }
    }, [currentProvider, providers, handleSelect]);

    const handleModelChange = (p: string, m: string) => {
        handleSelect(p, m);
        setIsOpen(false);
    };

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-3 px-4 py-2 bg-neutral-900 border border-neutral-800 rounded-xl hover:bg-neutral-800 transition-all text-sm font-medium text-neutral-300 group"
            >
                <div className="flex items-center gap-2">
                    {currentProvider === "ollama" ? (
                        <Cpu className="w-4 h-4 text-emerald-400" />
                    ) : currentProvider === "anthropic" ? (
                        <Zap className="w-4 h-4 text-orange-400" />
                    ) : (
                        <Globe className="w-4 h-4 text-blue-400" />
                    )}
                    <span className="capitalize">{currentProvider || "ollama"}:</span>
                    <span className="text-white font-mono">{currentModel || "..."}</span>
                </div>
                <ChevronDown className={`w-4 h-4 text-neutral-500 transition-transform ${isOpen ? "rotate-180" : ""}`} />
            </button>

            {isOpen && (
                <div className="absolute top-full mt-2 right-0 w-80 bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200 backdrop-blur-xl">
                    <div className="p-2 space-y-1">
                        {providers.map((p) => (
                            <div key={p.provider} className="p-1">
                                <div className="px-3 py-1.5 text-[10px] font-bold text-neutral-500 uppercase tracking-widest flex items-center justify-between">
                                    <span>{p.name}</span>
                                    {!p.configured && p.provider !== "ollama" && (
                                        <span className="text-red-500 lowercase font-normal italic">Key missing</span>
                                    )}
                                    {p.provider === "ollama" && p.error && (
                                        <div className="flex items-center gap-1 text-[8px] text-amber-500 font-bold animate-pulse">
                                            <Zap size={8} /> SERVICE DOWN
                                        </div>
                                    )}
                                </div>
                                {p.models.map((m) => (
                                    <button
                                        key={m}
                                        disabled={!p.configured && p.provider !== "ollama"}
                                        onClick={() => handleModelChange(p.provider, m)}
                                        className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center justify-between transition-colors
                      ${currentProvider === p.provider && currentModel === m
                                                ? "bg-emerald-600/10 text-emerald-400 border border-emerald-500/20"
                                                : "text-neutral-400 hover:bg-neutral-800 hover:text-white"
                                            }
                      ${(!p.configured && p.provider !== "ollama") ? "opacity-30 cursor-not-allowed" : ""}
                    `}
                                    >
                                        <span className="font-mono">{m}</span>
                                        {currentProvider === p.provider && currentModel === m && (
                                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                        )}
                                    </button>
                                ))}
                            </div>
                        ))}
                    </div>
                    {providers.find(p => p.provider === "ollama")?.error && (
                        <div className="p-3 bg-amber-500/10 border-t border-neutral-800 text-[10px] text-amber-500 font-medium leading-tight">
                            ⚠️ Ollama is unreachable. List shows fallback models. Please start Ollama to see your installed models.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
