import React, { useState, useEffect } from 'react';
import { ArrowRight, Sparkles, Check, Download, AlertCircle, Bot, FileText, Search, BarChart, Eye, FileCode, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';
import ResumeUploader from '../components/ResumeUploader';
import JobInput from '../components/JobInput';
import SocialInputs from '../components/SocialInputs';
import TemplateSelector from '../components/TemplateSelector';
import { resumeService } from '../services/api';
import { useAnalysisStream } from '../hooks/useAnalysisStream';

const STEPS = [
    { id: 'upload', title: 'Upload Resume' },
    { id: 'details', title: 'Job & Profile' },
    { id: 'analysis', title: 'Real-Time Analysis' },
];

const PROMPTS = [
    "Thinking about your resume...",
    "Scanning for ATS compatibility...",
    "Analyzing skills gap...",
    "Drafting improvements...",
];

const Dashboard = () => {
    const [currentStep, setCurrentStep] = useState(0);
    const [data, setData] = useState({
        resumeFile: null,
        resumeId: null,
        jobDetails: { type: 'url', value: '' },
        socials: { linkedin: '', website: '', github: '' },
        template: 'standard_ats',
    });

    // Custom Hook for Streaming
    const {
        startStream,
        stopStream,
        status,
        statusMessage,
        atsData,
        streamedText,
        error: streamError
    } = useAnalysisStream();

    const [uiError, setUiError] = useState(null);
    const [showPreview, setShowPreview] = useState(false);
    const [previewHtml, setPreviewHtml] = useState('');
    const [isOptimizing, setIsOptimizing] = useState(false);

    const handleNext = () => {
        if (currentStep < STEPS.length - 1) {
            setCurrentStep(prev => prev + 1);
        }
    };

    const handleStartAnalysis = async () => {
        if (!data.resumeId) {
            setUiError("Please upload a resume first.");
            return;
        }
        setUiError(null);
        setCurrentStep(2);

        const jobDesc = data.jobDetails.type === 'text' ? data.jobDetails.value : null;
        const jobUrl = data.jobDetails.type === 'url' ? data.jobDetails.value : null;

        startStream(data.resumeId, jobDesc, jobUrl);
    };

    const handleExport = async (format = 'docx') => {
        if (!data.resumeId) return;
        try {
            const blob = await resumeService.export(data.resumeId, data.template, format);
            const url = window.URL.createObjectURL(new Blob([blob]));
            const link = document.createElement('a');
            link.href = url;
            const ext = format === 'markdown' ? 'md' : format;
            link.setAttribute('download', `resume_optimized.${ext}`);
            document.body.appendChild(link);
            link.click();
            link.parentNode.removeChild(link);
        } catch (err) {
            console.error("Export failed:", err);
            setUiError(`Export to ${format.toUpperCase()} failed. Please try again.`);
        }
    };

    const handlePreview = async () => {
        if (!data.resumeId) return;
        try {
            const html = await resumeService.getPreview(data.resumeId, data.template);
            setPreviewHtml(html);
            setShowPreview(true);
        } catch (err) {
            console.error("Preview failed:", err);
            setUiError("Preview generation failed.");
        }
    };

    const handleOptimize = async () => {
        if (!data.resumeId) return;
        setIsOptimizing(true);
        setUiError(null);
        setPreviewHtml(''); // Clear cached preview
        try {
            const jdText = data.jobDetails.type === 'text' ? data.jobDetails.value : "Please optimize based on standard ATS best practices.";

            const res = await resumeService.optimize(data.resumeId, jdText);

            // UPDATE ID to the new optimized resume
            setData(prev => ({ ...prev, resumeId: res.new_resume_id }));

            // Re-run analysis to show improved score
            setTimeout(async () => {
                // Use the NEW resume ID explicitly
                const jobDesc = data.jobDetails.type === 'text' ? data.jobDetails.value : null;
                const jobUrl = data.jobDetails.type === 'url' ? data.jobDetails.value : null;
                startStream(res.new_resume_id, jobDesc, jobUrl);

                // Also auto-fetch preview of optimized resume
                try {
                    const html = await resumeService.getPreview(res.new_resume_id, data.template);
                    setPreviewHtml(html);
                } catch (e) {
                    console.warn('Auto-preview failed', e);
                }
            }, 500);

        } catch (err) {
            console.error("Optimization failed:", err);
            setUiError("Optimization failed. Backend LLM issue?");
        } finally {
            setIsOptimizing(false);
        }
    };

    // Determine Status Icon
    const getStatusIcon = () => {
        if (status === 'error') return <AlertCircle className="text-error" size={32} />;
        if (status === 'complete') return <Check className="text-success" size={32} />;
        return <Bot className="text-primary-400 animate-pulse" size={32} />;
    };

    return (
        <div className="max-w-5xl mx-auto pb-20">
            <header className="text-center mb-16 pt-10">
                <h2 className="text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-primary-300 via-white to-accent-400 drop-shadow-sm">
                    AI Resume Architect
                </h2>
                <p className="text-primary-100/70 text-lg max-w-2xl mx-auto">
                    Transform your resume with real-time AI analysis. Built for Taleo, iCIMS, and modern recruiting.
                </p>
            </header>

            {/* Steps Indicator */}
            <div className="flex justify-center mb-12">
                <div className="glass-card px-8 py-4 flex items-center space-x-6 backdrop-blur-xl">
                    {STEPS.map((step, index) => (
                        <div key={step.id} className="flex items-center">
                            <div
                                className={clsx(
                                    "w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300",
                                    index <= currentStep
                                        ? "bg-primary-500 text-white shadow-[0_0_15px_rgba(99,102,241,0.5)]"
                                        : "bg-white/5 text-white/30 border border-white/10"
                                )}
                            >
                                {index < currentStep ? <Check size={16} /> : index + 1}
                            </div>
                            <span
                                className={clsx(
                                    "ml-3 text-sm font-medium transition-colors",
                                    index <= currentStep ? "text-white" : "text-white/30"
                                )}
                            >
                                {step.title}
                            </span>
                            {index < STEPS.length - 1 && (
                                <div className={clsx(
                                    "w-12 h-px mx-4 transition-colors",
                                    index < currentStep ? "bg-primary-500/50" : "bg-white/10"
                                )} />
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Main Content Area */}
            <div className="relative min-h-[500px]">
                {(uiError || streamError) && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mb-8 p-4 glass-card border-error/30 bg-error/5 flex items-center gap-3 text-white"
                    >
                        <AlertCircle className="text-error" size={20} />
                        <p>{uiError || streamError}</p>
                    </motion.div>
                )}

                <AnimatePresence mode="wait">
                    {/* Step 1: Upload */}
                    {currentStep === 0 && (
                        <motion.div
                            key="step1"
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 20 }}
                        >
                            <ResumeUploader
                                onUploadComplete={async (file) => {
                                    try {
                                        const res = await resumeService.upload(file);
                                        setData(prev => ({ ...prev, resumeFile: file, resumeId: res.id }));
                                        setTimeout(handleNext, 800);
                                    } catch (err) {
                                        setUiError("Upload failed. Backend might be offline.");
                                    }
                                }}
                            />
                        </motion.div>
                    )}

                    {/* Step 2: Job Details */}
                    {currentStep === 1 && (
                        <motion.div
                            key="step2"
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 20 }}
                            className="grid grid-cols-1 gap-8"
                        >
                            <div className="glass-card p-6">
                                <JobInput
                                    onJobChange={(val) => setData(prev => ({ ...prev, jobDetails: val }))}
                                />
                            </div>

                            <div className="glass-card p-6">
                                <TemplateSelector
                                    selectedTemplate={data.template}
                                    onSelect={(val) => setData(prev => ({ ...prev, template: val }))}
                                />
                            </div>

                            <div className="flex justify-end pt-4">
                                <button
                                    onClick={handleStartAnalysis}
                                    className="btn btn-primary px-10 py-4 text-lg flex items-center gap-3 shadow-[0_0_20px_rgba(99,102,241,0.4)] hover:shadow-[0_0_30px_rgba(99,102,241,0.6)] border border-white/10"
                                >
                                    <Sparkles size={20} />
                                    Launch Analysis
                                </button>
                            </div>
                        </motion.div>
                    )}

                    {/* Step 3: Streaming Analysis */}
                    {currentStep === 2 && (
                        <motion.div
                            key="step3"
                            initial={{ opacity: 0, scale: 0.98 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="space-y-6"
                        >
                            {/* Status Card */}
                            <div className="glass-card p-6 flex flex-col md:flex-row items-center justify-between gap-6">
                                <div className="flex items-center gap-4">
                                    <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center border border-white/10 shadow-inner">
                                        {getStatusIcon()}
                                    </div>
                                    <div>
                                        <h3 className="text-xl font-bold text-white mb-1">
                                            {status === 'complete' ? 'Analysis Complete' : 'AI Agent Working...'}
                                        </h3>
                                        <div className="flex items-center gap-2 text-primary-200">
                                            {status !== 'complete' && status !== 'error' && (
                                                <span className="w-2 h-2 rounded-full bg-primary-400 animate-ping" />
                                            )}
                                            <span className="text-sm font-medium tracking-wide">
                                                {statusMessage || "Initializing..."}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {atsData && (
                                    <div className="flex items-center gap-8 px-6 py-3 bg-white/5 rounded-xl border border-white/10">
                                        <div className="text-right">
                                            <div className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary-300 to-white">
                                                {atsData.score}/100
                                            </div>
                                            <div className="text-xs text-muted uppercase tracking-wider">ATS Score</div>
                                        </div>
                                        <div className="h-10 w-px bg-white/10" />
                                        <div className="text-sm text-right">
                                            <div><span className="text-success">{atsData.matched_keywords?.length || 0}</span> Matched</div>
                                            <div><span className="text-error">{atsData.missing_keywords?.length || 0}</span> Missing</div>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Streaming Content */}
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                {/* Left Col: ATS Breakdown */}
                                <div className="lg:col-span-1 space-y-6">
                                    {atsData ? (
                                        <motion.div
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            className="glass-card p-6 space-y-6"
                                        >
                                            <div className="space-y-3">
                                                <h4 className="text-sm font-bold text-muted uppercase tracking-wider mb-4 border-b border-white/10 pb-2">Missing Capabilities</h4>
                                                <div className="flex flex-wrap gap-2">
                                                    {atsData.missing_keywords?.map((kw, i) => (
                                                        <span key={i} className="px-2 py-1 bg-error/10 text-error-200 border border-error/20 rounded-md text-xs">
                                                            {kw}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>

                                            <div className="space-y-3">
                                                <h4 className="text-sm font-bold text-muted uppercase tracking-wider mb-4 border-b border-white/10 pb-2">Matched Strengths</h4>
                                                <div className="flex flex-wrap gap-2">
                                                    {atsData.matched_keywords?.map((kw, i) => (
                                                        <span key={i} className="px-2 py-1 bg-success/10 text-success-200 border border-success/20 rounded-md text-xs">
                                                            {kw}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        </motion.div>
                                    ) : (
                                        <div className="glass-card p-6 h-48 flex items-center justify-center text-white/20 text-sm italic">
                                            ATS data usage pending...
                                        </div>
                                    )}
                                </div>

                                {/* Right Col: LLM Analysis Stream */}
                                <div className="lg:col-span-2">
                                    <div className="glass-card p-8 min-h-[400px] relative overflow-hidden">
                                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-primary-500/50 to-transparent" />

                                        <h4 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                                            <Sparkles size={18} className="text-primary-400" />
                                            AI Strategic Insight
                                        </h4>

                                        <div className="prose prose-invert prose-sm max-w-none text-slate-300 leading-relaxed">
                                            {streamedText ? (
                                                <ReactMarkdown>{streamedText}</ReactMarkdown>
                                            ) : (
                                                <div className="flex flex-col items-center justify-center h-40 space-y-4 opacity-30">
                                                    <div className="w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" />
                                                    <p className="text-sm">Connecting to Neural Engine...</p>
                                                </div>
                                            )}
                                            {status === 'streaming' && (
                                                <span className="inline-block w-2 h-4 bg-primary-500 ml-1 animate-pulse align-middle" />
                                            )}
                                        </div>
                                    </div>

                                    {status === 'complete' && (
                                        <motion.div
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: 0.5 }}
                                            className="mt-6 space-y-4"
                                        >
                                            <div className="flex flex-wrap items-center justify-end gap-3">
                                                <button
                                                    onClick={() => setCurrentStep(1)}
                                                    className="btn px-4 py-3 bg-white/5 hover:bg-white/10 text-white border border-white/10"
                                                >
                                                    Back
                                                </button>

                                                <button
                                                    onClick={handlePreview}
                                                    className="btn btn-secondary px-6 py-3 text-white shadow-lg flex items-center gap-2 border border-white/10 bg-white/5 hover:bg-white/10"
                                                >
                                                    <Eye size={18} />
                                                    Preview
                                                </button>

                                                <button
                                                    onClick={handleOptimize}
                                                    disabled={isOptimizing}
                                                    className="btn btn-primary px-6 py-3 text-white shadow-lg flex items-center gap-2"
                                                >
                                                    {isOptimizing ? (
                                                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                                    ) : (
                                                        <Sparkles size={18} />
                                                    )}
                                                    {isOptimizing ? "Optimizing..." : "Optimize Resume"}
                                                </button>

                                                <div className="h-8 w-px bg-white/10 mx-2" />

                                                <button
                                                    onClick={() => handleExport('pdf')}
                                                    className="btn px-4 py-3 bg-white/5 hover:bg-white/10 text-white border border-white/10 flex items-center gap-2"
                                                    title="Download PDF"
                                                >
                                                    <FileText size={18} /> PDF
                                                </button>
                                                <button
                                                    onClick={() => handleExport('docx')}
                                                    className="btn px-4 py-3 bg-white/5 hover:bg-white/10 text-white border border-white/10 flex items-center gap-2"
                                                    title="Download Word Doc"
                                                >
                                                    <FileText size={18} /> DOCX
                                                </button>
                                                <button
                                                    onClick={() => handleExport('markdown')}
                                                    className="btn px-4 py-3 bg-white/5 hover:bg-white/10 text-white border border-white/10 flex items-center gap-2"
                                                    title="Download Markdown"
                                                >
                                                    <FileCode size={18} /> MD
                                                </button>
                                            </div>
                                        </motion.div>
                                    )}
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Preview Modal */}
                <AnimatePresence>
                    {showPreview && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
                            onClick={() => setShowPreview(false)}
                        >
                            <motion.div
                                initial={{ scale: 0.9, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                exit={{ scale: 0.9, opacity: 0 }}
                                className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col"
                                onClick={e => e.stopPropagation()}
                            >
                                <div className="p-4 border-b flex justify-between items-center bg-gray-50">
                                    <h3 className="text-lg font-bold text-gray-800">Resume Preview</h3>
                                    <button
                                        onClick={() => setShowPreview(false)}
                                        className="p-2 hover:bg-gray-200 rounded-full transition-colors text-gray-500"
                                    >
                                        <X size={20} />
                                    </button>
                                </div>
                                <div className="flex-1 overflow-auto p-8 bg-white text-gray-900 resume-preview-content">
                                    <div dangerouslySetInnerHTML={{ __html: previewHtml }} />
                                </div>
                                <div className="p-4 border-t bg-gray-50 flex justify-end gap-3">
                                    <button
                                        onClick={() => handleExport('pdf')}
                                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-2"
                                    >
                                        <Download size={16} /> Download PDF
                                    </button>
                                </div>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default Dashboard;
