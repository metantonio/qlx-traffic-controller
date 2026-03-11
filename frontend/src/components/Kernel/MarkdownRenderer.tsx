"use client";

import React, { useEffect, useState, useRef, memo } from "react";
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

const Mermaid = memo(({ chart }: { chart: string }) => {
    const [svg, setSvg] = useState<string>("");
    const [error, setError] = useState<string | null>(null);
    const [isVisible, setIsVisible] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setIsVisible(true);
                    observer.disconnect();
                }
            },
            { threshold: 0.1 }
        );

        if (containerRef.current) {
            observer.observe(containerRef.current);
        }

        return () => observer.disconnect();
    }, []);

    useEffect(() => {
        if (!isVisible || !chart.trim()) return;

        const renderChart = async () => {
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
    }, [chart, isVisible]);

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
            ref={containerRef}
            className="mermaid-container my-4 min-h-[100px] overflow-x-auto flex justify-center bg-neutral-900/50 p-4 rounded-xl border border-neutral-800"
            dangerouslySetInnerHTML={{ __html: svg }}
        />
    );
});
Mermaid.displayName = 'Mermaid';

interface MarkdownRendererProps {
    content: string;
}

const MarkdownRenderer = memo(({ content }: MarkdownRendererProps) => {
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
                    img: ({ src, alt }) => {
                        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
                        const srcStr = typeof src === 'string' ? src : '';
                        const fullSrc = srcStr.startsWith('/') && !srcStr.startsWith('http') 
                            ? `${apiUrl}${srcStr}` 
                            : srcStr;
                        
                        return (
                            <div className="my-6 rounded-2xl overflow-hidden border border-neutral-800 shadow-2xl group relative" key={srcStr}>
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img 
                                    src={fullSrc} 
                                    alt={alt || "Screenshot"} 
                                    className="w-full h-auto cursor-zoom-in group-hover:scale-[1.02] transition-transform duration-500"
                                    onClick={() => window.open(fullSrc, '_blank')}
                                />
                                <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button 
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            window.open(fullSrc, '_blank');
                                        }}
                                        className="bg-black/60 backdrop-blur-md text-white px-3 py-1.5 rounded-lg text-xs font-bold border border-white/10 hover:bg-black/80 transition-colors flex items-center gap-2"
                                    >
                                        Open Full Size
                                    </button>
                                </div>
                            </div>
                        );
                    }
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
});
MarkdownRenderer.displayName = 'MarkdownRenderer';

export default MarkdownRenderer;
