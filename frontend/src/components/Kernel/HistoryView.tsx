"use client";

import { useEffect, useState, useCallback } from "react";
import { ChevronLeft, ChevronRight, MessageSquare, Clock, ArrowLeft } from "lucide-react";

interface HistoryItem {
    pid: string;
    agent_name: string;
    task: string;
    state: string;
    created_at: string;
    metrics: {
        tokens_used: number;
        tools_called: number;
        start_time: number | null;
        end_time: number | null;
    };
}

interface HistoryResponse {
    total: number;
    page: number;
    page_size: number;
    items: HistoryItem[];
}

interface HistoryViewProps {
    onSelectPid: (pid: string) => void;
    onBack: () => void;
}

export default function HistoryView({ onSelectPid, onBack }: HistoryViewProps) {
    const [data, setData] = useState<HistoryResponse | null>(null);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);

    const fetchHistory = useCallback(async (pageNum: number) => {
        setLoading(true);
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/history?page=${pageNum}&page_size=10`);
            const result = await response.json();
            setData(result);
        } catch (error) {
            console.error("Failed to fetch history:", error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchHistory(page);
    }, [page, fetchHistory]);

    const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString(undefined, { day: '2-digit', month: '2-digit', year: 'numeric' }) + ' ' +
            date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    };

    const getStatusColor = (state: string) => {
        switch (state) {
            case "completed": return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
            case "failed": return "text-red-400 bg-red-500/10 border-red-500/20";
            case "running": return "text-blue-400 bg-blue-500/10 border-blue-500/20";
            default: return "text-neutral-400 bg-neutral-500/10 border-neutral-500/20";
        }
    };

    return (
        <div className="flex flex-col h-full animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between mb-6">
                <button
                    onClick={onBack}
                    className="flex items-center gap-2 text-neutral-400 hover:text-white transition-colors group"
                >
                    <ArrowLeft size={18} className="group-hover:-translate-x-1 transition-transform" />
                    <span className="text-sm font-bold uppercase tracking-widest">Back to Control Tower</span>
                </button>
                <div className="flex items-center gap-2">
                    <Clock size={16} className="text-blue-500" />
                    <h2 className="text-sm font-bold text-neutral-400 uppercase tracking-widest">Worker History</h2>
                </div>
            </div>

            <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-3xl p-6 shadow-xl backdrop-blur-xl flex-grow overflow-hidden flex flex-col">
                <div className="overflow-x-auto flex-grow">
                    <table className="w-full text-left font-mono border-collapse">
                        <thead className="text-neutral-500 border-b border-neutral-800">
                            <tr>
                                <th className="py-2 px-3">PID</th>
                                <th className="py-2 px-3">AGENT</th>
                                <th className="py-2 px-3">TASK / DESCRIPTION</th>
                                <th className="py-2 px-3">STATUS</th>
                                <th className="py-2 px-3">EXECUTED AT</th>
                                <th className="py-2 px-3 text-right">ACTION</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-neutral-800/50">
                            {loading ? (
                                Array.from({ length: 5 }).map((_, i) => (
                                    <tr key={i} className="animate-pulse">
                                        <td colSpan={6} className="py-4 px-3">
                                            <div className="h-4 bg-neutral-800 rounded w-full"></div>
                                        </td>
                                    </tr>
                                ))
                            ) : data?.items.map((item) => (
                                <tr key={item.pid} className="hover:bg-neutral-800/30 transition-colors group">
                                    <td className="py-4 px-3 text-neutral-400">#{item.pid}</td>
                                    <td className="py-4 px-3 text-neutral-200">{item.agent_name}</td>
                                    <td className="py-4 px-3 text-neutral-400 max-w-md truncate" title={item.task}>
                                        {item.task}
                                    </td>
                                    <td className="py-4 px-3">
                                        <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wider ${getStatusColor(item.state)}`}>
                                            {item.state}
                                        </span>
                                    </td>
                                    <td className="py-4 px-3 text-neutral-500 text-xs">
                                        {item.created_at ? formatDate(item.created_at) : 'N/A'}
                                    </td>
                                    <td className="py-4 px-3 text-right">
                                        <button
                                            onClick={() => onSelectPid(item.pid)}
                                            className="p-2 hover:bg-blue-500/20 rounded-xl text-blue-400 transition-all border border-transparent hover:border-blue-500/30 group/btn"
                                            title="View Conversation"
                                        >
                                            <MessageSquare size={16} className="group-hover/btn:scale-110 transition-transform" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                <div className="mt-6 flex items-center justify-between border-t border-neutral-800 pt-6">
                    <span className="text-xs text-neutral-500 font-medium">
                        Showing <span className="text-neutral-300">{(page - 1) * 10 + 1}</span> to <span className="text-neutral-300">{Math.min(page * 10, data?.total || 0)}</span> of <span className="text-neutral-300">{data?.total || 0}</span> workers
                    </span>

                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1 || loading}
                            className="p-2 rounded-xl border border-neutral-800 hover:border-neutral-700 disabled:opacity-30 transition-all"
                        >
                            <ChevronLeft size={18} />
                        </button>

                        <div className="flex items-center gap-1">
                            {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
                                let pageNum = i + 1;
                                // Basic logic to show pages around current
                                if (totalPages > 5 && page > 3) {
                                    pageNum = page - 2 + i;
                                    if (pageNum > totalPages) pageNum = totalPages - (4 - i);
                                }

                                return (
                                    <button
                                        key={pageNum}
                                        onClick={() => setPage(pageNum)}
                                        className={`w-8 h-8 rounded-xl text-xs font-bold transition-all ${page === pageNum
                                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                                                : 'text-neutral-500 hover:text-white hover:bg-neutral-800'
                                            }`}
                                    >
                                        {pageNum}
                                    </button>
                                );
                            })}
                        </div>

                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page === totalPages || loading}
                            className="p-2 rounded-xl border border-neutral-800 hover:border-neutral-700 disabled:opacity-30 transition-all"
                        >
                            <ChevronRight size={18} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
