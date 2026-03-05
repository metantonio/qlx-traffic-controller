"use client";

import { KernelMetrics } from "@/app/page";

interface ProcessMonitorProps {
    metrics: KernelMetrics | null;
    onProcessClick?: (pid: string) => void;
}

export default function ProcessMonitor({ metrics, onProcessClick }: ProcessMonitorProps) {
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
                    </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/50">
                    {activeProcesses.map((proc) => (
                        <tr key={proc.pid} className="hover:bg-neutral-800/30 transition-colors group">
                            <td className="py-3 px-3 text-neutral-400">#{proc.pid}</td>
                            <td className="py-3 px-3 text-neutral-200">
                                <span className="flex items-center gap-2">
                                    <svg className="w-4 h-4 text-neutral-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 12h14M12 5l7 7-7 7" />
                                    </svg>
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
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
