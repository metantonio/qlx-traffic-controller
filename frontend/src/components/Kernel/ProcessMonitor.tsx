"use client";

import { KernelMetrics } from "@/app/page";
import { X, Trash2 } from "lucide-react";

interface ProcessMonitorProps {
    metrics: KernelMetrics | null;
    onProcessClick?: (pid: string) => void;
    onDismiss?: (pid: string) => void;
    onClearFinished?: () => void;
}

export default function ProcessMonitor({ metrics, onProcessClick, onDismiss, onClearFinished }: ProcessMonitorProps) {
    const activeProcesses = metrics?.processes || [];

    const getStatusColor = (state: string) => {
        switch (state) {
            case "running": return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
            case "queued": return "text-blue-400 bg-blue-500/10 border-blue-500/20";
            case "paused": return "text-amber-400 bg-amber-500/10 border-amber-500/20";
            default: return "text-neutral-400 bg-neutral-500/10 border-neutral-500/20";
        }
    };

    return (
        <div className="overflow-x-auto text-sm w-full">
            <table className="w-full text-left font-mono border-collapse">
                <thead className="text-neutral-500 border-b border-neutral-800">
                    <tr>
                        <th className="py-2 px-3">PID</th>
                        <th className="py-2 px-3">PROCESS / AGENT</th>
                        <th className="py-2 px-3">STATE</th>
                        <th className="py-2 px-3">MEM</th>
                        <th className="py-2 px-3">CPU</th>
                        <th className="py-2 px-3 text-right">
                            {onClearFinished && (
                                <button
                                    onClick={(e) => { e.stopPropagation(); onClearFinished(); }}
                                    className="p-1 hover:bg-red-500/10 rounded text-neutral-600 hover:text-red-400 transition-colors"
                                    title="Clear all finished"
                                >
                                    <Trash2 size={12} />
                                </button>
                            )}
                        </th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/50">
                    {activeProcesses.map((proc) => (
                        <tr
                            key={proc.pid}
                            onClick={() => onProcessClick?.(proc.pid)}
                            className={`transition-all group cursor-pointer border-l-2 ${proc.state === 'running'
                                ? 'bg-blue-500/5 border-blue-500 shadow-[inset_10px_0_20px_-10px_rgba(59,130,246,0.2)]'
                                : 'hover:bg-neutral-800/30 border-transparent hover:border-neutral-700'
                                }`}
                        >
                            <td className="py-3 px-3 text-neutral-400">#{proc.pid}</td>
                            <td className="py-3 px-3 text-neutral-200">
                                <span className="flex items-center gap-2">
                                    <div className={`w-1 h-1 rounded-full ${proc.state === 'running' ? 'bg-blue-400 animate-breathing' : 'bg-neutral-600'}`} />
                                    {proc.agent}
                                </span>
                            </td>
                            <td className="py-3 px-3">
                                <span className={`px-2 py-0.5 rounded-full border text-xs font-medium uppercase tracking-wider ${getStatusColor(proc.state)}`}>
                                    {proc.state}
                                </span>
                            </td>
                            <td className="py-3 px-3 text-neutral-400">{proc.mem}</td>
                            <td className="py-3 px-3 text-neutral-400">{proc.cpu}</td>
                            <td className="py-3 px-3 text-right">
                                {(proc.state === "completed" || proc.state === "failed") && onDismiss && (
                                    <button
                                        onClick={(e) => { e.stopPropagation(); onDismiss(proc.pid); }}
                                        className="p-1.5 hover:bg-neutral-700/50 rounded-lg text-neutral-500 hover:text-white transition-all opacity-0 group-hover:opacity-100"
                                        title="Dismiss Process"
                                    >
                                        <X size={14} />
                                    </button>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
