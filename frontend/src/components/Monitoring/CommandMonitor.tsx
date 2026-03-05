"use client";

export interface CommandEvent {
    type: string;
    source: string;
    payload: Record<string, any>;
}

interface CommandMonitorProps {
    events: CommandEvent[];
}

export default function CommandMonitor({ events }: CommandMonitorProps) {
    const commandEvents = events.filter((e) => e.type === "tool_requested" || e.type === "security_alert" || e.type === "agent_output");

    return (
        <div className="bg-neutral-950 font-mono text-sm rounded-xl border border-neutral-800 h-[400px] overflow-y-auto overflow-x-hidden p-4 shadow-inner">
            {commandEvents.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-neutral-600 space-y-3">
                    <svg className="w-8 h-8 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span>Waiting for command execution logs...</span>
                </div>
            ) : (
                <div className="space-y-3">
                    {commandEvents.map((event, idx) => (
                        <div key={idx} className="flex flex-col gap-1 border-b border-neutral-800/60 pb-3 last:border-0 hover:bg-neutral-900/30 rounded px-2 py-1 transition-colors">
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-neutral-500">{new Date().toLocaleTimeString()}</span>
                                <span className={`px-2 py-0.5 rounded ${event.type === 'security_alert' ? 'bg-red-500/20 text-red-400' : event.type === 'agent_output' ? 'bg-purple-500/20 text-purple-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                                    {event.source}
                                </span>
                            </div>
                            <div className={`${event.type === 'security_alert' ? 'text-red-300' : event.type === 'agent_output' ? 'text-neutral-200' : 'text-neutral-300'} break-words whitespace-pre-wrap`}>
                                {event.type === 'security_alert' ? (
                                    <span className="flex items-center gap-2">
                                        <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                        </svg>
                                        {event.payload.message}
                                    </span>
                                ) : event.type === 'agent_output' ? (
                                    <div className="flex flex-col gap-1">
                                        <span className="text-neutral-500 text-xs mt-1">Task: {event.payload.task}</span>
                                        <span className="text-purple-300 mt-1 pl-2 border-l-2 border-purple-500/30">
                                            {event.payload.response}
                                        </span>
                                    </div>
                                ) : (
                                    <span><span className="text-blue-400 mr-2">$</span>{event.payload.tool}({JSON.stringify(event.payload.arguments)})</span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
