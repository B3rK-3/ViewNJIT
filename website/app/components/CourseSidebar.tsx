"use client";

import React, { JSX, useEffect, useState } from "react";
import SectionsPopover from "./SectionsPopover";
import { sectionsData } from "../constants";

interface CourseSidebarProps {
    currentCourse: string;
    infoData?: {
        title: string;
        desc: string;
        prereq_tree: any;
    };
    isSidebarOpen: boolean;
    setIsSidebarOpen: (open: boolean) => void;
    prerequisitesText: JSX.Element;
    infoLink: string;
    currentTerm: string;
}

export default function CourseSidebar({
    currentCourse,
    infoData,
    isSidebarOpen,
    setIsSidebarOpen,
    prerequisitesText,
    infoLink,
    currentTerm,
}: CourseSidebarProps) {
    const [profLinks, setProfLinks] = useState<Record<string, string>>({});
    // Fetch professor links when popover opens
    useEffect(() => {
        const fetchProfessorLinks = async () => {
            if (!currentCourse || !sectionsData[currentCourse]) return;

            const courseData = sectionsData[currentCourse];
            const instructors = Array.from(
                new Set(Object.values(courseData).map((section) => section[8]))
            );

            // Map each instructor to a promise
            const fetchPromises = instructors.map(async (instructor) => {
                const [profLastName, profFirstName] = instructor.split(", ");
                const url = `https://backend-server-black-phi.vercel.app/prof?q=${profFirstName} ${profLastName}&getData=false`;
                const fallback =
                    "https://www.ratemyprofessors.com/teacher-not-found";

                try {
                    const response = await fetch(url);
                    if (!response.ok || response.status === 204) {
                        return { instructor, link: fallback };
                    }
                    const data = await response.json();
                    return { instructor, link: data.link || fallback };
                } catch (error) {
                    console.error(`Error fetching ${instructor}:`, error);
                    return { instructor, link: fallback };
                }
            });

            const results = await Promise.all(fetchPromises);

            const newLinks: Record<string, string> = {};
            results.forEach((res) => {
                newLinks[res.instructor] = res.link;
            });

            setProfLinks((prev) => ({ ...prev, ...newLinks }));
        };

        fetchProfessorLinks();
    }, [currentCourse, currentTerm]);
    return (
        <aside className="w-80 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-100 dark:border-slate-700 shadow-xl absolute rounded-md shadow-xl ml-7 top-28">
            <div className="p-2 pl-6 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center">
                {currentCourse && infoData ? (
                    <>
                        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                            {currentCourse}
                        </h3>
                    </>
                ) : (
                    <div className="text-sm text-slate-500 dark:text-slate-400 mt-2">
                        Select a course to see details
                    </div>
                )}
                <div className="flex items-center gap-1">
                    {currentCourse && (
                        <SectionsPopover
                            courseName={currentCourse}
                            profLinks={profLinks}
                            currentTerm={currentTerm}
                        />
                    )}
                    <button
                        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                        className="p-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className={`h-5 w-5 text-slate-500 transition-transform ${
                                isSidebarOpen ? "rotate-180" : ""
                            }`}
                            viewBox="0 0 20 20"
                            fill="currentColor"
                        >
                            <path
                                fillRule="evenodd"
                                d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                                clipRule="evenodd"
                            />
                        </svg>
                    </button>
                </div>
            </div>

            <div
                className={`transition-all duration-300 ease-in-out overflow-y-scroll ${
                    isSidebarOpen ? "max-h-96" : "overflow-hidden max-h-0"
                }`}
            >
                <div className="p-6 pt-2 space-y-4">
                    <div className="text-sm text-slate-700 dark:text-slate-300">
                        <span className="font-semibold text-slate-600 dark:text-slate-400">
                            Name:
                        </span>{" "}
                        {infoData && infoData.title}
                    </div>
                    <div className="text-sm text-slate-700 dark:text-slate-300">
                        <span className="font-semibold text-slate-600 dark:text-slate-400">
                            Description:
                        </span>{" "}
                        {infoData && infoData.desc}
                    </div>
                    <div className="text-sm text-slate-700 dark:text-slate-300">
                        <span className="font-semibold text-slate-600 dark:text-slate-400">
                            Link:
                        </span>{" "}
                        {currentCourse ? (
                            <a
                                href={infoLink}
                                target="_blank"
                                rel="noreferrer"
                                className="text-indigo-600 dark:text-indigo-400 hover:underline"
                            >
                                {currentCourse} -&gt;
                            </a>
                        ) : (
                            ""
                        )}
                    </div>
                    <div className="text-sm text-slate-700 dark:text-slate-300">
                        <span className="font-semibold text-slate-600 dark:text-slate-400">
                            Prerequisites:
                        </span>{" "}
                        {currentCourse ? prerequisitesText : ""}
                    </div>
                </div>
            </div>
        </aside>
    );
}
