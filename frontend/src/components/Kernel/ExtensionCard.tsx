"use client";

import React from "react";
import { Download, Settings, ExternalLink } from "lucide-react";

interface ExtensionCardProps {
    id: string;
    name: string;
    description: string;
    type: 'skill' | 'mcp';
    status: 'installed' | 'available';
    enabled?: boolean;
    onToggle?: (enabled: boolean) => void;
    onInstall?: () => void;
    onUninstall?: () => void;
    onConfigure?: () => void;
    requiresKey?: boolean;
    icon?: React.ReactNode;
}

export default function ExtensionCard({
    id,
    name,
    description,
    type,
    status,
    enabled = true,
    onToggle,
    onInstall,
    onUninstall,
    onConfigure,
    requiresKey,
    icon
}: ExtensionCardProps) {
    return (
        <div className="group p-6 bg-neutral-900/40 border border-neutral-800/80 rounded-3xl hover:border-neutral-700 hover:bg-neutral-800/40 transition-all duration-300 flex flex-col gap-5">
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-2xl border ${status === 'installed' ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' : 'bg-neutral-800 border-neutral-700 text-neutral-500'}`}>
                        {icon || (type === 'skill' ? <Settings size={20} /> : <ExternalLink size={20} />)}
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="font-bold text-neutral-100 text-lg tracking-tight">{name}</h3>
                            <div className="flex gap-1">
                                <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-wider ${type === 'skill' ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'}`}>
                                    {type}
                                </span>
                                {status === 'installed' && (
                                    <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 rounded text-[9px] font-black uppercase tracking-wider">
                                        Local
                                    </span>
                                )}
                            </div>
                        </div>
                        <div className="text-[10px] font-mono text-neutral-600 mt-1 uppercase tracking-tighter">ID: {id}</div>
                    </div>
                </div>

                {status === 'installed' ? (
                    <button
                        onClick={() => onToggle?.(!enabled)}
                        className={`relative w-11 h-6 rounded-full transition-colors ${enabled ? 'bg-orange-600' : 'bg-neutral-800'}`}
                    >
                        <div className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${enabled ? 'translate-x-5' : 'translate-x-0'}`} />
                    </button>
                ) : (
                    <button
                        onClick={onInstall}
                        className="p-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded-xl transition-all"
                        title="Install Extension"
                    >
                        <Download size={18} />
                    </button>
                )}
            </div>

            <p className="text-xs text-neutral-500 leading-relaxed line-clamp-2 min-h-[2.5rem]">
                {description}
            </p>

            <div className="flex items-center justify-between mt-auto pt-4 border-t border-neutral-800/50">
                <div className="flex items-center gap-2">
                    {status === 'installed' && (
                        <div className="flex items-center gap-1.5 text-[10px] font-bold text-neutral-500 uppercase tracking-widest">
                            <div className={`w-1.5 h-1.5 rounded-full ${enabled ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 'bg-neutral-700'}`} />
                            {enabled ? 'Active' : 'Disabled'}
                        </div>
                    )}
                </div>

                <div className="flex items-center gap-2">
                    {status === 'installed' && onConfigure && (
                        <button
                            onClick={onConfigure}
                            className="p-2 text-neutral-600 hover:text-blue-400 hover:bg-blue-400/10 rounded-xl transition-all"
                            title="Configure"
                        >
                            <Settings size={16} />
                        </button>
                    )}
                    {status === 'installed' && onUninstall && (
                        <button
                            onClick={onUninstall}
                            className="px-3 py-1.5 text-[10px] font-black uppercase tracking-widest text-red-400/60 hover:text-red-400 bg-red-400/5 hover:bg-red-400/10 border border-red-400/10 rounded-xl transition-all"
                        >
                            Uninstall
                        </button>
                    )}
                    {status === 'available' && (
                        <button
                            onClick={onInstall}
                            className="px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white text-[10px] font-black uppercase tracking-widest rounded-xl shadow-lg shadow-orange-600/20 transition-all"
                        >
                            {requiresKey ? 'Configure & Install' : 'Quick Install'}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
