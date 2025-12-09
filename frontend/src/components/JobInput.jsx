import React, { useState } from 'react';
import { Link, FileText } from 'lucide-react';
import clsx from 'clsx';
import { motion } from 'framer-motion';

const JobInput = ({ onJobChange }) => {
    const [activeTab, setActiveTab] = useState('url'); // 'url' or 'text'
    const [jobUrl, setJobUrl] = useState('');
    const [jobText, setJobText] = useState('');

    const handleUrlChange = (e) => {
        setJobUrl(e.target.value);
        onJobChange?.({ type: 'url', value: e.target.value });
    };

    const handleTextChange = (e) => {
        setJobText(e.target.value);
        onJobChange?.({ type: 'text', value: e.target.value });
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Target Job</h3>
                <div className="flex bg-slate-800 p-1 rounded-lg">
                    <button
                        onClick={() => setActiveTab('url')}
                        className={clsx(
                            "px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-2",
                            activeTab === 'url' ? "bg-slate-700 text-white shadow-sm" : "text-muted hover:text-white"
                        )}
                    >
                        <Link size={14} />
                        Job URL
                    </button>
                    <button
                        onClick={() => setActiveTab('text')}
                        className={clsx(
                            "px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-2",
                            activeTab === 'text' ? "bg-slate-700 text-white shadow-sm" : "text-muted hover:text-white"
                        )}
                    >
                        <FileText size={14} />
                        Description
                    </button>
                </div>
            </div>

            <div className="card bg-card/50">
                {activeTab === 'url' ? (
                    <motion.div
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                    >
                        <label className="block text-sm font-medium mb-2 text-muted">Job Posting URL</label>
                        <div className="relative">
                            <Link className="absolute left-3 top-3 text-muted" size={18} />
                            <input
                                type="url"
                                value={jobUrl}
                                onChange={handleUrlChange}
                                placeholder="https://linkedin.com/jobs/..."
                                className="input pl-10"
                            />
                        </div>
                        <p className="text-xs text-muted mt-2">
                            We'll scrape this page to extract keywords and requirements.
                        </p>
                    </motion.div>
                ) : (
                    <motion.div
                        initial={{ opacity: 0, x: 10 }}
                        animate={{ opacity: 1, x: 0 }}
                    >
                        <label className="block text-sm font-medium mb-2 text-muted">Paste Job Description</label>
                        <textarea
                            value={jobText}
                            onChange={handleTextChange}
                            rows={6}
                            placeholder="Paste the full job description here..."
                            className="input resize-none"
                        />
                    </motion.div>
                )}
            </div>
        </div>
    );
};

export default JobInput;
