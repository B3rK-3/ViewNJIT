"use client";

import { useState, useMemo, useCallback } from "react";
import dynamic from "next/dynamic";
import graphData from "../graph.json";

const MAX_GRAPH_COURSES = 40;

// Dynamic import to avoid SSR issues with React Flow
const CourseGraph = dynamic(() => import("./components/CourseGraph"), {
    ssr: false,
    loading: () => (
        <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
    ),
});

export default function Home() {
    const [selectedCourse, setSelectedCourse] = useState<string>("");
    const [infoCourse, setInfoCourse] = useState<string>("");
    const [searchQuery, setSearchQuery] = useState("");

    const courseList = useMemo(() => Object.keys(graphData).sort(), []);

    const filteredCourses = useMemo(() => {
        if (!searchQuery) return courseList;
        return courseList.filter((course) =>
            course.toLowerCase().includes(searchQuery.toLowerCase())
        );
    }, [courseList, searchQuery]);

    // Get departments for filtering
    const departments = useMemo(() => {
        const depts = new Set<string>();
        courseList.forEach((course) => {
            const dept = course.split(" ")[0];
            depts.add(dept);
        });
        return Array.from(depts).sort();
    }, [courseList]);

    const [selectedDept, setSelectedDept] = useState<string>("");

    const displayedCourses = useMemo(() => {
        let courses = filteredCourses;
        if (selectedDept) {
            courses = courses.filter((course) =>
                course.startsWith(selectedDept + " ")
            );
        }
        return courses;
    }, [filteredCourses, selectedDept]);

    const graphCourses = useMemo(() => {
        if (selectedCourse) return [selectedCourse];
        return displayedCourses.slice(0, MAX_GRAPH_COURSES);
    }, [displayedCourses, selectedCourse]);

    const infoData = useMemo(() => {
        console.log(infoCourse);
        if (!infoCourse) return undefined;
        return (graphData as Record<string, any>)[infoCourse] as
            | Record<string, any>
            | undefined;
    }, [infoCourse]);

    const formatPrereq = useCallback((prereq: any): string => {
        if (!prereq) return "None";
        if (typeof prereq === "string") return prereq;
        if (!Array.isArray(prereq.children) || prereq.children.length === 0) {
            return "None";
        }

        const parts = prereq.children
            .map((child: any) => formatPrereq(child))
            .filter((child: string) => Boolean(child));

        if (parts.length === 0) return "None";
        const joined = parts.join(` ${prereq.type} `);
        return parts.length > 1 ? `(${joined})` : joined;
    }, []);

    const prerequisitesText = useMemo(() => {
        if (!infoCourse || !infoData) return "None";
        return formatPrereq(infoData);
    }, [formatPrereq, infoCourse, infoData]);

    const infoDepartment = infoCourse ? infoCourse.split(" ")[0] : "";
    const infoLink = infoCourse
        ? `https://catalog.njit.edu/search/?search=${encodeURIComponent(
              infoCourse
          )}`
        : "";

    return (
        <div className="flex h-dvh bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-950 dark:via-slate-900 dark:to-indigo-950">
            {/* Sidebar */}
            <aside className="w-80 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-r border-slate-200 dark:border-slate-800 flex flex-col shadow-xl">
                <div className="p-6 border-b border-slate-200 dark:border-slate-800">
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                        ViewNJIT
                    </h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        Visualize classes and prereqs
                    </p>
                </div>

                {/* Search */}
                <div className="p-4 border-b border-slate-200 dark:border-slate-800">
                    <div className="relative">
                        <input
                            type="text"
                            placeholder="Search courses..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full px-4 py-2.5 pl-10 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                        />
                        <svg
                            className="absolute left-3 top-3 h-5 w-5 text-slate-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                            />
                        </svg>
                    </div>
                </div>

                {/* Department Filter */}
                <div className="p-4 border-b border-slate-200 dark:border-slate-800">
                    <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Filter by Department
                    </label>
                    <select
                        value={selectedDept}
                        onChange={(e) => setSelectedDept(e.target.value)}
                        className="mt-2 w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                    >
                        <option value="">All Departments</option>
                        {departments.map((dept) => (
                            <option key={dept} value={dept}>
                                {dept}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Show All Button */}
                <div className="px-4 pt-4">
                    <button
                        onClick={() => {
                            setSelectedCourse("");
                            setInfoCourse("");
                        }}
                        className={`w-full px-4 py-2.5 rounded-xl font-medium transition-all ${
                            selectedCourse === ""
                                ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/25"
                                : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                        }`}
                    >
                        View{" "}
                        {Math.min(displayedCourses.length, MAX_GRAPH_COURSES)}{" "}
                        Results
                    </button>
                </div>

                {/* Course List */}
                <div className="flex-1 overflow-y-auto p-4">
                    <div className="space-y-1">
                        {displayedCourses.slice(0, 100).map((course) => (
                            <button
                                key={course}
                                onClick={() => {
                                    setSelectedCourse(course);
                                    setInfoCourse(course);
                                }}
                                className={`w-full text-left px-4 py-2.5 rounded-lg font-medium transition-all ${
                                    selectedCourse === course
                                        ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md"
                                        : "text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                                }`}
                            >
                                {course}
                            </button>
                        ))}
                        {displayedCourses.length > 100 && (
                            <p className="text-center text-sm text-slate-500 py-2">
                                And {displayedCourses.length - 100} more...
                            </p>
                        )}
                    </div>
                </div>

                {/* Legend */}
                <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
                    <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                        Legend
                    </h3>
                    <div className="space-y-2">
                        <div className="flex items-center gap-2">
                            <div className="w-8 h-0.5 bg-amber-500"></div>
                            <span className="text-sm text-slate-600 dark:text-slate-400">
                                AND connection
                            </span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-8 h-0.5 bg-sky-500 animate-pulse"></div>
                            <span className="text-sm text-slate-600 dark:text-slate-400">
                                OR connection
                            </span>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 flex">
                <div className="flex-1 flex flex-col">
                    {/* Header */}
                    <header className="bg-white/60 dark:bg-slate-900/60 backdrop-blur-xl border-b border-slate-200 dark:border-slate-800 px-6 py-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
                                    {selectedCourse ||
                                        selectedDept +
                                            (selectedDept
                                                ? " Deparment"
                                                : "") ||
                                        "All Courses"}
                                </h2>
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                    {selectedCourse
                                        ? `Viewing prerequisites for ${selectedCourse}`
                                        : displayedCourses.length >
                                          MAX_GRAPH_COURSES
                                        ? `
                                            Showing the first 
                                            ${MAX_GRAPH_COURSES} matches to keep
                                            the graph smooth. Narrow your search
                                            or pick a course to focus.
                                        `
                                        : `Displaying ${Math.min(
                                              displayedCourses.length,
                                              MAX_GRAPH_COURSES
                                          )} courses in graph view`}
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="px-3 py-1 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 text-sm font-medium">
                                    {Object.keys(graphData).length} classes
                                </span>
                            </div>
                        </div>
                    </header>

                    {/* Graph Container */}
                    <div className="flex-1 p-4">
                        <div className="w-full h-full rounded-2xl overflow-hidden shadow-2xl border border-slate-200 dark:border-slate-800">
                            <CourseGraph
                                graphData={graphData as GraphData}
                                selectedCourse={selectedCourse || undefined}
                                infoCourse={infoCourse}
                                visibleCourses={graphCourses}
                                onCourseSelect={(course) => {
                                    // setSelectedCourse(course);
                                    setInfoCourse(course);
                                }}
                            />
                        </div>
                    </div>
                </div>

                {/* Course Sidebar */}
                <aside className="w-80 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-100 dark:border-slate-700 shadow-xl absolute rounded-md shadow-xl ml-7 top-28">
                    <div className="p-2 pl-6 border-b border-slate-200 dark:border-slate-800">
                        {infoCourse ? (
                            <>
                                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                                    {infoCourse}
                                </h3>
                            </>
                        ) : (
                            <div className="text-sm text-slate-500 dark:text-slate-400 mt-2">
                                Select a course to see details
                            </div>
                        )}
                    </div>

                    <div className="p-6 pt-2 space-y-4">
                        <div className="text-sm text-slate-700 dark:text-slate-300">
                            <span className="font-semibold text-slate-600 dark:text-slate-400">
                                Description:
                            </span>{" "}
                            {infoCourse && (infoData as any)?.desc
                                ? (infoData as any).desc
                                : "no description"}
                        </div>
                        <div className="text-sm text-slate-700 dark:text-slate-300">
                            <span className="font-semibold text-slate-600 dark:text-slate-400">
                                Link:
                            </span>{" "}
                            {infoCourse ? (
                                <a
                                    href={infoLink}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-indigo-600 dark:text-indigo-400 hover:underline"
                                >
                                    {infoCourse} -&gt;
                                </a>
                            ) : (
                                "no link"
                            )}
                        </div>
                        <div className="text-sm text-slate-700 dark:text-slate-300">
                            <span className="font-semibold text-slate-600 dark:text-slate-400">
                                Prerequisites:
                            </span>{" "}
                            {infoCourse ? prerequisitesText : "None"}
                        </div>
                    </div>
                </aside>
            </main>
        </div>
    );
}
