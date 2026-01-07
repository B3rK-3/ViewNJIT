"use client";

import React, { useState, useEffect, useRef } from "react";
import { MessageCircle, X, Send, Calendar } from "lucide-react";
import ScheduleViewer from "./ScheduleViewer";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { currentTerm, getSessionUUID, baseURL } from "../constants";

export default function ChatPopup({
    setSearchQuery,
    maxWidth,
    maxHeight,
}: {
    setSearchQuery: (query: string) => void;
    maxWidth?: number;
    maxHeight?: number;
}) {
    const chatURL = baseURL + "/chat";
    const sessionUUIDPromise = getSessionUUID();
    const errorMessage = "Something went wrong! Try again later!";
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<
        { id: number; text: string; sender: "user" | "bot" }[]
    >([
        {
            id: 1,
            text: "Hello! How can I help you?",
            sender: "bot",
        },
    ]);
    const [inputValue, setInputValue] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [schedules, setSchedules] = useState<any[]>([]);
    const [isViewerOpen, setIsViewerOpen] = useState(false);
    const [width, setWidth] = useState(350);
    const [height, setHeight] = useState(485);
    const [isResizing, setIsResizing] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const currentScheduleIndex = useRef(0);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading, isOpen]);

    // Ensure chat doesn't exceed graph dimensions if they shrink
    useEffect(() => {
        if (maxWidth && width > maxWidth) {
            setWidth(Math.max(350, maxWidth));
        }
        if (maxHeight && height > maxHeight) {
            setHeight(Math.max(485, maxHeight));
        }
    }, [maxWidth, maxHeight]);

    // Resize logic
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isResizing) return;

            // Since it's bottom-right anchored:
            // New Width = Current width + (initialX - mouseX)
            // But we can simplify: we know the right edge is screenWidth - 24px (right-6)
            // Wait, the popup is 'absolute bottom-20 right-0' relative to the 'fixed bottom-6 right-6' wrapper.
            // So the right edge is fixed at WindowWidth - 24px.
            // Width = RightEdge - MouseX
            // Height = BottomEdge - MouseY

            const newWidth = Math.max(
                350,
                Math.min(
                    maxWidth || Infinity,
                    window.innerWidth - 24 - e.clientX
                )
            );
            const newHeight = Math.max(
                485,
                Math.min(
                    maxHeight || Infinity,
                    window.innerHeight - 24 - 80 - e.clientY
                )
            );

            setWidth(newWidth);
            setHeight(newHeight);
        };

        const handleMouseUp = () => {
            setIsResizing(false);
        };

        if (isResizing) {
            window.addEventListener("mousemove", handleMouseMove);
            window.addEventListener("mouseup", handleMouseUp);
        }

        return () => {
            window.removeEventListener("mousemove", handleMouseMove);
            window.removeEventListener("mouseup", handleMouseUp);
        };
    }, [isResizing]);

    const handleDeleteSchedule = (index: number) => {
        const newSchedules = [...schedules];
        newSchedules.splice(index, 1);
        setSchedules(newSchedules);
    };

    const handleSendMessage = () => {
        if (inputValue.trim()) {
            const newMessage = {
                id: Date.now(),
                text: inputValue,
                sender: "user" as const,
            };
            setMessages([...messages, newMessage]);
            setIsLoading(true);

            // Reset current request index for overwriting logic
            currentScheduleIndex.current = 0;

            sessionUUIDPromise.then((sessionUUID) => {
                fetch(chatURL, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        sessionID: sessionUUID,
                        term: currentTerm,
                        query: inputValue,
                    }),
                })
                    .then(async (response) => {
                        if (!response.ok || !response.body) {
                            throw new Error(errorMessage);
                        }

                        const reader = response.body.getReader();
                        const decoder = new TextDecoder();

                        // Add initial empty bot message
                        const botMsgId = Date.now();
                        let currentText = "";

                        setMessages((prev) => [
                            ...prev,
                            {
                                id: botMsgId,
                                text: "",
                                sender: "bot",
                            },
                        ]);

                        while (true) {
                            const { done, value } = await reader.read();
                            if (done) break;

                            const chunk = decoder.decode(value, {
                                stream: true,
                            });
                            const lines = chunk.split("\n");

                            for (const line of lines) {
                                if (!line.trim()) continue;
                                try {
                                    const data = JSON.parse(line);
                                    if (data.type === "text") {
                                        currentText += data.content;
                                    } else if (data.type === "schedule") {
                                        const s = data.content;
                                        const idx =
                                            currentScheduleIndex.current;

                                        // Update global schedules state with overwrite logic
                                        setSchedules((prev) => {
                                            const newScheds = [...prev];
                                            if (idx < newScheds.length) {
                                                newScheds[idx] = s;
                                            } else {
                                                newScheds.push(s);
                                            }
                                            return newScheds;
                                        });

                                        currentScheduleIndex.current += 1;
                                    }

                                    setMessages((prev) => {
                                        const newMsgs = [...prev];
                                        const lastMsg =
                                            newMsgs[newMsgs.length - 1];
                                        if (lastMsg.id === botMsgId) {
                                            lastMsg.text = currentText;
                                        }
                                        return newMsgs;
                                    });
                                } catch (e) {
                                    console.error("JSON Parse error", e);
                                }
                            }
                        }
                        setIsLoading(false);
                    })
                    .catch((e) => {
                        setMessages((prevMessages) => [
                            ...prevMessages,
                            {
                                id: Date.now(),
                                text: errorMessage,
                                sender: "bot",
                            },
                        ]);
                        setIsLoading(false);
                    });
            });

            setInputValue("");
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    return (
        <div className="fixed bottom-6 right-6 z-50">
            {/* Schedule Viewer */}
            <ScheduleViewer
                schedules={schedules}
                isOpen={isViewerOpen}
                onClose={() => setIsViewerOpen(false)}
                onDelete={handleDeleteSchedule}
                setSearchQuery={setSearchQuery}
            />

            {/* Chat Window */}
            <div
                style={{
                    width: isOpen ? width : 0,
                    height: isOpen ? height : 0,
                }}
                className={`absolute bottom-20 right-0 bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col ease-out origin-bottom-right ${
                    isOpen
                        ? "opacity-100 scale-100 pointer-events-auto"
                        : "opacity-0 scale-95 pointer-events-none"
                } ${
                    isResizing
                        ? ""
                        : "transition-[width,height,opacity,scale] duration-300"
                }`}
            >
                {/* Resize Handle - Top Left */}
                <div
                    onMouseDown={() => setIsResizing(true)}
                    className="absolute top-0 left-0 w-4 h-4 cursor-nwse-resize z-[60] hover:bg-indigo-500/10 transition-colors group"
                >
                    <div className="absolute top-1 left-1 w-2 h-2 border-t-2 border-l-2 border-slate-300 dark:border-slate-600 group-hover:border-indigo-500 transition-colors" />
                </div>

                {/* Header */}
                <div className="bg-gradient-to-r from-indigo-600 to-indigo-700 px-4 py-3 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-2">
                        <MessageCircle className="w-5 h-5 text-white" />
                        <h3 className="font-semibold text-white">Course AI</h3>
                    </div>
                    <button
                        onClick={() => setIsOpen(false)}
                        className="text-white hover:bg-indigo-800 p-1 rounded-lg transition-colors cursor-pointer"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Messages Container */}
                <div className="flex-1 overflow-y-auto flex flex-col gap-3 p-4 bg-slate-50 dark:bg-slate-800 relative">
                    <style>{`
                        @keyframes typing {
                            0%, 60%, 100% { opacity: 0.5; }
                            30% { opacity: 1; }
                        }
                        .typing-dot {
                            animation: typing 1.4s infinite;
                        }
                        .typing-dot:nth-child(2) {
                            animation-delay: 0.2s;
                        }
                        .typing-dot:nth-child(3) {
                            animation-delay: 0.4s;
                        }
                        .markdown-content p {
                            margin-bottom: 0.5rem;
                        }
                        .markdown-content p:last-child {
                            margin-bottom: 0;
                        }
                        .markdown-content ul, .markdown-content ol {
                            margin-bottom: 0.5rem;
                            padding-left: 1.25rem;
                        }
                        .markdown-content li {
                            margin-bottom: 0.25rem;
                        }
                        .markdown-content a {
                            color: #4f46e5;
                            text-decoration: underline;
                        }
                        .dark .markdown-content a {
                            color: #818cf8;
                        }
                        .markdown-content code {
                            background-color: #f1f5f9;
                            padding: 0.125rem 0.25rem;
                            border-radius: 0.25rem;
                            font-size: 0.8rem;
                        }
                        .dark .markdown-content code {
                            background-color: #334155;
                        }
                    `}</style>
                    {messages.map((message) => (
                        <div
                            key={message.id}
                            className={`flex ${
                                message.sender === "user"
                                    ? "justify-end"
                                    : "justify-start"
                            }`}
                        >
                            <div
                                className={`max-w-[70%] px-4 py-2 rounded-lg ${
                                    message.sender === "user"
                                        ? "bg-indigo-600 text-white rounded-br-none"
                                        : "bg-white dark:bg-slate-700 text-slate-900 dark:text-white rounded-bl-none border border-slate-200 dark:border-slate-600"
                                }`}
                            >
                                {message.sender === "user" ? (
                                    <p className="text-sm whitespace-pre-wrap break-words">
                                        {message.text
                                            .replace(/\\n/g, "\n")
                                            .replace(/\\t/g, "\t")}
                                    </p>
                                ) : (
                                    <div className="text-sm markdown-content break-words">
                                        <ReactMarkdown
                                            remarkPlugins={[
                                                remarkGfm,
                                                remarkBreaks,
                                            ]}
                                        >
                                            {message.text
                                                .replace(/\\n/g, "\n")
                                                .replace(/\\t/g, "\t")}
                                        </ReactMarkdown>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="flex justify-start">
                            <div className="bg-white dark:bg-slate-700 text-slate-900 dark:text-white rounded-bl-none border border-slate-200 dark:border-slate-600 px-4 py-2 rounded-lg flex gap-1 items-center">
                                <span className="typing-dot inline-block w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-500"></span>
                                <span className="typing-dot inline-block w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-500"></span>
                                <span className="typing-dot inline-block w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-500"></span>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* View Button */}
                {schedules.length > 0 && (
                    <div className="absolute bottom-[52px] left-0 w-full px-4 py-2 bg-gradient-to-t from-white to-transparent dark:from-slate-900 z-10 flex justify-center">
                        <button
                            onClick={() => setIsViewerOpen(true)}
                            className="bg-emerald-500 hover:bg-emerald-600 text-white text-xs px-3 py-1 rounded-full shadow-md transition-all hover:scale-105 active:scale-95 flex items-center gap-1 "
                        >
                            <Calendar className="w-3 h-3" />
                            View Schedules ({schedules.length})
                        </button>
                    </div>
                )}

                {/* Input Area */}
                <div className="border-t border-slate-200 dark:border-slate-700 p-3 bg-white dark:bg-slate-900 flex gap-2 shrink-0">
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Ask something..."
                        className="flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                    />
                    <button
                        onClick={handleSendMessage}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white p-2 rounded-lg transition-colors"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </div>
            </div>

            {/* Toggle Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-14 h-14 rounded-full bg-gradient-to-br from-indigo-600 to-indigo-700 text-white shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center hover:scale-110 active:scale-95 cursor-pointer"
            >
                {isOpen ? (
                    <X className="w-6 h-6" />
                ) : (
                    <MessageCircle className="w-6 h-6" />
                )}
            </button>
        </div>
    );
}
