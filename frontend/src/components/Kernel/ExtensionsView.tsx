"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Info, Search, Sparkles, ExternalLink, RefreshCw, ChevronLeft, ChevronRight, Upload } from "lucide-react";
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
    const [installedAgentsPage, setInstalledAgentsPage] = useState(1);
    const [installedMcpPage, setInstalledMcpPage] = useState(1);
    const itemsPerPage = 16;

    // Separate pagination for Skill Store (Server-side)
    const [skillStorePage, setSkillStorePage] = useState(1);
    const [skillStoreTotalPages, setSkillStoreTotalPages] = useState(1);
    const [loadingStore, setLoadingStore] = useState(false);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    const fetchSkillStore = useCallback(async (page: number) => {
        setLoadingStore(true);
        try {
            const res = await fetch(`${apiUrl}/api/store/skills?page=${page}&page_size=${itemsPerPage}`);
            if (res.ok) {
                const data = await res.json();
                const items = (data.items || {}) as Record<string, { name: string, description: string }>;
                const fetchedSkills: Extension[] = Object.entries(items).map(([id, s]) => ({
                    id,
                    name: s.name,
                    description: s.description,
                    type: 'skill' as const,
                    status: 'available' as const
                }));
                setSkillStore(fetchedSkills);
                setSkillStoreTotalPages(data.pages || 1);
                setSkillStorePage(data.current_page || page);
            }
        } catch (err) {
            console.error("Failed to fetch skill store page:", err);
        } finally {
            setLoadingStore(false);
        }
    }, [apiUrl, itemsPerPage]);

    const fetchData = useCallback(async () => {
        setRefreshing(true);
        try {
            const [agentsRes, mcpRes, skillStoreRes, mcpStoreRes] = await Promise.all([
                fetch(`${apiUrl}/api/agents/custom`),
                fetch(`${apiUrl}/api/mcp/servers`),
                fetch(`${apiUrl}/api/store/skills?page=1&page_size=${itemsPerPage}`),
                fetch(`${apiUrl}/api/store/mcp`)
            ]);

            const agents = await agentsRes.json();
            const mcps = await mcpRes.json();
            const skillsData = await skillStoreRes.json();
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
            const skillsS = skillsData.items || {};
            const sStore: Extension[] = Object.entries(skillsS as Record<string, { name: string; description: string }>).map(([id, s]) => ({
                id,
                name: s.name,
                description: s.description,
                type: 'skill' as const,
                status: 'available' as const
            }));
            setSkillStoreTotalPages(skillsData.pages || 1);

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
    }, [apiUrl, itemsPerPage]);

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
                const res = await fetch(`${apiUrl}/api/store/install-skill`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ slug: id })
                });
                
                if (res.ok) {
                    fetchData();
                    setActiveTab('installed');
                } else {
                    const errorData = await res.json();
                    alert(`Installation failed: ${errorData.detail || errorData.error || 'Unknown error. Check backend logs for rate limits.'}`);
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

    const handleShare = async (id: string, type: 'skill' | 'mcp') => {
        try {
            const payload = type === 'skill' ? { agent_ids: [id] } : { mcp_ids: [id] };
            const res = await fetch(`${apiUrl}/api/share/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                const bundle = await res.json();
                const blob = new Blob([JSON.stringify(bundle, null, 4)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${id}_bundle.json`;
                a.click();
                URL.revokeObjectURL(url);
            }
        } catch (err) {
            console.error("Export failed:", err);
            alert("Failed to export bundle.");
        }
    };

    const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (event) => {
            try {
                const bundle = JSON.parse(event.target?.result as string);

                // Identify required keys
                const requiredKeys = new Set<string>();
                bundle.mcp_servers?.forEach((s: { env_schema?: Record<string, string> }) => {
                    Object.keys(s.env_schema || {}).forEach(k => requiredKeys.add(k));
                });

                const overrides: Record<string, string> = {};
                for (const key of Array.from(requiredKeys)) {
                    const val = prompt(`The bundle requires a value for ${key}:`);
                    if (val) overrides[key] = val;
                }

                const res = await fetch(`${apiUrl}/api/share/import`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ bundle, overrides })
                });

                if (res.ok) {
                    alert("Bundle imported successfully!");
                    fetchData();
                } else {
                    const error = await res.json();
                    alert(`Import failed: ${error.error}`);
                }
            } catch (err) {
                console.error("Import failed:", err);
                alert("Failed to parse bundle file.");
            }
        };
        reader.readAsText(file);
    };

    const filterExtensions = (list: Extension[]) => {
        return list.filter(ext =>
            ext.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            ext.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
            ext.id.toLowerCase().includes(searchTerm.toLowerCase())
        );
    };

    // Filtered lists for Installed tab
    const filteredAgents = filterExtensions(installedExtensions.filter(e => e.type === 'skill'));
    const filteredMcps = filterExtensions(installedExtensions.filter(e => e.type === 'mcp'));

    // Pagination for Store (External)
    const isStoreTab = activeTab === 'skills-store' && !searchTerm;
    const isMcpStoreTab = activeTab === 'mcp-store';

    useEffect(() => {
        if (activeTab === 'skills-store' && !searchTerm.trim()) {
            setSkillStorePage(1);
            fetchSkillStore(1);
        }
        setInstalledAgentsPage(1);
        setInstalledMcpPage(1);
    }, [searchTerm, activeTab, fetchSkillStore]);

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

    const renderPagination = (page: number, total: number, onChange: (p: number) => void) => {
        if (total <= 1) return null;
        return (
            <div className="flex items-center justify-center gap-4 py-8 border-t border-neutral-800/30">
                <button
                    onClick={() => onChange(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="flex items-center gap-2 px-4 py-2 bg-neutral-900 border border-neutral-800 rounded-xl text-neutral-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all font-bold text-[10px] uppercase tracking-widest"
                >
                    <ChevronLeft size={14} /> Prev
                </button>
                <div className="flex items-center gap-2">
                    {Array.from({ length: Math.min(5, total) }, (_, i) => {
                        let pageNum = i + 1;
                        if (total > 5 && page > 3) {
                            pageNum = page - 2 + i;
                            if (pageNum > total) pageNum = total - 4 + i;
                        }
                        if (pageNum < 1) pageNum = i + 1;

                        return (
                            <button
                                key={pageNum}
                                onClick={() => onChange(pageNum)}
                                className={`w-10 h-10 rounded-xl border font-mono text-xs transition-all ${page === pageNum ? 'bg-orange-600 border-orange-500 text-white' : 'bg-neutral-900 border-neutral-800 text-neutral-500 hover:border-neutral-700'}`}
                            >
                                {pageNum}
                            </button>
                        );
                    })}
                </div>
                <button
                    onClick={() => onChange(Math.min(total, page + 1))}
                    disabled={page === total}
                    className="flex items-center gap-2 px-4 py-2 bg-neutral-900 border border-neutral-800 rounded-xl text-neutral-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all font-bold text-[10px] uppercase tracking-widest"
                >
                    Next <ChevronRight size={14} />
                </button>
            </div>
        );
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
                        {searchTerm && (
                            <div className="absolute right-12 top-1/2 -translate-y-1/2 flex items-center gap-1.5 px-2 py-0.5 bg-blue-500/10 rounded-md border border-blue-500/20">
                                <span className="text-[10px] font-mono font-bold text-blue-400">
                                    {activeTab === 'installed' ? (filteredAgents.length + filteredMcps.length) : (activeTab === 'skills-store' ? skillStore.length : mcpStore.length)}
                                </span>
                            </div>
                        )}
                        {(searching || loadingStore) && (
                            <div className="absolute right-4 top-1/2 -translate-y-1/2">
                                <RefreshCw className="w-3 h-3 text-blue-400 animate-spin" />
                            </div>
                        )}
                    </div>
                    <label className="p-3 bg-neutral-900 border border-neutral-800 rounded-2xl text-neutral-400 hover:text-blue-400 transition-all cursor-pointer" title="Import Bundle (.json)">
                        <Upload size={18} />
                        <input type="file" accept=".json" onChange={handleImportFile} className="hidden" />
                    </label>
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
                                <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-6 mb-6">
                                    {filteredAgents.slice((installedAgentsPage - 1) * itemsPerPage, installedAgentsPage * itemsPerPage).map(ext => (
                                        <ExtensionCard
                                            key={ext.id}
                                            {...ext}
                                            onToggle={(val) => handleToggle(ext.id, ext.type, val)}
                                            onInstall={() => handleInstall(ext.id, ext.type, ext.requiresKey)}
                                            onUninstall={() => handleUninstall(ext.id, ext.type)}
                                            onConfigure={() => handleConfigure(ext.id, ext.type)}
                                            onShare={() => handleShare(ext.id, ext.type)}
                                        />
                                    ))}
                                    {filteredAgents.length === 0 && (
                                        <div className="col-span-full py-8 px-8 border border-neutral-800/50 rounded-3xl bg-neutral-900/20">
                                            <p className="text-neutral-600 text-xs italic">No custom agents or skills installed.</p>
                                        </div>
                                    )}
                                </div>
                                {renderPagination(installedAgentsPage, Math.ceil(filteredAgents.length / itemsPerPage), setInstalledAgentsPage)}
                            </section>

                            {/* Active Bridges Section */}
                            <section>
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-1.5 h-6 bg-orange-500 rounded-full shadow-[0_0_10px_rgba(249,115,22,0.5)]" />
                                    <h3 className="text-xl font-bold text-white tracking-tight">Active Bridges (MCP)</h3>
                                    <span className="px-2 py-0.5 bg-orange-500/10 text-orange-400 text-[10px] font-mono rounded-lg border border-blue-500/20">INFRASTRUCTURE</span>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-6 mb-6">
                                    {filteredMcps.slice((installedMcpPage - 1) * itemsPerPage, installedMcpPage * itemsPerPage).map(ext => (
                                        <ExtensionCard
                                            key={ext.id}
                                            {...ext}
                                            onToggle={(val) => handleToggle(ext.id, ext.type, val)}
                                            onInstall={() => handleInstall(ext.id, ext.type, ext.requiresKey)}
                                            onUninstall={() => handleUninstall(ext.id, ext.type)}
                                            onConfigure={() => handleConfigure(ext.id, ext.type)}
                                            onShare={() => handleShare(ext.id, ext.type)}
                                        />
                                    ))}
                                    {filteredMcps.length === 0 && (
                                        <div className="col-span-full py-8 px-8 border border-neutral-800/50 rounded-3xl bg-neutral-900/20">
                                            <p className="text-neutral-600 text-xs italic">No MCP bridges installed.</p>
                                        </div>
                                    )}
                                </div>
                                {renderPagination(installedMcpPage, Math.ceil(filteredMcps.length / itemsPerPage), setInstalledMcpPage)}
                            </section>
                        </div>
                    ) : (
                        <div className="flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-500 mb-10 min-h-[400px]">
                            <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-6 mb-6">
                                {loadingStore ? (
                                    <div className="col-span-full flex flex-col items-center justify-center py-20">
                                        <RefreshCw className="w-8 h-8 text-orange-500 animate-spin mb-4" />
                                        <p className="text-neutral-500 font-mono text-[10px] uppercase tracking-widest">Paging ClawHub Registry...</p>
                                    </div>
                                ) : (
                                    (activeTab === 'skills-store' ? skillStore : filterExtensions(mcpStore)).slice(
                                        isMcpStoreTab ? (currentPage - 1) * itemsPerPage : 0,
                                        isMcpStoreTab ? currentPage * itemsPerPage : undefined
                                    ).map(ext => (
                                        <ExtensionCard
                                            key={ext.id}
                                            {...ext}
                                            onToggle={(val) => handleToggle(ext.id, ext.type, val)}
                                            onInstall={() => handleInstall(ext.id, ext.type, ext.requiresKey)}
                                            onUninstall={() => handleUninstall(ext.id, ext.type)}
                                            onConfigure={() => handleConfigure(ext.id, ext.type)}
                                            onShare={() => handleShare(ext.id, ext.type)}
                                        />
                                    ))
                                )}
                            </div>
                            {isStoreTab ? 
                                renderPagination(skillStorePage, skillStoreTotalPages, (p) => {
                                    setSkillStorePage(p);
                                    fetchSkillStore(p);
                                }) : 
                                isMcpStoreTab && renderPagination(currentPage, Math.ceil(mcpStore.length / itemsPerPage), setCurrentPage)
                            }
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
