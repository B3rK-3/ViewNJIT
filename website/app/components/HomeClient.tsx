"use client";

import React, { useState, useMemo, useCallback, useEffect, JSX } from "react";
import dynamic from "next/dynamic";

import {
    CourseStructure,
    currentTermCourses,
    startTerm,
    generateNonBlueColor,
    generateRandomRGB,
    getRandomInt,
    Nodes,
} from "../constants";
import { Span } from "next/dist/trace";
import MainSidebar from "./MainSidebar";
import CourseSidebar from "./CourseSidebar";
import ChatPopup from "./ChatPopup";
import { graphData } from "../constants";

const MAX_GRAPH_COURSES = 40;


// Dynamic import to avoid SSR issues with React Flow
const CourseGraph = dynamic(() => import("./CourseGraph"), {
    ssr: false,
    loading: () => (
        <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
    ),
});

interface HomeClientProps {
    initialSelectedDept?: string;
    initialSelectedCourse?: string;
    initialSearchQuery?: string;
    initialInfoCourse?: string;
}

export default function HomeClient({
    initialSelectedDept,
    initialSelectedCourse,
    initialSearchQuery,
    initialInfoCourse,
}: HomeClientProps) {
    const [selectedCourse, setSelectedCourse] = useState<string>(
        initialSelectedCourse ?? ""
    );
    const [currentCourse, setCurrentCourse] = useState<string>(
        initialInfoCourse ?? initialSelectedCourse ?? ""
    );
    const [searchQuery, setSearchQuery] = useState(initialSearchQuery ?? "");
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [selectedTerm, setSelectedTerm] = useState(startTerm);
    const [displayOnlyTermCourses, setDisplayOnlyTermCourses] =
        useState(false);
   

    useEffect(() => {
        setSelectedCourse(initialSelectedCourse ?? "");
        setCurrentCourse(initialInfoCourse ?? initialSelectedCourse ?? "");
        setSearchQuery(initialSearchQuery ?? "");
    }, [initialInfoCourse, initialSearchQuery, initialSelectedCourse]);

    

    const courseList = useMemo(() => {
        if (displayOnlyTermCourses) {
            return [...currentTermCourses].sort();
        }
        return Object.keys(graphData).sort();
    }, [displayOnlyTermCourses, selectedTerm]);

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

    const [selectedDept, setSelectedDept] = useState<string>(
        initialSelectedDept ?? ""
    );

    useEffect(() => {
        setSelectedDept(initialSelectedDept ?? "");
    }, [initialSelectedDept]);

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
        if (!currentCourse) return undefined;
        return graphData[currentCourse];
    }, [currentCourse]);

    const getPrereqText = useCallback((prereq: Nodes | null): JSX.Element => {
        if (!prereq) return <>None</>;
        if (prereq.type == "COURSE") return <span>{prereq.course}</span>;
        if (prereq.type == "PERMISSION") return <span>{prereq.raw}</span>;
        if (prereq.type == "PLACEMENT") return <span>{prereq.name}</span>;
        if (prereq.type == "SKILL") return <span>{prereq.name}</span>;
        if (prereq.type == "STANDING") return <span>{prereq.standing}</span>;
        if (!Array.isArray(prereq.children) || prereq.children.length === 0) {
            return <></>;
        }

        const color = generateNonBlueColor();

        const parts = prereq.children.map((child: any) => getPrereqText(child));

        if (parts.length === 0) return <></>;
        return (
            <>
                <br></br>
                <span style={{ color: color, fontWeight: 700 }}>(</span>
                <span>{parts[0]}</span>
                {parts.slice(1).map((el) => {
                    if (React.Children.count(el) > 0) {
                        return (
                            <span key={getRandomInt(0, 9007199254740990)}>
                                {" "}
                                <strong>{prereq.type}</strong> <span>{el}</span>
                            </span>
                        );
                    }
                })}
                <span style={{ color: color, fontWeight: 700 }}>)</span>
                <br></br>
            </>
        );
    }, []);

    const prerequisitesText = useMemo(() => {
        if (!infoData) return <>None</>;
        return getPrereqText(infoData.prereq_tree);
    }, [getPrereqText, currentCourse, infoData]);

    const infoLink = currentCourse
        ? `https://catalog.njit.edu/search/?search=${encodeURIComponent(
              currentCourse
          )}`
        : "";

    return (
        <div className="flex h-dvh bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-950 dark:via-slate-900 dark:to-indigo-950">
            <MainSidebar
                searchQuery={searchQuery}
                setSearchQuery={setSearchQuery}
                selectedDept={selectedDept}
                setSelectedDept={setSelectedDept}
                departments={departments}
                displayedCourses={displayedCourses}
                selectedCourse={selectedCourse}
                setSelectedCourse={setSelectedCourse}
                setCurrentCourse={setCurrentCourse}
                currentTerm={selectedTerm}
                onTermChange={setSelectedTerm}
                displayOnlyTermCourses={displayOnlyTermCourses}
                setDisplayOnlyTermCourses={setDisplayOnlyTermCourses}
            />

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
                                    {Object.keys(graphData).length} courses
                                </span>
                            </div>
                        </div>
                    </header>

                    {/* Graph Container */}
                    <div className="flex-1 p-4">
                        <div className="w-full h-full rounded-2xl overflow-hidden shadow-2xl border border-slate-200 dark:border-slate-800">
                            <CourseGraph
                                graphData={graphData}
                                selectedCourse={selectedCourse || undefined}
                                infoCourse={currentCourse}
                                visibleCourses={graphCourses}
                                onCourseSelect={(course) => {
                                    // setSelectedCourse(course);
                                    setCurrentCourse(course);
                                }}
                            />
                        </div>
                    </div>
                </div>

                <CourseSidebar
                    currentCourse={currentCourse}
                    infoData={infoData}
                    isSidebarOpen={isSidebarOpen}
                    setIsSidebarOpen={setIsSidebarOpen}
                    prerequisitesText={prerequisitesText}
                    infoLink={infoLink}
                    currentTerm={selectedTerm}
                />
            </main>

            {/* Chat Popup */}
            <ChatPopup />
        </div>
    );
}
