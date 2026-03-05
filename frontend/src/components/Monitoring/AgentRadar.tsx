"use client";

interface AgentRadarProps {
    events: any[];
}

export default function AgentRadar({ events }: AgentRadarProps) {
    // Extract active agents from events (mock logic for scaffold)
    const activeAgents = [
        { name: "document_agent", role: "Document Analyzer", status: "idle" },
        { name: "research_agent", role: "Web Researcher", status: "processing" },
        { name: "system_assistant", role: "General Automation", status: "idle" },
    ];

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {activeAgents.map((agent) => (
                <div
                    key={agent.name}
                    className="relative overflow-hidden group border border-neutral-800 rounded-xl p-5 bg-gradient-to-b from-neutral-800/40 to-neutral-900/40 hover:border-neutral-700 transition-all duration-300"
                >
                    {/* Status Indicator Glow */}
                    <div className={`absolute top-0 left-0 w-full h-1 ${agent.status === 'processing' ? 'bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.5)]' : 'bg-neutral-700'}`} />

                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <h3 className="font-mono text-sm font-bold text-neutral-200">{agent.name}</h3>
                            <p className="text-xs text-neutral-400 mt-1">{agent.role}</p>
                        </div>
                        <div className={`p-1.5 rounded-md ${agent.status === 'processing' ? 'bg-blue-500/10 text-blue-400' : 'bg-neutral-800 text-neutral-500'}`}>
                            <svg className={`w-4 h-4 ${agent.status === 'processing' ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                        </div>
                    </div>

                    <div className="flex items-center gap-2 text-xs font-medium">
                        <span className={`px-2 py-0.5 rounded-full ${agent.status === 'processing' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' : 'bg-neutral-800 text-neutral-400 border border-neutral-700'}`}>
                            {agent.status.toUpperCase()}
                        </span>
                    </div>
                </div>
            ))}
        </div>
    );
}
