import React, { useEffect, useRef, useState } from 'react';
import { KnowledgeGraphData, GraphNode, GraphLink } from '../../types';
import { Activity, ShieldCheck, ZoomIn, ZoomOut, RotateCcw, Info } from 'lucide-react';

interface KnowledgeGraphViewProps {
  data: KnowledgeGraphData | null;
  height?: number;
}

export const KnowledgeGraphView: React.FC<KnowledgeGraphViewProps> = ({ data, height = 520 }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [zoom, setZoom] = useState(1);
  const animFrameRef = useRef<number | null>(null);

  const nodesRef = useRef<GraphNode[]>([]);
  const linksRef = useRef<GraphLink[]>([]);
  const draggingNodeRef = useRef<GraphNode | null>(null);

  useEffect(() => {
    if (!data) return;

    const width = 800;
    const h = height;

    // Initialize node positions in a circle
    const nodes = data.nodes.map((node, i) => {
      const angle = (i / data.nodes.length) * 2 * Math.PI;
      const radius = 180;
      return {
        ...node,
        x: width / 2 + Math.cos(angle) * radius + (Math.random() - 0.5) * 40,
        y: h / 2 + Math.sin(angle) * radius + (Math.random() - 0.5) * 40,
        vx: 0,
        vy: 0,
      };
    });

    nodesRef.current = nodes;
    linksRef.current = data.links;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let step = 0;
    const animate = () => {
      step++;
      const currentNodes = nodesRef.current;
      const currentLinks = linksRef.current;

      // Simple force simulation for stability
      if (step < 200) {
        // Link attraction
        currentLinks.forEach((link) => {
          const source = currentNodes.find((n) => n.id === link.source);
          const target = currentNodes.find((n) => n.id === link.target);
          if (source && target) {
            const dx = (target.x || 0) - (source.x || 0);
            const dy = (target.y || 0) - (source.y || 0);
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const targetDist = 110;
            const force = (dist - targetDist) * 0.015;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            if (source !== draggingNodeRef.current) {
              source.x = (source.x || 0) + fx;
              source.y = (source.y || 0) + fy;
            }
            if (target !== draggingNodeRef.current) {
              target.x = (target.x || 0) - fx;
              target.y = (target.y || 0) - fy;
            }
          }
        });

        // Node repulsion
        for (let i = 0; i < currentNodes.length; i++) {
          for (let j = i + 1; j < currentNodes.length; j++) {
            const a = currentNodes[i];
            const b = currentNodes[j];
            const dx = (b.x || 0) - (a.x || 0);
            const dy = (b.y || 0) - (a.y || 0);
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            if (dist < 150) {
              const rep = (150 - dist) * 0.02;
              const rx = (dx / dist) * rep;
              const ry = (dy / dist) * rep;
              if (a !== draggingNodeRef.current) {
                a.x = (a.x || 0) - rx;
                a.y = (a.y || 0) - ry;
              }
              if (b !== draggingNodeRef.current) {
                b.x = (b.x || 0) + rx;
                b.y = (b.y || 0) + ry;
              }
            }
          }
        }
      }

      // Draw
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.save();
      ctx.scale(zoom, zoom);

      // Draw Links
      currentLinks.forEach((link) => {
        const source = currentNodes.find((n) => n.id === link.source);
        const target = currentNodes.find((n) => n.id === link.target);
        if (source && target) {
          ctx.beginPath();
          ctx.moveTo(source.x || 0, source.y || 0);
          ctx.lineTo(target.x || 0, target.y || 0);
          ctx.strokeStyle = '#cbd5e1';
          ctx.lineWidth = 1.5;
          ctx.stroke();

          // Relation label
          const mx = ((source.x || 0) + (target.x || 0)) / 2;
          const my = ((source.y || 0) + (target.y || 0)) / 2;
          ctx.font = '9px Inter, sans-serif';
          ctx.fillStyle = '#64748b';
          ctx.fillText(link.relation, mx + 4, my - 4);
        }
      });

      // Draw Nodes
      currentNodes.forEach((node) => {
        const x = node.x || 0;
        const y = node.y || 0;
        const isSelected = selectedNode?.id === node.id;

        // Shadow / Glow
        ctx.beginPath();
        ctx.arc(x, y, node.radius + (isSelected ? 6 : 2), 0, 2 * Math.PI);
        ctx.fillStyle = isSelected ? '#fde047' : 'rgba(0,0,0,0.06)';
        ctx.fill();

        // Circle
        ctx.beginPath();
        ctx.arc(x, y, node.radius, 0, 2 * Math.PI);
        ctx.fillStyle = node.color || '#1b5e4b';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Label
        ctx.font = isSelected ? 'bold 11px Inter, sans-serif' : '10px Inter, sans-serif';
        ctx.fillStyle = '#0f172a';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, x, y + node.radius + 14);

        // Type badge inside or beneath
        ctx.font = '8px Inter, sans-serif';
        ctx.fillStyle = '#64748b';
        ctx.fillText(node.type.toUpperCase(), x, y + node.radius + 24);
      });

      ctx.restore();
      animFrameRef.current = requestAnimationFrame(animate);
    };

    animFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [data, zoom, selectedNode]);

  // Click & Drag handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = (e.clientX - rect.left) / zoom;
    const mouseY = (e.clientY - rect.top) / zoom;

    const clicked = nodesRef.current.find((n) => {
      const dx = (n.x || 0) - mouseX;
      const dy = (n.y || 0) - mouseY;
      return Math.sqrt(dx * dx + dy * dy) <= n.radius + 8;
    });

    if (clicked) {
      draggingNodeRef.current = clicked;
      setSelectedNode(clicked);
    } else {
      setSelectedNode(null);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!draggingNodeRef.current) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    draggingNodeRef.current.x = (e.clientX - rect.left) / zoom;
    draggingNodeRef.current.y = (e.clientY - rect.top) / zoom;
  };

  const handleMouseUp = () => {
    draggingNodeRef.current = null;
  };

  if (!data) {
    return (
      <div className="flex items-center justify-center p-12 bg-slate-50 rounded-2xl border border-dashed border-slate-300">
        <div className="text-center">
          <Activity className="w-8 h-8 text-slate-400 mx-auto animate-spin mb-2" />
          <p className="text-sm font-medium text-slate-600">Generating Neo4j Patient Knowledge Graph...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
      {/* Header */}
      <div className="px-5 py-3.5 bg-gradient-to-r from-slate-900 to-ayur-950 text-white flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-bold uppercase tracking-wider">Neo4j Clinical Telemetry Graph</span>
          <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full font-medium">
            Active Consult Mode
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setZoom((z) => Math.min(1.6, z + 0.1))}
            className="p-1 hover:bg-white/10 rounded transition"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.6, z - 0.1))}
            className="p-1 hover:bg-white/10 rounded transition"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="p-1 hover:bg-white/10 rounded transition"
            title="Reset Zoom"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="relative">
        <canvas
          ref={canvasRef}
          width={800}
          height={height}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          className="w-full bg-[#fcfbfa] cursor-grab active:cursor-grabbing block"
        />

        {/* Selected Node Inspector Drawer */}
        {selectedNode && (
          <div className="absolute top-4 right-4 max-w-xs w-full bg-white/95 backdrop-blur-md rounded-xl p-4 shadow-xl border border-slate-200 text-xs animate-in fade-in slide-in-from-right-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-slate-800 uppercase tracking-wider flex items-center space-x-1">
                <Info className="w-3.5 h-3.5 text-ayur-600" />
                <span>Node Inspection</span>
              </span>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>
            <div className="space-y-1.5">
              <p className="font-semibold text-slate-900 text-sm">{selectedNode.label}</p>
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold text-white" style={{ backgroundColor: selectedNode.color }}>
                  {selectedNode.type}
                </span>
                <span className="text-slate-500 text-[10px]">ID: {selectedNode.id}</span>
              </div>
              {selectedNode.details && (
                <div className="bg-slate-50 p-2 rounded-lg border border-slate-200 mt-2 space-y-1">
                  {Object.entries(selectedNode.details).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-[11px]">
                      <span className="text-slate-500 capitalize">{k.replace('_', ' ')}:</span>
                      <span className="font-medium text-slate-800 truncate max-w-[140px]">{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Graph Legend */}
        <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur-xs px-3 py-2 rounded-xl border border-slate-200 shadow-xs flex flex-wrap gap-2 text-[10px] font-semibold text-slate-700">
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#1b5e4b]" />
            <span>Patient</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#9333ea]" />
            <span>Symptom</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#dc2626]" />
            <span>Dosha</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#059669]" />
            <span>Shloka</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#b45309]" />
            <span>Book</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#2563eb]" />
            <span>Doctor</span>
          </div>
        </div>
      </div>
    </div>
  );
};
