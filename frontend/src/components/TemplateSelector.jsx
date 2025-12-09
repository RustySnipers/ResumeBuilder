import React from 'react';
import { clsx } from 'clsx';
import { Check } from 'lucide-react';

const TEMPLATES = [
    {
        id: 'standard_ats',
        name: 'Standard ATS',
        description: 'Clean, simple, single-column layout optimized for Taleo and iCIMS.',
        previewColor: 'bg-white',
        textColor: 'text-slate-900',
    },
    {
        id: 'modern_ats',
        name: 'Modern Professional',
        description: 'Professional typography with subtle accents. Still 100% ATS friendly.',
        previewColor: 'bg-slate-50',
        textColor: 'text-slate-800',
        accentColor: 'border-l-4 border-indigo-500',
    },
    {
        id: 'strict_ats',
        name: 'Strict ATS (iCIMS/Taleo)',
        description: 'Maximum compatibility. Black & white, standard fonts, no tables.',
        previewColor: 'bg-white',
        textColor: 'text-black',
        accentColor: 'border-l-4 border-black',
    }
];

const TemplateSelector = ({ selectedTemplate, onSelect }) => {
    return (
        <div className="space-y-4">
            <h3 className="text-lg font-semibold">Choose Template</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {TEMPLATES.map((template) => (
                    <div
                        key={template.id}
                        onClick={() => onSelect(template.id)}
                        className={clsx(
                            "relative p-4 rounded-xl border-2 cursor-pointer transition-all hover:scale-[1.02]",
                            selectedTemplate === template.id
                                ? "border-primary-500 bg-primary-500/5 shadow-md"
                                : "border-slate-700 hover:border-slate-600 bg-card"
                        )}
                    >
                        <div className="flex gap-4">
                            {/* Mini Preview */}
                            <div className={clsx(
                                "w-16 h-20 shadow-sm rounded border border-slate-200 flex flex-col p-1 gap-1 text-[4px] leading-tight overflow-hidden",
                                template.previewColor,
                                template.textColor,
                                template.accentColor
                            )}>
                                <div className="w-8 h-1 bg-current opacity-20 mb-1" />
                                <div className="w-full h-0.5 bg-current opacity-10" />
                                <div className="w-full h-0.5 bg-current opacity-10" />
                                <div className="w-10 h-0.5 bg-current opacity-10" />
                                <div className="w-6 h-1 bg-current opacity-20 mt-1" />
                                <div className="w-full h-0.5 bg-current opacity-10" />
                                <div className="w-full h-0.5 bg-current opacity-10" />
                            </div>

                            <div>
                                <h4 className="font-semibold text-main">{template.name}</h4>
                                <p className="text-xs text-muted mt-1">{template.description}</p>
                            </div>
                        </div>

                        {selectedTemplate === template.id && (
                            <div className="absolute top-3 right-3 w-6 h-6 bg-primary-500 rounded-full flex items-center justify-center text-white">
                                <Check size={14} />
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default TemplateSelector;
