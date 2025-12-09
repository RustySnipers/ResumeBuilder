import React from 'react';
import { Linkedin, Globe, Github } from 'lucide-react';

const SocialInputs = ({ onSocialChange }) => {
    const handleChange = (field, value) => {
        onSocialChange?.(field, value);
    };

    return (
        <div className="space-y-4">
            <h3 className="text-lg font-semibold">Your Profiles</h3>
            <div className="card bg-card/50 space-y-4">
                {/* LinkedIn */}
                <div>
                    <label className="block text-sm font-medium mb-2 text-muted">LinkedIn URL</label>
                    <div className="relative">
                        <Linkedin className="absolute left-3 top-3 text-[#0a66c2]" size={18} />
                        <input
                            type="url"
                            placeholder="https://linkedin.com/in/username"
                            className="input pl-10"
                            onChange={(e) => handleChange('linkedin', e.target.value)}
                        />
                    </div>
                </div>

                {/* Portfolio / Website */}
                <div>
                    <label className="block text-sm font-medium mb-2 text-muted">Portfolio / Website</label>
                    <div className="relative">
                        <Globe className="absolute left-3 top-3 text-emerald-500" size={18} />
                        <input
                            type="url"
                            placeholder="https://yourportfolio.com"
                            className="input pl-10"
                            onChange={(e) => handleChange('website', e.target.value)}
                        />
                    </div>
                </div>

                {/* GitHub (Optional) */}
                <div>
                    <label className="block text-sm font-medium mb-2 text-muted">GitHub (Optional)</label>
                    <div className="relative">
                        <Github className="absolute left-3 top-3 text-white" size={18} />
                        <input
                            type="url"
                            placeholder="https://github.com/username"
                            className="input pl-10"
                            onChange={(e) => handleChange('github', e.target.value)}
                        />
                    </div>
                </div>

                <p className="text-xs text-muted">
                    We'll scrape these profiles to add relevant skills and projects.
                </p>
            </div>
        </div>
    );
};

export default SocialInputs;
