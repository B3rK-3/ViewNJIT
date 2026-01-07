export default function Loading() {
    return (
        <div className="fixed inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-950 dark:via-slate-900 dark:to-indigo-950 z-50">
            <div className="relative">
                <div className="h-16 w-16 rounded-full border-4 border-slate-200 dark:border-slate-700"></div>
                <div className="absolute top-0 left-0 h-16 w-16 rounded-full border-4 border-indigo-600 border-t-transparent animate-spin"></div>
            </div>
            <h2 className="mt-4 text-lg font-medium text-slate-700 dark:text-slate-300 animate-pulse">
                Loading courses...
            </h2>
        </div>
    );
}
