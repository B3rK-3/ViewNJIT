// Types for the graph structure
type PrereqChild = string | PrereqGroup;

interface PrereqGroup {
    type: "AND" | "OR";
    children: PrereqChild[];
    min_grade?: string;
}

interface GraphData {
    [courseName: string]: PrereqGroup | undefined;
}