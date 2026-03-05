"use client";

import { useState, useEffect } from "react";

export interface Tool {
    name: string;
    description: string;
}

interface ToolManagerProps {
    onToolsChange: (enabledTools: string[]) => void;
}

export default function ToolManager({ onToolsChange }: ToolManagerProps) {
    const [tools, setTools] = useState<Tool[]>([]);
    const [enabledTools, setEnabledTools] = useState<Set<string>>(new Set());
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchTools = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
                const response = await fetch(`${apiUrl}/api/tools`);
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data = await response.json();

                if (Array.isArray(data)) {
                    setTools(data);
                    const allNames = data.map((t: Tool) => t.name);
                    setEnabledTools(new Set(allNames));
                    onToolsChange(allNames);
                } else {
                    console.error("API returned non-array data:", data);
                    setTools([]);
                }
            } catch (error) {
                console.error("Failed to fetch tools:", error);
                // Fallback to basic tools if API is down
                const fallback = [
                    { name: "shell_execute", description: "Execute system commands" },
                    { name: "filesystem_read", description: "Read files via MCP" }
                ];
                setTools(fallback);
                setEnabledTools(new Set(fallback.map(t => t.name)));
                onToolsChange(fallback.map(t => t.name));
            } finally {
                setLoading(false);
            }
        };
        fetchTools();
    }, []);

    const toggleTool = (name: string) => {
        const newEnabled = new Set(enabledTools);
        if (newEnabled.has(name)) {
            newEnabled.delete(name);
        } else {
            newEnabled.add(name);
        }
        setEnabledTools(newEnabled);
        onToolsChange(Array.from(newEnabled));
    };

    const toggleAll = (enable: boolean) => {
        const newEnabled = enable ? new Set(tools.map((t) => t.name)) : new Set<string>();
        setEnabledTools(newEnabled);
        onToolsChange(Array.from(newEnabled));
    };

    if (loading) return <div className="text-xs text-neutral-500 animate-pulse">Loading MCP tools...</div>;

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-medium text-neutral-500 uppercase tracking-wider">
                <span>Available Capabilities (MCP)</span>
                <div className="flex gap-2">
                    <button
                        onClick={() => toggleAll(true)}
                        className="hover:text-blue-400 transition-colors"
                    >
                        All
                    </button>
                    <span>/</span>
                    <button
                        onClick={() => toggleAll(false)}
                        className="hover:text-blue-400 transition-colors"
                    >
                        None
                    </button>
                </div>
            </div>
            <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
                {tools.map((tool) => (
                    <div
                        key={tool.name}
                        onClick={() => toggleTool(tool.name)}
                        className={`flex items-start gap-3 p-2 rounded-lg border transition-all cursor-pointer ${enabledTools.has(tool.name)
                            ? "bg-blue-500/10 border-blue-500/30 text-blue-100"
                            : "bg-neutral-900/50 border-neutral-800 text-neutral-500 hover:border-neutral-700"
                            }`}
                    >
                        <div className={`mt-1 h-3 w-3 rounded-sm border flex items-center justify-center transition-colors ${enabledTools.has(tool.name)
                            ? "bg-blue-500 border-blue-400"
                            : "bg-transparent border-neutral-700"
                            }`}>
                            {enabledTools.has(tool.name) && (
                                <svg className="w-2 h-2 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={4} d="M5 13l4 4L19 7" />
                                </svg>
                            )}
                        </div>
                        <div className="flex flex-col gap-0.5 min-w-0">
                            <span className="text-sm font-semibold truncate">{tool.name}</span>
                            <span className="text-[10px] leading-tight opacity-70 line-clamp-1">{tool.description}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
