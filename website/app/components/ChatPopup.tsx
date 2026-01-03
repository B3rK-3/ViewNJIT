"use client";

import React, { useState, useEffect, useRef } from "react";
import { MessageCircle, X, Send } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { currentTerm, getSessionUUID } from "../constants";

export default function ChatPopup() {
    const chatURL =
        process.env.NODE_ENV === "development"
            ? "http://localhost:3001/chat"
            : "https://flownjit.com/chat";
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
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading, isOpen]);

    const handleSendMessage = () => {
        if (inputValue.trim()) {
            const newMessage = {
                id: Date.now(),
                text: inputValue,
                sender: "user" as const,
            };
            setMessages([...messages, newMessage]);
            setIsLoading(true);

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
                    .then((response) => {
                        if (response.ok) {
                            return response.json();
                        } else {
                            return errorMessage;
                        }
                    })
                    .then((aiResponse) => {
                        setMessages((prevMessages) => [
                            ...prevMessages,
                            {
                                id: Date.now(),
                                text: aiResponse.response,
                                sender: "bot",
                            },
                        ]);
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
            {/* Chat Window */}
            <div
                className={`absolute bottom-20 right-0 w-80 bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden transition-all duration-300 ease-out origin-bottom-right ${
                    isOpen
                        ? "opacity-100 scale-100 pointer-events-auto"
                        : "opacity-0 scale-95 pointer-events-none"
                }`}
            >
                {/* Header */}
                <div className="bg-gradient-to-r from-indigo-600 to-indigo-700 px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <MessageCircle className="w-5 h-5 text-white" />
                        <h3 className="font-semibold text-white">
                            Course Chat
                        </h3>
                    </div>
                    <button
                        onClick={() => setIsOpen(false)}
                        className="text-white hover:bg-indigo-800 p-1 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Messages Container */}
                <div className="h-80 overflow-y-auto flex flex-col gap-3 p-4 bg-slate-50 dark:bg-slate-800">
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
                                className={`max-w-xs px-4 py-2 rounded-lg ${
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

                {/* Input Area */}
                <div className="border-t border-slate-200 dark:border-slate-700 p-3 bg-white dark:bg-slate-900 flex gap-2">
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
                className="w-14 h-14 rounded-full bg-gradient-to-br from-indigo-600 to-indigo-700 text-white shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center hover:scale-110 active:scale-95"
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
