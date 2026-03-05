"use client";

import React, { useEffect, useState } from "react";
import { ChevronDown, Cpu, Globe, Zap } from "lucide-react";

interface LLMProviderInfo {
    provider: string;
    name: string;
    models: string[];
    configured: boolean;
}

interface ModelSelectorProps {
    onSelect: (provider: string, model: string) => void;
    currentProvider?: string;
    currentModel?: string;
}

export default function ModelSelector({ onSelect, currentProvider, currentModel }: ModelSelectorProps) {
    const [providers, setProviders] = useState<LLMProviderInfo[]>([]);
    const [isOpen, setIsOpen] = useState(false);
    const [selectedProvider, setSelectedProvider] = useState<string>("");
    const [selectedModel, setSelectedModel] = useState<string>("");

    useEffect(() => {
        const fetchModels = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
                const res = await fetch(`${apiUrl}/api/llm/models`);
                const data = await res.json();
                setProviders(data);

                // Default selection if none provided
                if (!currentProvider && data.length > 0) {
                    setSelectedProvider(data[0].provider);
                    setSelectedModel(data[0].models[0]);
                    onSelect(data[0].provider, data[0].models[0]);
                }
            } catch (err) {
                console.error("Failed to fetch LLM models:", err);
            }
        };
        fetchModels();
    }, []);

    useEffect(() => {
        if (currentProvider) setSelectedProvider(currentProvider);
        if (currentModel) setSelectedModel(currentModel);
    }, [currentProvider, currentModel]);

    const handleModelChange = (p: string, m: string) => {
        setSelectedProvider(p);
        setSelectedModel(m);
        onSelect(p, m);
        setIsOpen(false);
    };

    const currentProviderInfo = providers.find((p) => p.provider === selectedProvider);

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-3 px-4 py-2 bg-neutral-900 border border-neutral-800 rounded-xl hover:bg-neutral-800 transition-all text-sm font-medium text-neutral-300 group"
            >
                <div className="flex items-center gap-2">
                    {selectedProvider === "ollama" ? (
                        <Cpu className="w-4 h-4 text-emerald-400" />
                    ) : selectedProvider === "anthropic" ? (
                        <Zap className="w-4 h-4 text-orange-400" />
                    ) : (
                        <Globe className="w-4 h-4 text-blue-400" />
                    )}
                    <span className="capitalize">{selectedProvider}:</span>
                    <span className="text-white font-mono">{selectedModel}</span>
                </div>
                <ChevronDown className={`w-4 h-4 text-neutral-500 transition-transform ${isOpen ? "rotate-180" : ""}`} />
            </button>

            {isOpen && (
                <div className="absolute top-full mt-2 left-0 w-80 bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200 backdrop-blur-xl">
                    <div className="p-2 space-y-1">
                        {providers.map((p) => (
                            <div key={p.provider} className="p-1">
                                <div className="px-3 py-1.5 text-[10px] font-bold text-neutral-500 uppercase tracking-widest flex items-center justify-between">
                                    <span>{p.name}</span>
                                    {!p.configured && (
                                        <span className="text-red-500 lowercase font-normal italic">Key missing</span>
                                    )}
                                </div>
                                {p.models.map((m) => (
                                    <button
                                        key={m}
                                        disabled={!p.configured && p.provider !== "ollama"}
                                        onClick={() => handleModelChange(p.provider, m)}
                                        className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center justify-between transition-colors
                      ${selectedProvider === p.provider && selectedModel === m
                                                ? "bg-emerald-600/10 text-emerald-400 border border-emerald-500/20"
                                                : "text-neutral-400 hover:bg-neutral-800 hover:text-white"
                                            }
                      ${(!p.configured && p.provider !== "ollama") ? "opacity-30 cursor-not-allowed" : ""}
                    `}
                                    >
                                        <span className="font-mono">{m}</span>
                                        {selectedProvider === p.provider && selectedModel === m && (
                                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                        )}
                                    </button>
                                ))}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
