"use client";

import React, { useState, useEffect, useCallback } from "react";
import { X, Plus, Trash2, Zap, Sparkles, Terminal, Database, MessageSquare, ChevronRight, Cpu, Info, Edit2 } from "lucide-react";

interface MCPServer {
    id: string;
    name: string;
}

interface Tool {
    name: string;
    description: string;
    mcp_server?: string; // We'll infer this in main.py or here
}

interface CustomAgent {
    id: string;
    name: string;
    description: string;
    system_prompt: string;
    mcp_servers: string[];
    static_tools: string[];
    provider?: string;
    model?: string;
}

interface LLMProvider {
    provider: string;
    name: string;
    models: string[];
    configured: boolean;
    error?: string;
}

interface CustomAgentManagerModalProps {
    isOpen: boolean;
    onClose: () => void;
    onChanged: () => void;
}

export default function CustomAgentManagerModal({ isOpen, onClose, onChanged }: CustomAgentManagerModalProps) {
    const [agents, setAgents] = useState<CustomAgent[]>([]);
    const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
    const [allTools, setAllTools] = useState<Tool[]>([]);
    const [llmProviders, setLlmProviders] = useState<LLMProvider[]>([]);
    const [loading, setLoading] = useState(true);
    const [view, setView] = useState<'list' | 'create'>('list');
    const [isEditing, setIsEditing] = useState(false);

    const [formData, setFormData] = useState({
        id: '',
        name: '',
        description: '',
        system_prompt: '',
        mcp_servers: [] as string[],
        static_tools: ['shell_execute'] as string[],
        provider: 'ollama',
        model: ''
    });

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    const fetchAllData = useCallback(async () => {
        setLoading(true);
        try {
            const urls = [
                `${apiUrl}/api/agents/custom`,
                `${apiUrl}/api/mcp/servers`,
                `${apiUrl}/api/tools`,
                `${apiUrl}/api/llm/models`
            ];

            const results = await Promise.all(urls.map(url =>
                fetch(url).catch(e => {
                    console.error(`Network error reaching ${url}:`, e);
                    throw new Error(`Failed to reach ${url}`);
                })
            ));

            const [agentsRes, serversRes, toolsRes, modelsRes] = results;

            if (!agentsRes.ok) throw new Error(`Agents API error: ${agentsRes.status}`);
            if (!serversRes.ok) throw new Error(`Servers API error: ${serversRes.status}`);
            if (!toolsRes.ok) throw new Error(`Tools API error: ${toolsRes.status}`);
            if (!modelsRes.ok) throw new Error(`Models API error: ${modelsRes.status}`);

            const [agentsData, serversData, toolsData, modelsData] = await Promise.all(
                results.map(res => res.json())
            );

            setAgents(agentsData);
            setMcpServers(serversData);
            setAllTools(toolsData);
            setLlmProviders(modelsData);

            // Set a default model if not set
            if (modelsData.length > 0 && !formData.model) {
                const ollamaP = modelsData.find((p: LLMProvider) => p.provider === 'ollama');
                if (ollamaP && ollamaP.models.length > 0) {
                    setFormData(prev => ({ ...prev, model: ollamaP.models[0] }));
                }
            }
        } catch (err) {
            console.error("Neural Registry Sync Failure:", err);
        } finally {
            setLoading(false);
        }
    }, [apiUrl, formData.model]);

    useEffect(() => {
        if (isOpen) fetchAllData();
    }, [isOpen, fetchAllData]);

    const handleAdd = async () => {
        if (!formData.id || !formData.name) return;
        try {
            const method = isEditing ? 'PUT' : 'POST';
            const url = isEditing ? `${apiUrl}/api/agents/custom/${formData.id}` : `${apiUrl}/api/agents/custom`;

            await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            setFormData({
                id: '',
                name: '',
                description: '',
                system_prompt: '',
                mcp_servers: [],
                static_tools: ['shell_execute'],
                provider: 'ollama',
                model: ''
            });
            setIsEditing(false);
            setView('list');
            fetchAllData();
            onChanged();
        } catch (err) {
            console.error("Failed to save custom agent:", err);
        }
    };

    const handleEdit = (agent: CustomAgent) => {
        setFormData({
            id: agent.id,
            name: agent.name,
            description: agent.description,
            system_prompt: agent.system_prompt || '',
            mcp_servers: agent.mcp_servers || [],
            static_tools: agent.static_tools || [],
            provider: agent.provider || 'ollama',
            model: agent.model || ''
        });
        setIsEditing(true);
        setView('create');
    };

    const handleDelete = async (id: string) => {
        try {
            await fetch(`${apiUrl}/api/agents/custom/${id}`, { method: 'DELETE' });
            fetchAllData();
            onChanged();
        } catch (err) {
            console.error("Failed to delete custom agent:", err);
        }
    };

    const toggleMcpServer = (serverId: string) => {
        setFormData(prev => ({
            ...prev,
            mcp_servers: prev.mcp_servers.includes(serverId)
                ? prev.mcp_servers.filter(id => id !== serverId)
                : [...prev.mcp_servers, serverId]
        }));
    };

    const toggleStaticTool = (toolName: string) => {
        setFormData(prev => ({
            ...prev,
            static_tools: prev.static_tools.includes(toolName)
                ? prev.static_tools.filter(name => name !== toolName)
                : [...prev.static_tools, toolName]
        }));
    };

    // Heuristic: tools that are NOT in the static registry list often come from MCP servers.
    // In our case, the backend /api/tools returns all.
    // Let's identify static tools as those that aren't mapped to known MCP servers in the scheduler.
    // For simplicity, we'll let the user choose from "Standard" vs "MCP Bridges".
    const standardTools = ["shell_execute", "filesystem_read", "memory_access"];
    const availableStaticTools = allTools.filter(t => standardTools.includes(t.name));

    const getToolsPerServer = (serverId: string) => {
        // This is a rough estimate since we don't have server-to-tool mapping in the /api/tools response yet
        // In a real scenario, /api/tools should return the server ID.
        // For now, if it's Filesystem or Memory, we know they are prominent.
        if (serverId === 'filesystem') return allTools.filter(t => t.name.includes('file') || t.name.includes('dir')).length;
        if (serverId === 'memory') return allTools.filter(t => t.name.includes('memory') || t.name.includes('entities')).length;
        return 0;
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-md p-4" onClick={onClose}>
            <div className="bg-neutral-900 border border-neutral-800 w-full max-w-2xl rounded-[2.5rem] overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-300" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="p-8 border-b border-neutral-800 flex items-center justify-between bg-neutral-950/20">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-purple-500/10 rounded-2xl">
                            <Sparkles className="w-6 h-6 text-purple-400" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-black text-white">Agent Personnel</h2>
                            <p className="text-[10px] text-neutral-500 uppercase tracking-widest font-mono">Autonomous Personality Architect</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-neutral-800 rounded-xl text-neutral-400 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <div className="p-8 max-h-[70vh] overflow-y-auto custom-scrollbar">
                    {view === 'list' ? (
                        <div className="space-y-6">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xs font-bold text-neutral-500 uppercase tracking-widest ml-1">Active Neural Patterns</h3>
                                <button
                                    onClick={() => { setView('create'); setIsEditing(false); setFormData({ id: '', name: '', description: '', system_prompt: '', mcp_servers: [], static_tools: ['shell_execute'], provider: 'ollama', model: '' }); }}
                                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-xl transition-all shadow-lg shadow-blue-500/10"
                                >
                                    <Plus size={14} /> New Persona
                                </button>
                            </div>

                            {loading ? (
                                <div className="py-12 text-center text-neutral-600 animate-pulse font-mono text-[10px] uppercase tracking-[0.2em]">Synchronizing Registry...</div>
                            ) : agents.length === 0 ? (
                                <div className="py-12 text-center border-2 border-dashed border-neutral-800 rounded-3xl text-neutral-600 bg-neutral-900/20">
                                    <div className="mb-2 opacity-20"><Sparkles size={40} className="mx-auto" /></div>
                                    <p className="text-sm font-medium">No custom personalities defined</p>
                                    <p className="text-[10px] uppercase mt-1 tracking-widest opacity-50 font-mono">Create your first agent to get started</p>
                                </div>
                            ) : (
                                <div className="grid gap-4">
                                    {agents.map(a => (
                                        <div key={a.id} className="group p-5 bg-neutral-800/20 border border-neutral-800/50 rounded-3xl flex items-center justify-between hover:border-neutral-700 hover:bg-neutral-800/40 transition-all duration-300">
                                            <div className="flex items-center gap-5">
                                                <div className="w-12 h-12 rounded-2xl bg-neutral-900 flex items-center justify-center text-neutral-400 group-hover:text-purple-400 transition-colors border border-neutral-800">
                                                    <Sparkles size={20} />
                                                </div>
                                                <div className="min-w-0">
                                                    <div className="font-black text-neutral-100 text-lg tracking-tight">{a.name}</div>
                                                    <div className="text-xs text-neutral-500 mt-0.5 font-medium line-clamp-1">{a.description}</div>
                                                    <div className="flex items-center gap-2 mt-2">
                                                        <span className="px-2 py-0.5 bg-neutral-900 border border-neutral-800 rounded-md text-[9px] font-mono text-neutral-500 uppercase tracking-wider">{a.mcp_servers.length} Bridges</span>
                                                        <span className="px-2 py-0.5 bg-neutral-900 border border-neutral-800 rounded-md text-[9px] font-mono text-neutral-500 uppercase tracking-wider">{a.static_tools.length} Tools</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => handleEdit(a)}
                                                    className="p-3 text-neutral-700 hover:text-blue-400 hover:bg-blue-400/10 rounded-2xl transition-all opacity-0 group-hover:opacity-100"
                                                >
                                                    <Edit2 size={18} />
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(a.id)}
                                                    className="p-3 text-neutral-700 hover:text-red-400 hover:bg-red-400/10 rounded-2xl transition-all opacity-0 group-hover:opacity-100"
                                                >
                                                    <Trash2 size={18} />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="space-y-8 animate-in slide-in-from-right-4 duration-300">
                            <div className="flex items-center gap-4 text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2 cursor-pointer hover:text-neutral-300 transition-colors" onClick={() => { setView('list'); setIsEditing(false); }}>
                                Neural Registry <ChevronRight size={14} /> <span className="text-blue-400">{isEditing ? 'Synthesize Persona' : 'Architect Persona'}</span>
                            </div>

                            <div className="grid grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-1.5"><Terminal size={10} /> Unique Descriptor (ID)</label>
                                    <input
                                        disabled={isEditing}
                                        className={`w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-5 py-3 text-sm text-white focus:border-blue-500/50 outline-none transition-all placeholder:text-neutral-800 ${isEditing ? 'opacity-50 cursor-not-allowed' : ''}`}
                                        placeholder="devops-engineer"
                                        value={formData.id}
                                        onChange={e => setFormData({ ...formData, id: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-1.5"><Sparkles size={10} /> Display Identity</label>
                                    <input
                                        className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-5 py-3 text-sm text-white focus:border-purple-500/50 outline-none transition-all placeholder:text-neutral-800"
                                        placeholder="DevOps Master Agent"
                                        value={formData.name}
                                        onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] text-neutral-500 uppercase font-black ml-1">Functional Description</label>
                                <input
                                    className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-5 py-3 text-sm text-white focus:border-blue-500/50 outline-none transition-all placeholder:text-neutral-800"
                                    placeholder="Handles deployment scripts and system maintenance..."
                                    value={formData.description}
                                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-1.5"><MessageSquare size={10} /> Core Directives (System Prompt)</label>
                                <textarea
                                    className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-5 py-4 text-sm text-white focus:border-blue-500/50 outline-none transition-all min-h-[120px] placeholder:text-neutral-800 resize-none font-medium leading-relaxed"
                                    placeholder="You are an expert DevOps engineer. Always verify system state before applying changes..."
                                    value={formData.system_prompt}
                                    onChange={e => setFormData({ ...formData, system_prompt: e.target.value })}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-1.5"><Cpu size={10} /> LLM Provider</label>
                                    <select
                                        className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-4 py-3 text-sm text-white focus:border-blue-500/50 outline-none transition-all appearance-none cursor-pointer"
                                        value={formData.provider}
                                        onChange={e => {
                                            const p = llmProviders.find(p => p.provider === e.target.value);
                                            setFormData({
                                                ...formData,
                                                provider: e.target.value,
                                                model: p && p.models.length > 0 ? p.models[0] : ''
                                            });
                                        }}
                                    >
                                        {llmProviders.map(p => (
                                            <option key={p.provider} value={p.provider}>
                                                {p.name} {!p.configured ? '(Not Configured)' : ''}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-1.5"><Zap size={10} /> Neural Model</label>
                                    <select
                                        className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-4 py-3 text-sm text-white focus:border-purple-500/50 outline-none transition-all appearance-none cursor-pointer"
                                        value={formData.model}
                                        onChange={e => setFormData({ ...formData, model: e.target.value })}
                                    >
                                        {llmProviders.find(p => p.provider === formData.provider)?.models.map(m => (
                                            <option key={m} value={m}>{m}</option>
                                        )) || <option value="">No models available</option>}
                                    </select>
                                    {formData.provider === 'ollama' && llmProviders.find(p => p.provider === 'ollama')?.error && (
                                        <div className="mt-2 p-2 bg-amber-500/10 border border-amber-500/20 rounded-xl text-[9px] text-amber-500 font-medium flex items-center gap-2 animate-pulse">
                                            <Info size={10} /> Ollama not running. Showing fallbacks.
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Standard Capabilities Selection */}
                            <div className="space-y-4">
                                <div className="flex items-center justify-between ml-1">
                                    <h4 className="text-[10px] text-neutral-500 uppercase font-black flex items-center gap-1.5"><Cpu size={10} /> Standard Capabilities</h4>
                                    <div className="group relative">
                                        <Info size={12} className="text-neutral-600 cursor-help hover:text-blue-400 transition-colors" />
                                        <div className="absolute right-0 bottom-full mb-2 w-64 p-3 bg-neutral-950 border border-neutral-800 rounded-xl text-[10px] text-neutral-400 leading-relaxed shadow-2xl opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                                            <p className="font-bold text-blue-400 mb-1">Standard Capabilities</p>
                                            Built-in system tools for direct interaction. These are high-performance native functions.
                                            <br /><br />
                                            <span className="text-neutral-200">Filesystem Read:</span> Basic access to read local files.
                                            <br />
                                            <span className="text-neutral-200">Memory Access:</span> Enables &quot;Sequential Memory&quot; for tracking facts across turns.
                                        </div>
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    {availableStaticTools.length > 0 ? availableStaticTools.map(t => (
                                        <div
                                            key={t.name}
                                            onClick={() => toggleStaticTool(t.name)}
                                            className={`p-4 rounded-2xl border cursor-pointer transition-all flex items-center justify-between group ${formData.static_tools.includes(t.name) ? "bg-emerald-500/10 border-emerald-500/30" : "bg-neutral-950 border-neutral-800 hover:border-neutral-700"}`}
                                        >
                                            <div className="min-w-0">
                                                <div className={`text-xs font-bold ${formData.static_tools.includes(t.name) ? "text-emerald-200" : "text-neutral-500 group-hover:text-neutral-300"}`}>{t.name}</div>
                                                <div className="text-[9px] text-neutral-600 truncate">{t.description}</div>
                                            </div>
                                            <div className={`w-4 h-4 rounded-md border flex items-center justify-center transition-all ${formData.static_tools.includes(t.name) ? "bg-emerald-500 border-emerald-400" : "bg-transparent border-neutral-800"}`}>
                                                {formData.static_tools.includes(t.name) && <Plus size={10} className="text-white" />}
                                            </div>
                                        </div>
                                    )) : (
                                        <div className="col-span-2 py-4 text-center text-neutral-700 text-[10px] uppercase font-mono tracking-widest bg-neutral-950 rounded-2xl border border-neutral-900">
                                            Scanning system tools...
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* MCP Bridges Selection */}
                            <div className="space-y-4">
                                <div className="flex items-center justify-between ml-1">
                                    <h4 className="text-[10px] text-neutral-500 uppercase font-black flex items-center gap-1.5"><Database size={10} /> Enabled Neural Bridges (MCP Servers)</h4>
                                    <div className="group relative">
                                        <Info size={12} className="text-neutral-600 cursor-help hover:text-purple-400 transition-colors" />
                                        <div className="absolute right-0 bottom-full mb-2 w-64 p-3 bg-neutral-950 border border-neutral-800 rounded-xl text-[10px] text-neutral-400 leading-relaxed shadow-2xl opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                                            <p className="font-bold text-purple-400 mb-1">Neural Bridges (MCP)</p>
                                            Advanced connectors to external ecosystems. They provide exhaustive toolsets (Search, Write, Analyze) beyond basic reading.
                                            <br /><br />
                                            <span className="text-neutral-200">Filesystem (MCP):</span> Full recursive search, editing, and management.
                                            <br />
                                            <span className="text-neutral-200">Memory (MCP):</span> Advanced Knowledge Graph for long-term intelligence.
                                        </div>
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    {mcpServers.map(s => {
                                        const toolCount = getToolsPerServer(s.id);
                                        return (
                                            <div
                                                key={s.id}
                                                onClick={() => toggleMcpServer(s.id)}
                                                className={`p-4 rounded-2xl border cursor-pointer transition-all flex items-center justify-between group ${formData.mcp_servers.includes(s.id) ? "bg-blue-500/10 border-blue-500/30" : "bg-neutral-950 border-neutral-800 hover:border-neutral-700"}`}
                                            >
                                                <div className="min-w-0">
                                                    <div className={`text-xs font-bold ${formData.mcp_servers.includes(s.id) ? "text-blue-200" : "text-neutral-500 group-hover:text-neutral-300"}`}>{s.name}</div>
                                                    <div className="text-[9px] text-blue-500/50 font-bold uppercase tracking-tight">{toolCount > 0 ? `${toolCount} Tools Available` : "Server Bridge"}</div>
                                                </div>
                                                <div className={`w-4 h-4 rounded-md border flex items-center justify-center transition-all ${formData.mcp_servers.includes(s.id) ? "bg-blue-500 border-blue-400" : "bg-transparent border-neutral-800"}`}>
                                                    {formData.mcp_servers.includes(s.id) && <Plus size={10} className="text-white" />}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="flex gap-4 pt-4">
                                <button
                                    onClick={() => setView('list')}
                                    className="flex-1 py-4 px-6 border border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-neutral-400 font-bold rounded-2xl transition-all"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleAdd}
                                    disabled={!formData.id || !formData.name}
                                    className="flex-[2] py-4 px-6 bg-blue-600 hover:bg-blue-500 disabled:bg-neutral-800 disabled:text-neutral-600 text-white font-black rounded-2xl transition-all shadow-xl shadow-blue-500/20 flex items-center justify-center gap-2"
                                >
                                    <Zap size={18} />
                                    {isEditing ? 'Update Neural Model' : 'Materialize Persona'}
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                <div className="p-4 border-t border-neutral-800 bg-neutral-950/50 flex justify-center">
                    <p className="text-[9px] text-neutral-600 uppercase tracking-[0.2em] font-mono">Neural Interface // Secure Channel Encrypted</p>
                </div>
            </div>
        </div>
    );
}
