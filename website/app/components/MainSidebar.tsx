"use client";

import React from "react";
import { semesters, setCurrentTerm, terms } from "../constants";
import { Grandstander } from "next/font/google";
const TitleFont = Grandstander({
    weight: "600",
    subsets: ["latin"],
    variable: "--font-kaushan",
});
const MAX_GRAPH_COURSES = 40;

interface MainSidebarProps {
    searchQuery: string;
    setSearchQuery: (query: string) => void;
    selectedDept: string;
    setSelectedDept: (dept: string) => void;
    departments: string[];
    displayedCourses: string[];
    selectedCourse: string;
    setSelectedCourse: (course: string) => void;
    setCurrentCourse: (course: string) => void;
    currentTerm: string;
    onTermChange: (term: string) => void;
    displayOnlyTermCourses: boolean;
    setDisplayOnlyTermCourses: (checked: boolean) => void;
}

export default function MainSidebar({
    searchQuery,
    setSearchQuery,
    selectedDept,
    setSelectedDept,
    departments,
    displayedCourses,
    selectedCourse,
    setSelectedCourse,
    setCurrentCourse,
    currentTerm,
    onTermChange,
    displayOnlyTermCourses,
    setDisplayOnlyTermCourses,
}: MainSidebarProps) {
    const getTermLabel = (term: string) => {
        const semesterCode = term.slice(-2);
        const year = term.slice(0, -2);
        const semesterName = semesters[semesterCode as keyof typeof semesters];

        return semesterName ? `${year} ${semesterName}` : term;
    };

    return (
        <aside
            className={`w-80 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-r border-slate-200 dark:border-slate-800 flex flex-col shadow-xl `}
        >
            <div className="p-6 border-b border-slate-200 dark:border-slate-800">
                <h1
                    className={`text-3xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent ${TitleFont.className}
            `}
                >
                    FlowNJIT
                </h1>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                    Visualize courses and prereqs
                </p>
            </div>

            {/* Search */}
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-col gap-y-2">
                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Search Course Name
                </label>
                <div className="relative">
                    <input
                        type="text"
                        placeholder="Search courses..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full px-4 py-2 pl-10 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
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

                <div>
                    <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Filter by Department
                    </label>
                    <div className="relative mt-1">
                        <select
                            value={selectedDept}
                            onChange={(e) => setSelectedDept(e.target.value)}
                            className="w-full px-3 py-2 pr-8 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                        >
                            <option value="">All Departments</option>
                            {departments.map((dept) => (
                                <option key={dept} value={dept}>
                                    {dept}
                                </option>
                            ))}
                        </select>
                        {selectedDept && (
                            <button
                                onClick={() => setSelectedDept("")}
                                className="absolute right-5 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg leading-none cursor-pointer"
                            >
                                ×
                            </button>
                        )}
                    </div>
                </div>

                {/* Term Selector */}
                <div>
                    <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Term
                    </label>
                    <select
                        value={currentTerm}
                        onChange={(e) => {
                            const nextTerm = e.target.value;
                            setCurrentTerm(nextTerm);
                            onTermChange(nextTerm);
                        }}
                        className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                    >
                        {terms.map((term) => (
                            <option key={term} value={term}>
                                {getTermLabel(term)}
                            </option>
                        ))}
                    </select>
                </div>

                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 mt-1">
                    <input
                        type="checkbox"
                        checked={displayOnlyTermCourses}
                        onChange={(e) =>
                            setDisplayOnlyTermCourses(e.target.checked)
                        }
                        className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    Display only selected term courses
                </label>

                <button
                    onClick={() => {
                        setSelectedCourse("");
                        setCurrentCourse("");
                    }}
                    className={`mt-3 w-full px-4 py-2.5 rounded-xl font-medium transition-all ${
                        selectedCourse === ""
                            ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/25"
                            : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                    }`}
                >
                    View {Math.min(displayedCourses.length, MAX_GRAPH_COURSES)}{" "}
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
                                setCurrentCourse(course);
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
            <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
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
                    <div className="flex items-center gap-2">
                        <div
                            className="w-8 h-4 border-2 rounded-sm bg-white dark:bg-slate-900"
                            style={{ borderColor: "#1ac300ff" }}
                        ></div>
                        <span className="text-sm text-slate-600 dark:text-slate-400">
                            Offered with selected term
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div
                            className="w-8 h-4 border-2 rounded-sm bg-white dark:bg-slate-900"
                            style={{ borderColor: "#ff2929" }}
                        ></div>
                        <span className="text-sm text-slate-600 dark:text-slate-400">
                            Not offered with selected term
                        </span>
                    </div>
                </div>
            </div>
        </aside>
    );
}
