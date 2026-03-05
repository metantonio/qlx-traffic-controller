"use client";

import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import mermaid from "mermaid";

// Initialize mermaid
if (typeof window !== "undefined") {
    mermaid.initialize({
        startOnLoad: true,
        theme: "dark",
        securityLevel: "loose",
        fontFamily: "Inter, sans-serif",
    });
}

const Mermaid = ({ chart }: { chart: string }) => {
    const [svg, setSvg] = useState<string>("");
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const renderChart = async () => {
            if (!chart.trim()) return;

            try {
                const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
                const { svg } = await mermaid.render(id, chart);
                setSvg(svg);
                setError(null);
            } catch (err) {
                console.error("Mermaid rendering error:", err);
                setError("Failed to render diagram");
            }
        };

        renderChart();
    }, [chart]);

    if (error) {
        return (
            <div className="p-4 bg-red-900/10 border border-red-900/20 rounded-lg text-red-400 text-xs font-mono">
                {error}
                <pre className="mt-2 text-[10px] opacity-70 overflow-x-auto">{chart}</pre>
            </div>
        );
    }

    return (
        <div
            className="mermaid-container my-4 overflow-x-auto flex justify-center bg-neutral-900/50 p-4 rounded-xl border border-neutral-800"
            dangerouslySetInnerHTML={{ __html: svg }}
        />
    );
};

interface MarkdownRendererProps {
    content: string;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
    return (
        <div className="markdown-body prose prose-invert max-w-none text-sm leading-relaxed">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
                    code({ inline, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || "");
                        const lang = match ? match[1] : "";

                        if (!inline && lang === "mermaid") {
                            return <Mermaid chart={String(children).replace(/\n$/, "")} />;
                        }

                        return (
                            <code
                                className={`${className} ${inline
                                    ? "bg-neutral-800 px-1.5 py-0.5 rounded text-blue-300 font-mono"
                                    : "block bg-neutral-900 p-4 rounded-xl border border-neutral-800 font-mono text-xs overflow-x-auto my-4 text-emerald-300"
                                    }`}
                                {...props}
                            >
                                {children}
                            </code>
                        );
                    },
                    p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
                    ul: ({ children }) => <ul className="list-disc pl-6 mb-4">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal pl-6 mb-4">{children}</ol>,
                    li: ({ children }) => <li className="mb-1">{children}</li>,
                    h1: ({ children }) => <h1 className="text-xl font-bold mb-4 text-white border-b border-neutral-800 pb-2">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-lg font-bold mb-3 text-white">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-md font-bold mb-2 text-white">{children}</h3>,
                    a: ({ href, children }) => (
                        <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                            {children}
                        </a>
                    ),
                    table: ({ children }) => (
                        <div className="overflow-x-auto mb-4 border border-neutral-800 rounded-xl">
                            <table className="w-full text-left border-collapse">{children}</table>
                        </div>
                    ),
                    thead: ({ children }) => <thead className="bg-neutral-800/50">{children}</thead>,
                    th: ({ children }) => <th className="p-3 border-b border-neutral-700 font-bold text-xs uppercase text-neutral-400">{children}</th>,
                    td: ({ children }) => <td className="p-3 border-b border-neutral-800 text-xs">{children}</td>,
                    blockquote: ({ children }) => (
                        <blockquote className="border-l-4 border-blue-500/50 bg-blue-500/5 p-4 rounded-r-xl italic my-4 text-neutral-400">
                            {children}
                        </blockquote>
                    ),
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
