"use client";

import React, { useState, useEffect } from "react";
import { X, Plus, Trash2, Settings, ExternalLink } from "lucide-react";

interface MCPServer {
    id: string;
    name: string;
    command: string;
    args: string[];
    enabled: boolean;
}

interface MCPManagerModalProps {
    isOpen: boolean;
    onClose: () => void;
    onChanged: () => void;
}

export default function MCPManagerModal({ isOpen, onClose, onChanged }: MCPManagerModalProps) {
    const [servers, setServers] = useState<MCPServer[]>([]);
    const [loading, setLoading] = useState(true);
    const [newServer, setNewServer] = useState({ id: '', name: '', command: 'npx', args: '' });

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    const fetchServers = React.useCallback(async () => {
        try {
            const res = await fetch(`${apiUrl}/api/mcp/servers`);
            const data = await res.json();
            setServers(data);
        } catch (err) {
            console.error("Failed to fetch MCP servers:", err);
        } finally {
            setLoading(false);
        }
    }, [apiUrl]);

    useEffect(() => {
        if (isOpen) fetchServers();
    }, [isOpen, fetchServers]);

    const handleAdd = async () => {
        if (!newServer.id || !newServer.command) return;
        try {
            await fetch(`${apiUrl}/api/mcp/servers`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: newServer.id,
                    name: newServer.name || newServer.id,
                    command: newServer.command,
                    args: newServer.args.split(' ').filter(a => a.trim() !== '')
                })
            });
            setNewServer({ id: '', name: '', command: 'npx', args: '' });
            fetchServers();
            onChanged();
        } catch (err) {
            console.error("Failed to add MCP server:", err);
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await fetch(`${apiUrl}/api/mcp/servers/${id}`, { method: 'DELETE' });
            fetchServers();
            onChanged();
        } catch (err) {
            console.error("Failed to delete MCP server:", err);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-md p-4" onClick={onClose}>
            <div className="bg-neutral-900 border border-neutral-800 w-full max-w-2xl rounded-3xl overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-200" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="p-6 border-b border-neutral-800 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-xl">
                            <Settings className="w-5 h-5 text-blue-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">MCP Infrastructure</h2>
                            <p className="text-xs text-neutral-500 uppercase tracking-widest font-mono">Model Context Protocol Management</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-neutral-800 rounded-xl text-neutral-400 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <div className="p-6 space-y-8 max-h-[70vh] overflow-y-auto custom-scrollbar">
                    {/* Active Servers List */}
                    <div className="space-y-4">
                        <h3 className="text-xs font-bold text-neutral-500 uppercase tracking-widest">Active Bridges</h3>
                        {loading ? (
                            <div className="py-8 text-center text-neutral-600 animate-pulse">Scanning network...</div>
                        ) : servers.length === 0 ? (
                            <div className="py-8 text-center border-2 border-dashed border-neutral-800 rounded-2xl text-neutral-600">
                                No MCP servers configured
                            </div>
                        ) : (
                            <div className="grid gap-3">
                                {servers.map(s => (
                                    <div key={s.id} className="group p-4 bg-neutral-800/30 border border-neutral-800/50 rounded-2xl flex items-center justify-between hover:border-neutral-700 transition-all">
                                        <div className="flex items-center gap-4">
                                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                                            <div>
                                                <div className="font-semibold text-neutral-200">{s.name}</div>
                                                <div className="text-[10px] font-mono text-neutral-500 mt-0.5">
                                                    {s.command} {s.args.join(' ')}
                                                </div>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => handleDelete(s.id)}
                                            className="p-2 text-neutral-600 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* New Server Form */}
                    <div className="p-6 bg-neutral-800/20 border border-neutral-800 rounded-3xl space-y-4">
                        <h3 className="text-xs font-bold text-neutral-500 uppercase tracking-widest flex items-center gap-2">
                            Deploy New Bridge
                        </h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <label className="text-[10px] text-neutral-500 uppercase font-black ml-1">Unique ID</label>
                                <input
                                    className="w-full bg-neutral-900 border border-neutral-800 rounded-xl px-4 py-2.5 text-sm text-white focus:border-blue-500/50 outline-none transition-all"
                                    placeholder="e.g. google-maps"
                                    value={newServer.id}
                                    onChange={e => setNewServer({ ...newServer, id: e.target.value })}
                                />
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-[10px] text-neutral-500 uppercase font-black ml-1">Display Name</label>
                                <input
                                    className="w-full bg-neutral-900 border border-neutral-800 rounded-xl px-4 py-2.5 text-sm text-white focus:border-blue-500/50 outline-none transition-all"
                                    placeholder="Google Maps MCP"
                                    value={newServer.name}
                                    onChange={e => setNewServer({ ...newServer, name: e.target.value })}
                                />
                            </div>
                        </div>
                        <div className="grid grid-cols-4 gap-4">
                            <div className="space-y-1.5 col-span-1">
                                <label className="text-[10px] text-neutral-500 uppercase font-black ml-1">Binary</label>
                                <input
                                    className="w-full bg-neutral-900 border border-neutral-800 rounded-xl px-4 py-2.5 text-sm text-white focus:border-blue-500/50 outline-none transition-all"
                                    placeholder="npx"
                                    value={newServer.command}
                                    onChange={e => setNewServer({ ...newServer, command: e.target.value })}
                                />
                            </div>
                            <div className="space-y-1.5 col-span-3">
                                <label className="text-[10px] text-neutral-500 uppercase font-black ml-1">Arguments</label>
                                <input
                                    className="w-full bg-neutral-900 border border-neutral-800 rounded-xl px-4 py-2.5 text-sm text-white focus:border-blue-500/50 outline-none transition-all"
                                    placeholder="-y @modelcontextprotocol/server-..."
                                    value={newServer.args}
                                    onChange={e => setNewServer({ ...newServer, args: e.target.value })}
                                />
                            </div>
                        </div>
                        <button
                            onClick={handleAdd}
                            disabled={!newServer.id || !newServer.command}
                            className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-neutral-800 disabled:text-neutral-600 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2 mt-2 shadow-lg shadow-blue-500/10"
                        >
                            <Plus size={18} />
                            Provision MCP Server
                        </button>
                    </div>
                </div>

                <div className="p-4 border-t border-neutral-800 bg-neutral-950/50 flex justify-center">
                    <a
                        href="https://glama.ai/mcp/servers"
                        target="_blank"
                        rel="noreferrer"
                        className="text-[10px] text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1 font-mono uppercase tracking-widest"
                    >
                        Browse Registry <ExternalLink size={10} />
                    </a>
                </div>
            </div>
        </div>
    );
}
