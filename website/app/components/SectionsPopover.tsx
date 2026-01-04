"use client";

import React, { useState, useRef, useEffect, useMemo } from "react";
import { graphData, sectionsData } from "../constants";

interface SectionsPopoverProps {
    courseName: string;
    profLinks: Record<string, { link: string; avgRating?: string }>;
    currentTerm: string;
}

interface SectionData {
    section: string;
    code: string;
    days: string;
    time: string;
    room: string;
    status: string;
    capacity: string;
    enrolled: string;
    instructor: string;
    format: string;
    credits: string;
    book: string;
    notes: string;
}

export default function SectionsPopover({
    courseName,
    profLinks,
    currentTerm,
}: SectionsPopoverProps) {
    const [isOpen, setIsOpen] = useState(false);

    const popoverRef = useRef<HTMLDivElement>(null);
    const buttonRef = useRef<HTMLButtonElement>(null);

    // Close popover when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (
                popoverRef.current &&
                !popoverRef.current.contains(event.target as Node) &&
                buttonRef.current &&
                !buttonRef.current.contains(event.target as Node)
            ) {
                setIsOpen(false);
            }
        }

        if (isOpen) {
            document.addEventListener("mousedown", handleClickOutside);
            return () => {
                document.removeEventListener("mousedown", handleClickOutside);
            };
        }
    }, [isOpen]);

    const courseSectionData = useMemo(() => {
        return sectionsData[courseName];
    }, [courseName, currentTerm]);

    const courseTitle = useMemo(() => {
        return graphData[courseName]?.title || "Unknown Course";
    }, [courseName]);

    const sections: SectionData[] = useMemo(() => {
        if (!courseSectionData) return [];
        return Object.values(courseSectionData).map((sectionArray) => ({
            section: sectionArray[0],
            code: sectionArray[1],
            days: sectionArray[2],
            time: sectionArray[3],
            room: sectionArray[4],
            status: sectionArray[5],
            capacity: sectionArray[6],
            enrolled: sectionArray[7],
            instructor: sectionArray[8],
            format: sectionArray[9],
            credits: sectionArray[10],
            book: sectionArray[11],
            notes: sectionArray[12],
        }));
    }, [courseSectionData]);

    if (!courseSectionData) {
        return (
            <div className="relative">
                <button
                    disabled
                    className="p-1 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed"
                    title="No sections available"
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-5 w-5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                    </svg>
                </button>
            </div>
        );
    }

    const getProfessorElement = (profName: string) => {
        const profData = profLinks[profName];
        const notFoundUrl =
            "https://www.ratemyprofessors.com/teacher-not-found";

        if (!profData || profData.link === notFoundUrl) {
            return (
                <span className="flex items-center gap-1 inline-flex">
                    {profName}
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-4 w-4 text-red-500"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                    >
                        <title>Professor not found in RateMyProfessors</title>
                        <path
                            fillRule="evenodd"
                            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                            clipRule="evenodd"
                        />
                    </svg>
                </span>
            );
        }

        const displayName =
            profData.avgRating && profData.avgRating !== "0"
                ? `${profName} (${profData.avgRating})`
                : profName;

        return (
            <a
                href={profData.link}
                target="_blank"
                rel="noreferrer"
                className="text-indigo-600 dark:text-indigo-400 hover:underline"
            >
                {displayName}
            </a>
        );
    };

    return (
        <div className="relative ">
            <button
                ref={buttonRef}
                onClick={() => setIsOpen(!isOpen)}
                className="p-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
                title="View sections"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-5 w-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                </svg>
            </button>

            {isOpen && (
                <div
                    ref={popoverRef}
                    className="absolute left-0 mt-2 w-[800px] max-h-[600px] bg-white dark:bg-slate-800 rounded-lg shadow-2xl border border-slate-200 dark:border-slate-700 z-50 overflow-hidden animate-rollout"
                >
                    <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
                        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                            {courseName}
                        </h3>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                            {courseTitle}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-500 mt-1">
                            {sections.length} section
                            {sections.length !== 1 ? "s" : ""} available
                        </p>
                    </div>

                    <div className="overflow-auto max-h-[500px]">
                        <table className="w-full text-sm text-center">
                            <thead className="bg-slate-100 dark:bg-slate-900 sticky top-0">
                                <tr>
                                    <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-300">
                                        Section
                                    </th>
                                    <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-300">
                                        CRN
                                    </th>
                                    <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-300">
                                        Days
                                    </th>
                                    <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-300">
                                        Time
                                    </th>
                                    <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-300">
                                        Room
                                    </th>
                                    <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-300">
                                        Status
                                    </th>
                                    <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-300">
                                        Enrolled
                                    </th>
                                    <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-300">
                                        Instructor
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                                {sections.map((section, idx) => (
                                    <tr
                                        key={idx}
                                        className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                                    >
                                        <td className="px-3 py-2 text-slate-900 dark:text-white font-medium">
                                            {section.section}
                                        </td>
                                        <td className="px-3 py-2 text-slate-600 dark:text-slate-400">
                                            {section.code}
                                        </td>
                                        <td className="px-3 py-2 text-slate-600 dark:text-slate-400">
                                            {section.days}
                                        </td>
                                        <td className="px-3 py-2 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                                            {section.time.split(", ")[0]}
                                            {section.time
                                                .split(", ")
                                                .splice(1)
                                                .map((el, idx) => {
                                                    return (
                                                        <span key={idx}>
                                                            <br></br>
                                                            {el}
                                                        </span>
                                                    );
                                                })}
                                        </td>
                                        <td className="px-3 py-2 text-slate-600 dark:text-slate-400">
                                            {section.room.split(", ")[0]}
                                            {section.room
                                                .split(", ")
                                                .splice(1)
                                                .map((el, idx) => {
                                                    return (
                                                        <span key={idx}>
                                                            <br></br>
                                                            {el}
                                                        </span>
                                                    );
                                                })}
                                        </td>
                                        <td className="px-3 py-2">
                                            <span
                                                className={`px-2 py-1 rounded-full text-xs font-medium ${
                                                    section.status === "Open"
                                                        ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                                                        : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                                                }`}
                                            >
                                                {section.status}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2 text-slate-600 dark:text-slate-400">
                                            {section.enrolled}/
                                            {section.capacity}
                                        </td>
                                        <td className="px-3 py-2 text-slate-600 dark:text-slate-400">
                                            {getProfessorElement(
                                                section.instructor
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
