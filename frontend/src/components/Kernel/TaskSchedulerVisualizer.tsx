"use client";

import { KernelMetrics } from "@/app/page";

interface TaskSchedulerVisualizerProps {
    metrics: KernelMetrics | null;
}

export default function TaskSchedulerVisualizer({ metrics }: TaskSchedulerVisualizerProps) {
    const qState = metrics?.queues || { HIGH: 0, MEDIUM: 0, LOW: 0 };
    const maxConcurrent = 3; // From Kernel defaults
    const activeRunning = metrics?.active_count || 0;

    const queues = [
        { priority: "HIGH", count: qState.HIGH, limit: 3, color: "bg-rose-500", text: "text-rose-400" },
        { priority: "MEDIUM", count: qState.MEDIUM, limit: 5, color: "bg-blue-500", text: "text-blue-400" },
        { priority: "LOW", count: qState.LOW, limit: 10, color: "bg-neutral-500", text: "text-neutral-400" },
    ];

    return (
        <div className="flex flex-col gap-4 font-mono text-sm w-full">
            <div className="flex justify-between items-center mb-2">
                <span className="text-neutral-400 text-xs uppercase tracking-widest">Active Dispatcher</span>
                <span className="flex items-center gap-2 text-emerald-400 text-xs">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    SCHEDULER Ticking
                </span>
            </div>

            {queues.map((q) => (
                <div key={q.priority} className="flex flex-col gap-2">
                    <div className="flex justify-between items-center">
                        <span className={`${q.text} font-bold tracking-wide`}>{q.priority} QUEUE</span>
                        <span className="text-neutral-500">[{q.count} / {q.limit}]</span>
                    </div>
                    <div className="w-full bg-neutral-900 rounded-full h-2.5 outline outline-1 outline-neutral-800">
                        <div
                            className={`${q.color} h-2.5 rounded-full shadow-[0_0_10px_currentColor] transition-all duration-500`}
                            style={{ width: `${Math.max(5, (q.count / q.limit) * 100)}%` }}
                        ></div>
                    </div>
                </div>
            ))}

            <div className="mt-4 p-3 bg-neutral-900/50 border border-neutral-800 rounded text-xs text-neutral-400 flex flex-col gap-1">
                <div className="flex justify-between">
                    <span>Max Concurrent Processes:</span>
                    <span className="text-neutral-200">{maxConcurrent}</span>
                </div>
                <div className="flex justify-between">
                    <span>Current Load:</span>
                    <span className="text-cyan-400 font-bold">{Math.round((activeRunning / maxConcurrent) * 100)}% ({activeRunning} Running)</span>
                </div>
            </div>
        </div>
    );
}
