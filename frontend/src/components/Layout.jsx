import React from 'react';
import { Bot, FileText, Settings, Github } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import clsx from 'clsx';

const Layout = ({ children }) => {
    const location = useLocation();

    const NavItem = ({ to, icon: Icon, label }) => {
        const isActive = location.pathname === to;
        return (
            <Link
                to={to}
                className={clsx(
                    "flex items-center gap-2 px-3 py-2 rounded-lg transition-colors text-sm font-medium",
                    isActive
                        ? "bg-primary-500/10 text-primary"
                        : "text-muted hover:text-white hover:bg-slate-800"
                )}
            >
                <Icon size={18} />
                <span>{label}</span>
            </Link>
        );
    };

    return (
        <div className="flex h-screen bg-app text-main overflow-hidden">
            {/* Sidebar */}
            <aside className="w-64 border-r border-border-color bg-card flex flex-col">
                <div className="p-6">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-500/20">
                            <Bot className="text-white" size={24} />
                        </div>
                        <div>
                            <h1 className="text-lg font-bold leading-tight">ResumeAI</h1>
                            <p className="text-xs text-muted">Local Assistant</p>
                        </div>
                    </div>
                </div>

                <nav className="flex-1 px-4 space-y-1">
                    <NavItem to="/" icon={FileText} label="Dashboard" />
                    <NavItem to="/settings" icon={Settings} label="Settings" />
                </nav>

                <div className="p-4 border-t border-border-color">
                    <a
                        href="https://github.com/google-deepmind"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-xs text-muted hover:text-white transition-colors"
                    >
                        <Github size={16} />
                        <span>Open Source</span>
                    </a>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-auto bg-app relative">
                {/* Background Gradient Effect */}
                <div className="absolute top-0 left-0 w-full h-96 bg-gradient-to-b from-primary-900/20 to-transparent pointer-events-none" />

                <div className="relative z-10 p-8 max-w-7xl mx-auto">
                    {children}
                </div>
            </main>
        </div>
    );
};

export default Layout;
