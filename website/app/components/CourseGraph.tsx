"use client";

import React, { useCallback, useMemo } from "react";
import {
    ReactFlow,
    Node,
    Edge,
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    MarkerType,
    Handle,
    Position,
    NodeProps,
} from "@xyflow/react";
import ELK from "elkjs/lib/elk.bundled.js";
import "@xyflow/react/dist/style.css";
import {
    CourseInfo,
    CourseStructure,
    currentTermCourses,
    Nodes,
} from "../constants";

// Custom node component for courses
function CourseNode({ data }: NodeProps) {
    console.log(data);
    const label = String(data.label || "");
    const subtitle = data.subtitle ? String(data.subtitle) : null;
    const background = String(data.background || "");
    const borderColor = String(data.borderColor || "");
    const textColor = String(data.textColor || "");
    const isSelected = Boolean(data.isSelected);

    return (
        <div
            className={`px-4 py-3 rounded-xl shadow-lg border-2 transition-all duration-200 hover:shadow-xl ${
                isSelected ? "ring-2 ring-indigo-500 ring-offset-2" : ""
            }`}
            style={{
                background,
                borderColor: isSelected ? "#6366f1" : borderColor,
                minWidth: "120px",
            }}
        >
            <Handle
                type="target"
                position={Position.Left}
                className="!bg-slate-400 !w-3 !h-3"
            />
            <div className="text-center">
                <div className="font-bold text-sm" style={{ color: textColor }}>
                    {label}
                </div>
                {subtitle && (
                    <div
                        className="text-xs opacity-70"
                        style={{ color: textColor }}
                    >
                        {subtitle}
                    </div>
                )}
            </div>
            <Handle
                type="source"
                position={Position.Right}
                className="!bg-slate-400 !w-3 !h-3"
            />
        </div>
    );
}

// Custom node for AND/OR gates
function GateNode({ data }: NodeProps) {
    const isAnd = data.gateType === "AND";
    return (
        <div
            className={`px-3 py-2 rounded-lg shadow-md border-2 font-bold text-xs transition-all duration-200 hover:shadow-lg ${
                isAnd
                    ? "bg-gradient-to-br from-amber-100 to-amber-200 border-amber-400 text-amber-800"
                    : "bg-gradient-to-br from-sky-100 to-sky-200 border-sky-400 text-sky-800"
            }`}
        >
            <Handle
                type="target"
                position={Position.Left}
                className="!bg-slate-400 !w-2 !h-2"
            />
            <div className="text-center">{isAnd ? "AND" : "OR"}</div>
            <Handle
                type="source"
                position={Position.Right}
                className="!bg-slate-400 !w-2 !h-2"
            />
        </div>
    );
}

const nodeTypes = {
    course: CourseNode,
    gate: GateNode,
};

// Color palette for different course departments
const departmentColors: {
    [key: string]: { bg: string; border: string; text: string };
} = {
    ARCH: {
        bg: "linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%)",
        border: "#ec4899",
        text: "#831843",
    },
    BIOL: {
        bg: "linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)",
        border: "#22c55e",
        text: "#14532d",
    },
    CHEM: {
        bg: "linear-gradient(135deg, #fef9c3 0%, #fef08a 100%)",
        border: "#eab308",
        text: "#713f12",
    },
    CS: {
        bg: "linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)",
        border: "#3b82f6",
        text: "#1e3a8a",
    },
    MATH: {
        bg: "linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)",
        border: "#6366f1",
        text: "#312e81",
    },
    PHYS: {
        bg: "linear-gradient(135deg, #fae8ff 0%, #f5d0fe 100%)",
        border: "#a855f7",
        text: "#581c87",
    },
    ACCT: {
        bg: "linear-gradient(135deg, #ccfbf1 0%, #99f6e4 100%)",
        border: "#14b8a6",
        text: "#134e4a",
    },
    FIN: {
        bg: "linear-gradient(135deg, #fed7aa 0%, #fdba74 100%)",
        border: "#f97316",
        text: "#7c2d12",
    },
    MGMT: {
        bg: "linear-gradient(135deg, #fecaca 0%, #fca5a5 100%)",
        border: "#ef4444",
        text: "#7f1d1d",
    },
    default: {
        bg: "linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)",
        border: "#64748b",
        text: "#1e293b",
    },
};

function getDepartmentColor(courseName: string) {
    const dept = courseName.split(" ")[0];
    return departmentColors[dept] || departmentColors.default;
}

interface CourseGraphProps {
    graphData: CourseStructure;
    selectedCourse?: string;
    infoCourse?: string;
    visibleCourses: string[];
    onCourseSelect: (courseName: string) => void;
}

export default function CourseGraph({
    graphData,
    selectedCourse,
    infoCourse,
    visibleCourses,
    onCourseSelect,
}: CourseGraphProps) {
    const elk = useMemo(() => new ELK(), []);
    const [reactFlowInstance, setReactFlowInstance] = React.useState<null | {
        fitView: (options?: any) => void;
    }>(null);
    const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

    const calculateLayout = useCallback(async () => {
        const elkNodes: { id: string; width: number; height: number }[] = [];
        const elkEdges: { id: string; sources: string[]; targets: string[] }[] =
            [];
        const rfNodeMap = new Map<string, Node>();
        const rfEdges: Edge[] = [];
        const edgeSet = new Set<string>();
        const nodeSet = new Set<string>();
        const gateSet = new Set<string>();
        const expandedCourses = new Set<string>();
        let gateCounter = 0;
        let edgeCounter = 0;
        const animateEdges = Boolean(selectedCourse);
        const expandAllPrereqs = Boolean(selectedCourse);

        const ensureCourseNode = (courseName: string, subtitle?: string) => {
            if (!nodeSet.has(courseName)) {
                const colors = getDepartmentColor(courseName);
                rfNodeMap.set(courseName, {
                    id: courseName,
                    type: "course",
                    position: { x: 0, y: 0 },
                    data: {
                        label: courseName,
                        subtitle,
                        background: colors.bg,
                        borderColor: currentTermCourses.has(courseName)
                            ? "#1ac300ff"
                            : "#ff2929",
                        textColor: colors.text,
                        isSelected: courseName === infoCourse,
                    },
                });
                elkNodes.push({ id: courseName, width: 180, height: 90 });
                nodeSet.add(courseName);
            } else if (subtitle && rfNodeMap.has(courseName)) {
                const current = rfNodeMap.get(courseName);
                if (current) {
                    current.data = {
                        ...current.data,
                        subtitle: current.data?.subtitle ?? subtitle,
                        isSelected: courseName === infoCourse,
                    };
                }
            }
        };

        const ensureGateNode = (gateId: string, gateType: "AND" | "OR") => {
            if (!gateSet.has(gateId)) {
                rfNodeMap.set(gateId, {
                    id: gateId,
                    type: "gate",
                    position: { x: 0, y: 0 },
                    data: { gateType },
                });
                elkNodes.push({ id: gateId, width: 90, height: 50 });
                gateSet.add(gateId);
            }
        };

        const addEdge = (
            source: string,
            target: string,
            type: "AND" | "OR",
            offset: number
        ) => {
            const key = `${source}->${target}`;
            if (edgeSet.has(key)) return;
            edgeSet.add(key);
            rfEdges.push({
                id: key,
                source,
                target,
                type: "smoothstep",
                // sourcePosition: Position.Right,
                // targetPosition: Position.Left,
                animated: animateEdges && type === "OR",
                // pathOptions: { offset },
                style: {
                    stroke: type === "AND" ? "#f59e0b" : "#0ea5e9",
                    strokeWidth: 2,
                },
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color: type === "AND" ? "#f59e0b" : "#0ea5e9",
                },
            });
            elkEdges.push({
                id: `e-${edgeCounter++}`,
                sources: [source],
                targets: [target],
            });
        };

        const processPrereq = (
            prereq: Nodes,
            depth: number,
            _parentType: "AND" | "OR",
            siblingIndex: number
        ): string | null => {
            // Handle new COURSE node structure
            if (typeof prereq === "object" && prereq.type === "COURSE") {
                const courseName = prereq.course;
                ensureCourseNode(courseName);

                const courseInfo =
                    expandAllPrereqs && graphData[courseName]
                        ? graphData[courseName]
                        : undefined;

                if (
                    courseInfo &&
                    courseInfo.prereq_tree &&
                    !expandedCourses.has(courseName)
                ) {
                    const coursePrereqs = courseInfo.prereq_tree;
                    expandedCourses.add(courseName);
                    coursePrereqs.children.forEach((child, idx) => {
                        const childId = processPrereq(
                            child,
                            depth + 1,
                            coursePrereqs.type,
                            idx
                        );
                        if (childId) {
                            const offsetSign = idx % 2 === 0 ? 1 : -1;
                            const offsetStep = Math.floor(idx / 2) + 1;
                            const edgeOffset =
                                offsetSign * offsetStep * Math.random() * 16;
                            addEdge(
                                childId,
                                courseName,
                                coursePrereqs.type,
                                edgeOffset
                            );
                        }
                    });
                }

                return courseName;
            }

            // Handle AND/OR nodes
            if (
                typeof prereq === "object" &&
                (prereq.type === "AND" || prereq.type === "OR")
            ) {
                const validChildren: string[] = [];

                prereq.children.forEach((child, idx) => {
                    const childId = processPrereq(
                        child,
                        depth + 1,
                        prereq.type,
                        idx
                    );
                    if (childId) {
                        validChildren.push(childId);
                    }
                });

                // If no valid children (all were filtered out), return null
                if (validChildren.length === 0) {
                    return null;
                }

                // If only one valid child, return it directly without a gate
                if (validChildren.length === 1) {
                    return validChildren[0];
                }

                // Create gate node for multiple valid children
                const gateId = `gate-${gateCounter++}`;
                ensureGateNode(gateId, prereq.type);

                validChildren.forEach((childId, idx) => {
                    const offsetSign = idx % 2 === 0 ? 1 : -1;
                    const offsetStep = Math.floor(idx / 2) + 1;
                    const edgeOffset = offsetSign * offsetStep * 16;
                    addEdge(childId, gateId, prereq.type, edgeOffset);
                });

                return gateId;
            }

            // Skip non-course nodes (PLACEMENT, PERMISSION, STANDING, SKILL)
            // These will be displayed in the future but ignored for now
            return null;
        };

        const coursesToProcess: [string, CourseInfo][] = selectedCourse
            ? [[selectedCourse, graphData[selectedCourse]]]
            : visibleCourses.map((course) => [course, graphData[course]]);

        coursesToProcess.forEach(([courseName, courseInfo]) => {
            const prereqs = courseInfo.prereq_tree;

            if (prereqs) {
                ensureCourseNode(
                    courseName,
                    prereqs.type === "AND" ? "Requires ALL" : "Requires ONE"
                );
                prereqs.children.forEach((child, idx) => {
                    const childId = processPrereq(child, 1, prereqs.type, idx);
                    if (childId) {
                        const offsetSign = idx % 2 === 0 ? 1 : -1;
                        const offsetStep = Math.floor(idx / 2) + 1;
                        const edgeOffset = offsetSign * offsetStep * 20;
                        addEdge(childId, courseName, prereqs.type, edgeOffset);
                    }
                });
            } else {
                ensureCourseNode(courseName, "");
            }
        });

        const elkGraph = {
            id: "root",
            layoutOptions: {
                "elk.algorithm": "layered",
                "elk.direction": "RIGHT",
                "elk.edgeRouting": "ORTHOGONAL",
                "elk.layered.spacing.nodeNodeBetweenLayers": "80",
                "elk.layered.spacing.baseValue": "80",
                "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
                "elk.spacing.nodeNode": "60",
            },
            children: elkNodes,
            edges: elkEdges,
        };

        const layout = await elk.layout(elkGraph);
        const positionMap = new Map<string, { x: number; y: number }>();

        const collect = (n: any) => {
            if (n.id && typeof n.x === "number" && typeof n.y === "number") {
                positionMap.set(n.id, { x: n.x, y: n.y });
            }
            if (Array.isArray(n.children)) {
                n.children.forEach((child: any) => collect(child));
            }
        };

        collect(layout);

        const finalNodes = Array.from(rfNodeMap.values()).map((node) => {
            const pos = positionMap.get(node.id) || { x: 0, y: 0 };
            return { ...node, position: pos };
        });

        return { nodes: finalNodes, edges: rfEdges };
    }, [elk, graphData, selectedCourse, visibleCourses]);

    React.useEffect(() => {
        let cancelled = false;
        (async () => {
            const { nodes: newNodes, edges: newEdges } =
                await calculateLayout();
            if (cancelled) return;

            // Apply the current selection state immediately to the new nodes
            // This prevents a "flash" of unselected state when layout changes
            const nodesWithSelection = newNodes.map((node) => ({
                ...node,
                data: {
                    ...node.data,
                    isSelected: node.id === infoCourse,
                },
            }));

            setNodes(nodesWithSelection);
            setEdges(newEdges);
        })();
        return () => {
            cancelled = true;
        };
    }, [calculateLayout, setNodes, setEdges]); // infoCourse is NOT here

    React.useEffect(() => {
        setNodes((nds) =>
            nds.map((node) => {
                // Optimization: only update if the state actually changes
                const isSelected = node.id === infoCourse;
                if (node.data.isSelected === isSelected) {
                    return node;
                }

                return {
                    ...node,
                    data: {
                        ...node.data,
                        isSelected,
                    },
                };
            })
        );
    }, [infoCourse, setNodes]);

    const handleNodeClick = useCallback(
        (_event: React.MouseEvent, node: Node) => {
            if (node.type === "course") {
                const courseId = String(node.id);
                if (courseId === infoCourse) {
                    onCourseSelect("");
                    return;
                }
                onCourseSelect(String(node.id));
            }
        },
        [onCourseSelect]
    );

    React.useEffect(() => {
        let cancelled = false;
        (async () => {
            const { nodes: newNodes, edges: newEdges } =
                await calculateLayout();
            if (cancelled) return;
            setNodes(newNodes);
            setEdges(newEdges);
            if (newNodes.length > 0 && reactFlowInstance) {
                requestAnimationFrame(() => {
                    reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
                });
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [calculateLayout, reactFlowInstance, setNodes, setEdges]);

    return (
        <div className="w-full h-full bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 rounded-xl overflow-hidden shadow-inner">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={handleNodeClick}
                onInit={setReactFlowInstance}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-left"
                className="bg-transparent"
            >
                <Background color="#94a3b8" gap={20} size={1} />
                <Controls className="bg-white dark:bg-slate-800 rounded-lg shadow-lg" />
                {nodes.length <= 200 && (
                    <MiniMap
                        nodeStrokeColor="#64748b"
                        nodeColor={(n) => {
                            if (n.type === "gate")
                                return n.data?.gateType === "AND"
                                    ? "#fbbf24"
                                    : "#38bdf8";
                            return "#94a3b8";
                        }}
                        className="bg-white dark:bg-slate-800 rounded-lg shadow-lg"
                    />
                )}
            </ReactFlow>
        </div>
    );
}
