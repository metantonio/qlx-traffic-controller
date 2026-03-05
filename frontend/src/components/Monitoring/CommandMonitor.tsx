"use client";

import { useState } from "react";

export interface CommandEvent {
    type: string;
    source: string;
    payload: Record<string, any>;
    timestamp?: number;
}

interface CommandMonitorProps {
    events: CommandEvent[];
}

export default function CommandMonitor({ events }: CommandMonitorProps) {
    const [filter, setFilter] = useState("");

    const commandEvents = events
        .filter((e) => e.type === "tool_requested" || e.type === "security_alert" || e.type === "agent_output")
        .filter((e) => !filter || e.source.toLowerCase().includes(filter.toLowerCase()));

    const formatTime = (ts?: number) => {
        if (!ts) return "00:00:00";
        return new Date(ts * 1000).toLocaleTimeString([], { hour12: false });
    };

    return (
        <div className="flex flex-col h-[500px] bg-[#0d0d0f] rounded-2xl border border-neutral-800/50 shadow-inner overflow-hidden">
            {/* Header / Filter bar */}
            <div className="p-3 bg-neutral-900/40 border-b border-neutral-800/50 flex items-center gap-2">
                <div className="relative flex-1">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-neutral-600">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                    <input
                        type="text"
                        placeholder="Filter by Agent PID..."
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        className="w-full bg-neutral-950 border border-neutral-800 rounded-lg py-1.5 pl-9 pr-3 text-xs placeholder:text-neutral-700 focus:outline-none focus:border-blue-500/30 font-mono text-neutral-300 transition-all"
                    />
                </div>
            </div>

            {/* Logs Area */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 font-mono text-[11px] leading-relaxed custom-scrollbar">
                {commandEvents.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-neutral-700 space-y-3 opacity-40">
                        <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <span className="text-xs uppercase tracking-widest font-bold font-sans">No logs found</span>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {commandEvents.map((event, idx) => (
                            <div key={idx} className="group flex flex-col gap-1.5 border-l-2 border-neutral-800 hover:border-neutral-700 pl-4 py-0.5 transition-all">
                                <div className="flex items-center justify-between mb-0.5">
                                    <div className="flex items-center gap-3">
                                        <span className="text-neutral-600 font-bold bg-neutral-950 px-1.5 py-0.5 rounded border border-neutral-800/50">
                                            {formatTime(event.timestamp)}
                                        </span>
                                        <span className={`font-black tracking-tighter uppercase px-2 py-0.5 rounded text-[9px] ${event.type === 'security_alert' ? 'bg-red-500/10 text-red-400' :
                                                event.type === 'agent_output' ? 'bg-blue-500/10 text-blue-400' :
                                                    'bg-emerald-500/10 text-emerald-400'
                                            }`}>
                                            {event.source}
                                        </span>
                                    </div>
                                    <span className="text-[9px] text-neutral-700 uppercase font-black tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">
                                        {event.type.replace('_', ' ')}
                                    </span>
                                </div>
                                <div className={`${event.type === 'security_alert' ? 'text-red-300' :
                                        event.type === 'agent_output' ? 'text-neutral-200' : 'text-neutral-400'
                                    } break-words whitespace-pre-wrap`}>
                                    {event.type === 'security_alert' ? (
                                        <div className="flex items-start gap-2 bg-red-500/5 p-2 rounded border border-red-500/10">
                                            <svg className="w-3.5 h-3.5 text-red-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                            </svg>
                                            <span className="font-semibold">{event.payload.message}</span>
                                        </div>
                                    ) : event.type === 'agent_output' ? (
                                        <div className="flex flex-col gap-1.5">
                                            <div className="flex items-center gap-2 text-neutral-500">
                                                <span className="h-px bg-neutral-800 flex-1"></span>
                                                <span className="text-[9px] uppercase tracking-tighter">Summary</span>
                                                <span className="h-px bg-neutral-800 flex-1"></span>
                                            </div>
                                            <span className="text-blue-200 leading-relaxed font-sans text-xs">
                                                {event.payload.response}
                                            </span>
                                        </div>
                                    ) : (
                                        <div className="bg-neutral-900/30 p-2 rounded-lg border border-neutral-800/30">
                                            <span className="text-emerald-500/70 mr-2 opacity-50 font-black">❯</span>
                                            <span className="text-emerald-400 font-bold">{event.payload.tool}</span>
                                            <span className="text-neutral-500 mx-1">(</span>
                                            <span className="text-neutral-300 italic">{JSON.stringify(event.payload.arguments)}</span>
                                            <span className="text-neutral-500">)</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
