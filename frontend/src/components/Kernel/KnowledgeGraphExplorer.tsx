"use client";

import { useEffect, useState, useRef, useMemo } from "react";
import dynamic from "next/dynamic";
import { Maximize2, RefreshCw, ZoomIn } from "lucide-react";

// Dynamically import ForceGraph2D with SSR disabled
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
    ssr: false,
});

interface GraphEntity {
    name: string;
    entityType: string;
    observations: string[];
}

interface GraphRelation {
    from: string;
    to: string;
    relationType: string;
}

interface GraphNode {
    id: string;
    name: string;
    type: string;
    color: string;
    x?: number;
    y?: number;
}

interface GraphData {
    entities: GraphEntity[];
    relations: GraphRelation[];
}

export default function KnowledgeGraphExplorer() {
    const [data, setData] = useState<GraphData>({ entities: [], relations: [] });
    const [loading, setLoading] = useState(true);
    const fgRef = useRef<any>(undefined);

    const fetchData = async () => {
        setLoading(true);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
            const response = await fetch(`${apiUrl}/api/memory`);
            if (!response.ok) throw new Error("Failed to fetch memory graph");
            const result = await response.json();
            setData(result);
        } catch (error) {
            console.error("Error fetching knowledge graph:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const graphData = useMemo(() => {
        const nodes: GraphNode[] = data.entities.map((e) => ({
            id: e.name,
            name: e.name,
            type: e.entityType,
            color: e.entityType === "Person" ? "#3b82f6" : "#a855f7",
        }));

        const links = data.relations.map((r) => ({
            source: r.from,
            target: r.to,
            label: r.relationType,
        }));

        return { nodes, links };
    }, [data]);

    return (
        <div className="relative w-full h-full min-h-[400px] bg-neutral-950/20 border border-neutral-800 rounded-3xl overflow-hidden group">
            <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
                <button
                    onClick={fetchData}
                    className="p-2 rounded-xl bg-neutral-900/80 border border-neutral-800 text-neutral-400 hover:text-white hover:bg-neutral-800 transition-all shadow-lg backdrop-blur-md"
                    title="Refresh Graph"
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                </button>
                <div className="h-4 w-px bg-neutral-800 mx-1"></div>
                <button
                    onClick={() => fgRef.current?.zoomToFit(400)}
                    className="p-2 rounded-xl bg-neutral-900/80 border border-neutral-800 text-neutral-400 hover:text-white hover:bg-neutral-800 transition-all shadow-lg backdrop-blur-md"
                >
                    <ZoomIn className="w-4 h-4" />
                </button>
            </div>

            <div className="absolute bottom-4 right-4 z-10 flex flex-col gap-2">
                <div className="p-3 rounded-xl bg-neutral-900/80 border border-neutral-800 backdrop-blur-md shadow-lg text-[10px] font-bold uppercase tracking-widest space-y-2">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                        <span className="text-neutral-400">Person</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                        <span className="text-neutral-400">Other Entity</span>
                    </div>
                </div>
            </div>

            {graphData.nodes.length === 0 && !loading ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-neutral-600 pointer-events-none">
                    <Maximize2 className="w-12 h-12 mb-4 opacity-10" />
                    <span className="font-mono text-xs tracking-tighter opacity-40 uppercase">No neural links established. Run memory tasks to populate.</span>
                </div>
            ) : (
                <ForceGraph2D
                    ref={fgRef}
                    graphData={graphData}
                    nodeLabel={(node: any) => `${(node as GraphNode).id} (${(node as GraphNode).type})`}
                    linkLabel={(link: any) => link.label}
                    nodeColor={(node: any) => (node as GraphNode).color}
                    nodeRelSize={6}
                    linkDirectionalArrowLength={3.5}
                    linkDirectionalArrowRelPos={1}
                    linkCurvature={0.25}
                    linkColor={() => "#333"}
                    nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
                        const gNode = node as GraphNode;
                        const label = gNode.id;
                        const fontSize = 12 / globalScale;
                        ctx.font = `${fontSize}px Inter`;

                        ctx.fillStyle = gNode.color;
                        ctx.beginPath(); ctx.arc(gNode.x || 0, gNode.y || 0, 4, 0, 2 * Math.PI, false); ctx.fill();

                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillStyle = '#888';
                        ctx.fillText(label, gNode.x || 0, (gNode.y || 0) + 8);
                    }}
                    backgroundColor="rgba(0,0,0,0)"
                />
            )}
        </div>
    );
}
