import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

const ResumeUploader = ({ onUploadComplete }) => {
    const [isDragActive, setIsDragActive] = useState(false);
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);
    const inputRef = useRef(null);

    // Mock upload logic for UI dev (replace with optional prop or hook later)
    const handleUpload = async (selectedFile) => {
        setFile(selectedFile);
        setError(null);
        setUploading(true);

        try {
            // Simulate/Call API
            if (onUploadComplete) {
                await onUploadComplete(selectedFile);
            } else {
                // Fallback simulation
                await new Promise(resolve => setTimeout(resolve, 2000));
            }
            setSuccess(true);
        } catch (err) {
            setError(err.message || 'Upload failed');
        } finally {
            setUploading(false);
        }
    };

    const onDragEnter = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragActive(true);
    };

    const onDragLeave = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragActive(false);
    };

    const onDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const onDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleUpload(e.dataTransfer.files[0]);
        }
    };

    return (
        <div className="w-full max-w-2xl mx-auto">
            <AnimatePresence mode="wait">
                {!success ? (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className={clsx(
                            "relative rounded-xl border-2 border-dashed transition-all duration-300 p-10 text-center cursor-pointer group overflow-hidden bg-card",
                            isDragActive
                                ? "border-primary-500 bg-primary-500/5 scale-[1.01]"
                                : "border-slate-700 hover:border-primary-500/50 hover:bg-slate-800/50",
                            error && "border-error bg-error/5"
                        )}
                        onDragEnter={onDragEnter}
                        onDragLeave={onDragLeave}
                        onDragOver={onDragOver}
                        onDrop={onDrop}
                        onClick={() => inputRef.current?.click()}
                    >
                        <input
                            ref={inputRef}
                            type="file"
                            className="hidden"
                            accept=".pdf,.docx,.txt"
                            onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
                        />

                        <div className="flex flex-col items-center justify-center gap-4 relative z-10">
                            <div className={clsx(
                                "w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300",
                                isDragActive ? "bg-primary-500 text-white shadow-lg shadow-primary-500/30" : "bg-slate-800 text-muted group-hover:bg-primary-500/20 group-hover:text-primary-400"
                            )}>
                                {uploading ? (
                                    <Loader2 className="animate-spin" size={32} />
                                ) : (
                                    <UploadCloud size={32} />
                                )}
                            </div>

                            <div>
                                <h3 className="text-xl font-semibold">
                                    {uploading ? "Uploading..." : "Upload Resume"}
                                </h3>
                                <p className="text-muted mt-2 max-w-xs mx-auto">
                                    Drag and drop your resume here, or click to browse.
                                    <br />
                                    <span className="text-xs opacity-70">Supports PDF, DOCX, TXT</span>
                                </p>
                            </div>

                            {error && (
                                <div className="flex items-center gap-2 text-error text-sm mt-2 bg-error/10 px-3 py-1 rounded-full">
                                    <AlertCircle size={14} />
                                    <span>{error}</span>
                                </div>
                            )}
                        </div>

                        {/* Background Glow Effect */}
                        <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-transparent to-primary-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </motion.div>
                ) : (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="card bg-success/10 border-success/20 text-center py-12"
                    >
                        <div className="w-16 h-16 rounded-full bg-success text-white flex items-center justify-center mx-auto mb-4 shadow-lg shadow-success/20">
                            <CheckCircle size={32} />
                        </div>
                        <h3 className="text-xl font-semibold text-white">Upload Complete!</h3>
                        <p className="text-success-300 mt-2">{file?.name}</p>
                        <button
                            onClick={() => { setSuccess(false); setFile(null); }}
                            className="mt-6 text-sm text-muted hover:text-white underline underline-offset-4"
                        >
                            Upload another
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default ResumeUploader;
