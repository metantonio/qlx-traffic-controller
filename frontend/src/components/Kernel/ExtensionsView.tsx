"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Info, Search, Sparkles, ExternalLink, RefreshCw } from "lucide-react";
import ExtensionCard from "./ExtensionCard";

interface Extension {
    id: string;
    name: string;
    description: string;
    type: 'skill' | 'mcp';
    status: 'installed' | 'available';
    enabled?: boolean;
    requiresKey?: boolean;
}

export default function ExtensionsView() {
    const [activeTab, setActiveTab] = useState<'installed' | 'skills-store' | 'mcp-store'>('installed');
    const [searchTerm, setSearchTerm] = useState("");
    const [installedExtensions, setInstalledExtensions] = useState<Extension[]>([]);
    const [skillStore, setSkillStore] = useState<Extension[]>([]);
    const [mcpStore, setMcpStore] = useState<Extension[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    const fetchData = useCallback(async () => {
        setRefreshing(true);
        try {
            const [agentsRes, mcpRes, skillStoreRes, mcpStoreRes] = await Promise.all([
                fetch(`${apiUrl}/api/agents/custom`),
                fetch(`${apiUrl}/api/mcp/servers`),
                fetch(`${apiUrl}/api/store/skills`),
                fetch(`${apiUrl}/api/store/mcp`)
            ]);

            const agents = await agentsRes.json();
            const mcps = await mcpRes.json();
            const skillsS = await skillStoreRes.json();
            const mcpsS = await mcpStoreRes.json();

            // Format installed
            const installed: Extension[] = [
                ...agents.map((a: { id: string; name: string; description: string }) => ({
                    id: a.id,
                    name: a.name,
                    description: a.description,
                    type: 'skill' as const,
                    status: 'installed' as const,
                    enabled: true // Agents are "enabled" by existing
                })),
                ...mcps.map((m: { id: string; name: string; command: string; args: string[]; enabled: boolean }) => ({
                    id: m.id,
                    name: m.name,
                    description: `${m.command} ${m.args.join(' ')}`,
                    type: 'mcp' as const,
                    status: 'installed' as const,
                    enabled: m.enabled
                }))
            ];

            // Format stores
            const sStore: Extension[] = Object.entries(skillsS).map(([id, s]: [string, any]) => ({
                id,
                name: s.name,
                description: s.description,
                type: 'skill' as const,
                status: 'available' as const
            }));

            const mStore: Extension[] = Object.entries(mcpsS).map(([id, m]: [string, any]) => ({
                id,
                name: m.name,
                description: m.description,
                type: 'mcp' as const,
                status: 'available' as const,
                requiresKey: m.requires_api_key
            }));

            setInstalledExtensions(installed);
            setSkillStore(sStore);
            setMcpStore(mStore);
        } catch (err) {
            console.error("Failed to fetch extensions data:", err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [apiUrl]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleToggle = async (id: string, type: 'skill' | 'mcp', enabled: boolean) => {
        try {
            if (type === 'mcp') {
                const res = await fetch(`${apiUrl}/api/mcp/servers/${id}/toggle`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled })
                });
                if (!res.ok) throw new Error("Failed to toggle MCP");
            } else {
                // For Skills (Custom Agents), we don't have a toggle yet, 
                // but we could implement it. For now, we'll just log or 
                // update the config if we had an "enabled" field.
                console.log(`Toggling Skill ${id} to ${enabled}`);
            }
            setInstalledExtensions(prev => prev.map(ext => ext.id === id ? { ...ext, enabled } : ext));
        } catch (err) {
            console.error("Toggle failed:", err);
        }
    };

    const handleInstall = async (id: string, type: 'skill' | 'mcp', requiresKey?: boolean) => {
        try {
            if (type === 'mcp') {
                const url = `${apiUrl}/api/store/install`;
                let overrides = {};
                if (requiresKey) {
                    const key = prompt(`API Key required for ${id}:`);
                    if (!key) return;
                    overrides = { 'api': key, 'key': key, 'token': key };
                }
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ server_id: id, overrides })
                });
                if (res.ok) {
                    fetchData();
                    setActiveTab('installed');
                }
            } else {
                // Skill installation
                const skillsData = await (await fetch(`${apiUrl}/api/store/skills`)).json();
                const skillEntry = Object.entries(skillsData).find(([sId]) => sId === id);
                if (!skillEntry) return;

                const skill = skillEntry[1] as {
                    name: string;
                    description: string;
                    system_prompt?: string;
                    mcp_servers?: string[];
                    static_tools?: string[];
                };

                const res = await fetch(`${apiUrl}/api/agents/custom`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        id,
                        name: skill.name,
                        description: skill.description,
                        system_prompt: skill.system_prompt,
                        mcp_servers: skill.mcp_servers,
                        static_tools: skill.static_tools
                    })
                });
                if (res.ok) {
                    fetchData();
                    setActiveTab('installed');
                }
            }
        } catch (err) {
            console.error("Install failed:", err);
        }
    };

    const handleUninstall = async (id: string, type: 'skill' | 'mcp') => {
        if (!confirm(`Are you sure you want to uninstall ${id}?`)) return;
        try {
            const endpoint = type === 'skill' ? `/api/agents/custom/${id}` : `/api/mcp/servers/${id}`;
            const res = await fetch(`${apiUrl}${endpoint}`, { method: 'DELETE' });
            if (res.ok) fetchData();
        } catch (err) {
            console.error("Uninstall failed:", err);
        }
    };

    const filterExtensions = (list: Extension[]) => {
        return list.filter(ext =>
            ext.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            ext.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
            ext.id.toLowerCase().includes(searchTerm.toLowerCase())
        );
    };

    const currentList = activeTab === 'installed' ? filterExtensions(installedExtensions) :
        activeTab === 'skills-store' ? filterExtensions(skillStore) :
            filterExtensions(mcpStore);

    return (
        <div className="flex-grow p-10 overflow-y-auto custom-scrollbar bg-[#0a0a0b]">
            <header className="mb-10 flex items-center justify-between">
                <div>
                    <h2 className="text-4xl font-black tracking-tighter text-white">Extensions</h2>
                    <p className="text-neutral-500 text-sm mt-1 font-medium tracking-wide font-mono uppercase">System Capability Hub</p>
                </div>
                <div className="flex items-center gap-4">
                    <div className="relative group">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-600 group-focus-within:text-blue-400 transition-colors" />
                        <input
                            type="text"
                            placeholder="Search extensions..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="bg-neutral-900/50 border border-neutral-800 rounded-2xl pl-11 pr-6 py-3 text-sm text-white focus:border-blue-500/50 outline-none w-64 transition-all"
                        />
                    </div>
                    <button
                        onClick={fetchData}
                        className={`p-3 bg-neutral-900 border border-neutral-800 rounded-2xl text-neutral-400 hover:text-white transition-all ${refreshing ? 'animate-spin' : ''}`}
                    >
                        <RefreshCw size={18} />
                    </button>
                </div>
            </header>

            {/* Info Banner */}
            <div className="mb-10 p-8 bg-neutral-900/40 border-l-4 border-l-orange-600 border border-neutral-800/80 rounded-3xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-orange-600/5 blur-[80px] rounded-full -mr-16 -mt-16 group-hover:bg-orange-600/10 transition-colors" />
                <div className="flex items-start gap-6 relative">
                    <div className="p-4 bg-orange-600/10 rounded-2xl border border-orange-600/20">
                        <Info className="w-6 h-6 text-orange-500" />
                    </div>
                    <div className="max-w-3xl">
                        <h3 className="text-lg font-bold text-neutral-100 mb-2">Skills & Ecosystem</h3>
                        <p className="text-sm text-neutral-400 leading-relaxed">
                            Skills extend your agents with new capabilities. OpenFang supports the <span className="text-orange-400 font-bold">OpenClaw/ClawHub</span> ecosystem (3,000+ community skills) plus local skills.
                        </p>
                        <ul className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2">
                            <li className="flex items-center gap-2 text-xs text-neutral-500">
                                <span className="w-1.5 h-1.5 rounded-full bg-orange-600/50" />
                                <strong>Prompt-only</strong> — context and instructions (most ClawHub skills)
                            </li>
                            <li className="flex items-center gap-2 text-xs text-neutral-500">
                                <span className="w-1.5 h-1.5 rounded-full bg-orange-600/50" />
                                <strong>MCP Servers</strong> — external tools via Model Context Protocol
                            </li>
                        </ul>
                    </div>
                </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex gap-2 mb-8 border-b border-neutral-800/50 pb-px">
                {[
                    { id: 'installed', label: 'Installed', count: installedExtensions.length, icon: <RefreshCw size={14} /> },
                    { id: 'skills-store', label: 'Skill Store', icon: <Sparkles size={14} /> },
                    { id: 'mcp-store', label: 'MCP Store', icon: <ExternalLink size={14} /> }
                ].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as any)}
                        className={`flex items-center gap-2 px-6 py-4 text-xs font-black uppercase tracking-[0.2em] transition-all relative ${activeTab === tab.id ? 'text-orange-500' : 'text-neutral-500 hover:text-neutral-300'}`}
                    >
                        {tab.icon}
                        {tab.label}
                        {tab.count !== undefined && (
                            <span className={`ml-2 px-2 py-0.5 rounded-full text-[10px] ${activeTab === tab.id ? 'bg-orange-600/20' : 'bg-neutral-800'}`}>
                                {tab.count}
                            </span>
                        )}
                        {activeTab === tab.id && (
                            <div className="absolute bottom-0 left-0 w-full h-0.5 bg-orange-600" />
                        )}
                    </button>
                ))}
            </div>

            {loading ? (
                <div className="py-20 text-center">
                    <div className="inline-block p-4 bg-neutral-900 border border-neutral-800 rounded-2xl mb-4 animate-bounce">
                        <Sparkles className="w-8 h-8 text-neutral-600" />
                    </div>
                    <p className="text-neutral-600 font-mono text-xs uppercase tracking-widest">Accessing Extension Registry...</p>
                </div>
            ) : currentList.length === 0 ? (
                <div className="py-20 text-center border-2 border-dashed border-neutral-800/50 rounded-[3rem] bg-neutral-900/10">
                    <Search className="w-12 h-12 text-neutral-800 mx-auto mb-4" />
                    <h4 className="text-neutral-400 font-bold">No extensions found</h4>
                    <p className="text-xs text-neutral-600 mt-1">Try searching for something else or browse the store.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {currentList.map(ext => (
                        <ExtensionCard
                            key={ext.id}
                            id={ext.id}
                            name={ext.name}
                            description={ext.description}
                            type={ext.type}
                            status={ext.status}
                            enabled={ext.enabled}
                            requiresKey={ext.requiresKey}
                            onToggle={(val) => handleToggle(ext.id, ext.type, val)}
                            onInstall={() => handleInstall(ext.id, ext.type, ext.requiresKey)}
                            onUninstall={() => handleUninstall(ext.id, ext.type)}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
