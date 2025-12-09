import { useState, useRef, useCallback } from 'react';

export const useAnalysisStream = () => {
    const [status, setStatus] = useState('idle'); // idle, connecting, streaming, complete, error
    const [statusMessage, setStatusMessage] = useState('');
    const [atsData, setAtsData] = useState(null);
    const [streamedText, setStreamedText] = useState('');
    const [error, setError] = useState(null);
    const abortControllerRef = useRef(null);

    const startStream = useCallback(async (resumeId, jobDescription, jobUrl) => {
        setStatus('connecting');
        setStatusMessage('Initializing Connection...');
        setStreamedText('');
        setAtsData(null);
        setError(null);

        abortControllerRef.current = new AbortController();

        try {
            const response = await fetch('/api/v1/jobs/analyze/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    resume_id: resumeId,
                    job_description: jobDescription,
                    job_url: jobUrl
                }),
                signal: abortControllerRef.current.signal
            });

            if (!response.ok) {
                throw new Error(`Connection failed: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            setStatus('streaming');

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n\n');

                for (const line of lines) {
                    if (!line.trim()) continue;

                    try {
                        const event = JSON.parse(line);

                        switch (event.type) {
                            case 'status':
                                setStatusMessage(event.data);
                                break;
                            case 'ats_result':
                                setAtsData(event.data);
                                break;
                            case 'token':
                                setStreamedText(prev => prev + event.data);
                                break;
                            case 'done':
                                setStatus('complete');
                                break;
                            case 'error':
                                throw new Error(event.data);
                        }
                    } catch (e) {
                        console.warn("Internal parse error", e, line);
                    }
                }
            }

        } catch (err) {
            if (err.name !== 'AbortError') {
                setError(err.message);
                setStatus('error');
            }
        }
    }, []);

    const stopStream = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
    }, []);

    return {
        startStream,
        stopStream,
        status,
        statusMessage,
        atsData,
        streamedText,
        error
    };
};
