"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Info, Search, Sparkles, ExternalLink, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import ExtensionCard from "./ExtensionCard";
import CustomAgentManagerModal from "./CustomAgentManagerModal";

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
    const [searching, setSearching] = useState(false);
    const [isAgentModalOpen, setIsAgentModalOpen] = useState(false);
    const [editingAgentId, setEditingAgentId] = useState<string | null>(null);

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 10;

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
                    enabled: true
                })),
                ...mcps.map((m: { id: string; name: string; command: string; args: string[]; enabled: boolean }) => ({
                    id: m.id,
                    name: m.name,
                    description: `${m.name} Bridge (${m.id})`,
                    type: 'mcp' as const,
                    status: 'installed' as const,
                    enabled: m.enabled
                }))
            ];

            // Format stores
            const sStore: Extension[] = (Object.entries(skillsS) as [string, { name: string; description: string }][]).map(([id, s]) => ({
                id,
                name: s.name,
                description: s.description,
                type: 'skill' as const,
                status: 'available' as const
            }));

            const mStore: Extension[] = (Object.entries(mcpsS) as [string, { name: string; description: string; requires_api_key?: boolean }][]).map(([id, m]) => ({
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

    // Live Search for ClawHub
    useEffect(() => {
        if (activeTab !== 'skills-store' || !searchTerm.trim()) return;

        const delayDebounceFn = setTimeout(async () => {
            setSearching(true);
            try {
                const res = await fetch(`${apiUrl}/api/store/search?q=${encodeURIComponent(searchTerm)}`);
                if (res.ok) {
                    const data = await res.json();
                    const liveResults: Extension[] = (data.results || []).map((s: { slug: string; displayName?: string; summary?: string }) => ({
                        id: s.slug,
                        name: s.displayName || s.slug,
                        description: s.summary || "",
                        type: 'skill' as const,
                        status: 'available' as const
                    }));
                    setSkillStore(liveResults);
                }
            } catch (err) {
                console.error("ClawHub search error:", err);
            } finally {
                setSearching(false);
            }
        }, 500);

        return () => clearTimeout(delayDebounceFn);
    }, [searchTerm, activeTab, apiUrl]);

    const handleToggle = async (id: string, type: 'skill' | 'mcp', enabled: boolean) => {
        try {
            if (type === 'mcp') {
                const res = await fetch(`${apiUrl}/api/mcp/servers/${id}/toggle`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled })
                });
                if (!res.ok) throw new Error("Failed to toggle MCP");
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
                // Install Skill
                let skill: { name: string; description: string; system_prompt?: string; mcp_servers?: string[]; static_tools?: string[] } | null = null;
                const skillsData = await (await fetch(`${apiUrl}/api/store/skills`)).json();

                if (skillsData[id]) {
                    skill = skillsData[id];
                } else {
                    // Try fetching details from ClawHub via backend proxy if available, or directly (with CORS risk)
                    // Better to use search/details via backend
                    const detailRes = await fetch(`${apiUrl}/api/store/search?q=${id}`); // Re-using search as a quick detail check or specific endpoint
                    const searchData = await detailRes.json();
                    const found = searchData.results?.find((s: { slug: string; displayName?: string; summary?: string }) => s.slug === id);
                    if (found) {
                        skill = {
                            name: found.displayName || found.slug,
                            description: found.summary || "",
                            system_prompt: `I am the specialized agent for ${found.displayName}. My purpose is to ${found.summary}.`,
                            mcp_servers: [],
                            static_tools: []
                        };
                    }
                }

                if (!skill) {
                    alert("Could not find skill details for installation.");
                    return;
                }

                const res = await fetch(`${apiUrl}/api/agents/custom`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        id,
                        name: skill.name,
                        description: skill.description,
                        system_prompt: skill.system_prompt || `I am the ${skill.name} specialist.`,
                        mcp_servers: skill.mcp_servers || [],
                        static_tools: skill.static_tools || []
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

    const handleConfigure = (id: string, type: 'skill' | 'mcp') => {
        if (type === 'skill') {
            setEditingAgentId(id);
            setIsAgentModalOpen(true);
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
        activeTab === 'skills-store' ? (searchTerm ? skillStore : filterExtensions(skillStore)) :
            filterExtensions(mcpStore);

    const totalPages = Math.ceil(currentList.length / itemsPerPage);
    const paginatedList = currentList.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

    useEffect(() => {
        setCurrentPage(1);
    }, [searchTerm, activeTab]);

    const handleSyncRegistry = async () => {
        const url = prompt("Enter External MCP Registry URL (JSON):", "https://raw.githubusercontent.com/modelcontextprotocol/servers/main/index.json");
        if (!url) return;

        try {
            setRefreshing(true);
            const res = await fetch(`${apiUrl}/api/store/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const data = await res.json();
            if (res.ok) {
                alert("Registry synchronized successfully!");
                fetchData();
            } else {
                alert(`Sync failed: ${data.detail || data.message}`);
            }
        } catch (err) {
            console.error("Registry sync failed:", err);
            alert("Network error while syncing registry.");
        } finally {
            setRefreshing(false);
        }
    };

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
                            className="bg-neutral-900/50 border border-neutral-800 rounded-2xl pl-11 pr-12 py-3 text-sm text-white focus:border-blue-500/50 outline-none w-64 transition-all"
                        />
                        {searching && (
                            <div className="absolute right-4 top-1/2 -translate-y-1/2">
                                <RefreshCw className="w-3 h-3 text-blue-400 animate-spin" />
                            </div>
                        )}
                    </div>
                    <button
                        onClick={handleSyncRegistry}
                        title="Import Community Registry"
                        className="p-3 bg-neutral-900 border border-neutral-800 rounded-2xl text-neutral-400 hover:text-orange-500 transition-all"
                    >
                        <RefreshCw size={18} className={refreshing ? 'animate-spin' : ''} />
                    </button>
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
                            Skills extend your agents with new capabilities. QLX-traffic-controller supports the <span className="text-orange-400 font-bold">OpenClaw/ClawHub</span> ecosystem (3,000+ community skills) plus local skills.
                            <br />
                            <span className="text-[11px] text-blue-400 mt-2 block font-medium">To use a Skill, it must be assigned to an Agent first. When you create or edit an agent, you can equip them with these specialized capabilities.</span>
                        </p>
                        <ul className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2">
                            <li className="flex items-center gap-2 text-xs text-neutral-500">
                                <span className="w-1.5 h-1.5 rounded-full bg-orange-600/50" />
                                <strong>Prompt-only</strong> — context and instructions (ClawHub skills)
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
                        onClick={() => setActiveTab(tab.id as 'installed' | 'skills-store' | 'mcp-store')}
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
                <>
                    {activeTab === 'installed' ? (
                        <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500 mb-10">
                            {/* Active Agents Section */}
                            <section>
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-1.5 h-6 bg-blue-500 rounded-full shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
                                    <h3 className="text-xl font-bold text-white tracking-tight">Active Agents & Skills</h3>
                                    <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-[10px] font-mono rounded-lg border border-blue-500/20">SPECIALISTS</span>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-6">
                                    {paginatedList.filter(ext => ext.type === 'skill').map(ext => (
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
                                            onConfigure={() => handleConfigure(ext.id, ext.type)}
                                        />
                                    ))}
                                    {paginatedList.filter(ext => ext.type === 'skill').length === 0 && (
                                        <div className="col-span-full py-8 px-8 border border-neutral-800/50 rounded-3xl bg-neutral-900/20">
                                            <p className="text-neutral-600 text-xs italic">No custom agents or skills active in this page.</p>
                                        </div>
                                    )}
                                </div>
                            </section>

                            {/* Active Bridges Section */}
                            <section>
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-1.5 h-6 bg-orange-500 rounded-full shadow-[0_0_10px_rgba(249,115,22,0.5)]" />
                                    <h3 className="text-xl font-bold text-white tracking-tight">Active Bridges (MCP)</h3>
                                    <span className="px-2 py-0.5 bg-orange-500/10 text-orange-400 text-[10px] font-mono rounded-lg border border-orange-500/20">INFRASTRUCTURE</span>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-6">
                                    {paginatedList.filter(ext => ext.type === 'mcp').map(ext => (
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
                                            onConfigure={() => handleConfigure(ext.id, ext.type)}
                                        />
                                    ))}
                                    {paginatedList.filter(ext => ext.type === 'mcp').length === 0 && (
                                        <div className="col-span-full py-8 px-8 border border-neutral-800/50 rounded-3xl bg-neutral-900/20">
                                            <p className="text-neutral-600 text-xs italic">No MCP bridges active in this page.</p>
                                        </div>
                                    )}
                                </div>
                            </section>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500 mb-10">
                            {paginatedList.map(ext => (
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
                                    onConfigure={() => handleConfigure(ext.id, ext.type)}
                                />
                            ))}
                        </div>
                    )}

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                        <div className="flex items-center justify-center gap-4 py-8 border-t border-neutral-800/30">
                            <button
                                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                                disabled={currentPage === 1}
                                className="flex items-center gap-2 px-4 py-2 bg-neutral-900 border border-neutral-800 rounded-xl text-neutral-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all font-bold text-[10px] uppercase tracking-widest"
                            >
                                <ChevronLeft size={14} /> Prev
                            </button>
                            <div className="flex items-center gap-2">
                                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                    // Show pages around current
                                    let pageNum = i + 1;
                                    if (totalPages > 5 && currentPage > 3) {
                                        pageNum = currentPage - 2 + i;
                                        if (pageNum > totalPages) pageNum = totalPages - 4 + i;
                                    }
                                    return (
                                        <button
                                            key={pageNum}
                                            onClick={() => setCurrentPage(pageNum)}
                                            className={`w-10 h-10 rounded-xl border font-mono text-xs transition-all ${currentPage === pageNum ? 'bg-orange-600 border-orange-500 text-white' : 'bg-neutral-900 border-neutral-800 text-neutral-500 hover:border-neutral-700'}`}
                                        >
                                            {pageNum}
                                        </button>
                                    );
                                })}
                            </div>
                            <button
                                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                                disabled={currentPage === totalPages}
                                className="flex items-center gap-2 px-4 py-2 bg-neutral-900 border border-neutral-800 rounded-xl text-neutral-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all font-bold text-[10px] uppercase tracking-widest"
                            >
                                Next <ChevronRight size={14} />
                            </button>
                        </div>
                    )}
                </>
            )}

            <CustomAgentManagerModal
                isOpen={isAgentModalOpen}
                onClose={() => {
                    setIsAgentModalOpen(false);
                    setEditingAgentId(null);
                }}
                onChanged={fetchData}
                initialAgentId={editingAgentId}
            />
        </div>
    );
}
