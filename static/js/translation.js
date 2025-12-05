// ===================================
// Translation Page JavaScript
// ===================================

let selectedFile = null;
let mediaRecorder = null;
let audioChunks = [];
let recordingInterval = null;
let recordingSeconds = 0;

document.addEventListener('DOMContentLoaded', function() {
    // Load available languages from server
    loadLanguages();

    // Method tabs switching
    const methodTabs = document.querySelectorAll('.method-tab');
    const methodContents = document.querySelectorAll('.method-content');
    
    methodTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const method = this.dataset.method;
            
            // Update active tab
            methodTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Update active content
            methodContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === method + 'Method') {
                    content.classList.add('active');
                }
            });
            
            // Reset states
            resetTranslation();
        });
    });
    
    // Text input handling
    const inputText = document.getElementById('inputText');
    if (inputText) {
        const charCount = document.getElementById('charCount');
        
        inputText.addEventListener('input', function() {
            const length = this.value.length;
            charCount.textContent = length;
            
            if (length > 1000) {
                this.value = this.value.substring(0, 1000);
                charCount.textContent = 1000;
            }
        });
    }
    
    // File upload handling (only if upload elements exist)
    const uploadArea = document.getElementById('uploadArea');
    const audioFileInput = document.getElementById('audioFile');
    const translateButton = document.getElementById('translateButton');

    if (uploadArea && audioFileInput) {
        uploadArea.addEventListener('click', () => {
            audioFileInput.click();
        });

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'var(--primary-color)';
            uploadArea.style.backgroundColor = 'rgba(99, 102, 241, 0.1)';
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = '';
            uploadArea.style.backgroundColor = '';
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '';
            uploadArea.style.backgroundColor = '';

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelect(files[0]);
            }
        });

        audioFileInput.addEventListener('change', function(e) {
            if (this.files.length > 0) {
                handleFileSelect(this.files[0]);
            }
        });
    }
    
    // Record button handling
    const recordButton = document.getElementById('recordButton');
    recordButton.addEventListener('click', toggleRecording);
    
    // Translate button
    translateButton.addEventListener('click', performTranslation);
});

function handleFileSelect(file) {
    if (!file.type.startsWith('audio/')) {
        showToast('Please select an audio file', 'danger');
        return;
    }
    
    selectedFile = file;
    
    // Show file info
    document.getElementById('uploadArea').style.display = 'none';
    const fileInfo = document.getElementById('fileInfo');
    fileInfo.style.display = 'flex';
    document.getElementById('fileName').textContent = file.name;
}

async function loadLanguages() {
    try {
        const response = await fetch('/api/languages');
        const data = await response.json();

        if (data.success && data.languages) {
            const select = document.getElementById('targetLanguage');
            // Clear existing options
            select.innerHTML = '';

            Object.entries(data.languages).forEach(([code, name]) => {
                const opt = document.createElement('option');
                opt.value = code;
                opt.textContent = name;
                select.appendChild(opt);
            });
        }
    } catch (err) {
        console.warn('Could not load languages:', err);
    }
}

function clearFile() {
    selectedFile = null;
    const audioInput = document.getElementById('audioFile');
    if (audioInput) audioInput.value = '';
    const uploadAreaEl = document.getElementById('uploadArea');
    if (uploadAreaEl) uploadAreaEl.style.display = 'block';
    const fileInfo = document.getElementById('fileInfo');
    if (fileInfo) fileInfo.style.display = 'none';
    resetResults();
}

function clearTextInput() {
    const inputText = document.getElementById('inputText');
    if (inputText) {
        inputText.value = '';
        document.getElementById('charCount').textContent = '0';
    }
    resetResults();
}

async function toggleRecording() {
    const recordButton = document.getElementById('recordButton');
    const recordStatus = document.getElementById('recordStatus');
    const recordTimer = document.getElementById('recordTimer');
    const pulseRing = document.querySelector('.pulse-ring');
    
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            mediaRecorder.addEventListener('dataavailable', event => {
                audioChunks.push(event.data);
            });
            
            mediaRecorder.addEventListener('stop', async () => {
                // Use the actual MIME type provided by the MediaRecorder when available
                const mimeType = mediaRecorder && mediaRecorder.mimeType ? mediaRecorder.mimeType : 'audio/webm';
                const audioBlob = new Blob(audioChunks, { type: mimeType });

                // Try to convert recorded Blob to WAV16 on the client so server doesn't need ffmpeg
                try {
                    const wavBlob = await encodeBlobToWav(audioBlob);
                    selectedFile = new File([wavBlob], 'recording.wav', { type: 'audio/wav' });
                } catch (err) {
                    // If conversion fails, fall back to original blob
                    console.warn('Client-side WAV conversion failed, using raw blob:', err);
                    const ext = mimeType.includes('webm') ? 'webm' : (mimeType.includes('ogg') ? 'ogg' : 'dat');
                    selectedFile = new File([audioBlob], `recording.${ext}`, { type: mimeType });
                }

                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());

                showToast('Recording saved successfully', 'success');
            });
            
            mediaRecorder.start();
            recordingSeconds = 0;
            
            // Update UI
            recordButton.classList.add('recording');
            recordButton.innerHTML = '<i class="las la-stop"></i>';
            recordStatus.textContent = 'Recording... Click to stop';
            pulseRing.classList.add('active');
            
            // Start timer
            recordingInterval = setInterval(() => {
                recordingSeconds++;
                const minutes = Math.floor(recordingSeconds / 60);
                const seconds = recordingSeconds % 60;
                recordTimer.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            }, 1000);
            
        } catch (error) {
            console.error('Error accessing microphone:', error);
            showToast('Could not access microphone. Please check permissions.', 'danger');
        }
    } else {
        // Stop recording
        mediaRecorder.stop();
        clearInterval(recordingInterval);
        
        // Reset UI
        recordButton.classList.remove('recording');
        recordButton.innerHTML = '<i class="las la-microphone"></i>';
        recordStatus.textContent = 'Recording saved! Click to record again';
        pulseRing.classList.remove('active');
    }
}

async function performTranslation() {
    const activeMethod = document.querySelector('.method-tab.active').dataset.method;
    
    if (activeMethod === 'text') {
        await translateText();
    } else {
        await translateAudio();
    }
}

async function translateText() {
    const inputText = document.getElementById('inputText');
    if (!inputText) {
        showToast('Text input not available', 'danger');
        return;
    }
    
    const text = inputText.value.trim();
    
    if (!text) {
        showToast('Please enter some text to translate', 'warning');
        return;
    }
    
    const targetLanguage = document.getElementById('targetLanguage').value;
    const translateButton = document.getElementById('translateButton');
    const spinner = document.getElementById('translateSpinner');
    
    translateButton.disabled = true;
    spinner.style.display = 'inline-block';
    resetResults();
    
    try {
        const response = await fetch('/api/translate-text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                target_language: targetLanguage
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayResults(data);
            showToast('Translation completed successfully!', 'success');
        } else {
            throw new Error(data.error || 'Translation failed');
        }
        
    } catch (error) {
        console.error('Translation error:', error);
        showToast(error.message || 'An error occurred during translation', 'danger');
    } finally {
        translateButton.disabled = false;
        spinner.style.display = 'none';
    }
}

async function translateAudio() {
    if (!selectedFile) {
        showToast('Please select or record an audio file first', 'warning');
        return;
    }
    
    const targetLanguage = document.getElementById('targetLanguage').value;
    const translateButton = document.getElementById('translateButton');
    const spinner = document.getElementById('translateSpinner');
    
    // Show loading state
    translateButton.disabled = true;
    spinner.style.display = 'inline-block';
    resetResults();
    
    try {
        const formData = new FormData();
        formData.append('audio', selectedFile);
        formData.append('target_language', targetLanguage);
        
        const response = await fetch('/api/translate', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayResults(data);
            showToast('Translation completed successfully!', 'success');
        } else {
            throw new Error(data.error || 'Translation failed');
        }
        
    } catch (error) {
        console.error('Translation error:', error);
        showToast(error.message || 'An error occurred during translation', 'danger');
    } finally {
        translateButton.disabled = false;
        spinner.style.display = 'none';
    }
}

function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    const originalText = document.getElementById('originalText');
    const translatedText = document.getElementById('translatedText');
    
    originalText.textContent = data.original_text;
    translatedText.textContent = data.translated_text;
    
    // Store translated text for TTS
    window.currentTranslation = data.translated_text;
    // Store URL returned by server (if any)
    window.currentTTS = data.tts_url || null;
    
    resultsDiv.style.display = 'block';
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function resetResults() {
    const resultsDiv = document.getElementById('results');
    resultsDiv.style.display = 'none';
    window.currentTranslation = null;
}

function resetTranslation() {
    clearFile();
    resetResults();
    
    // Reset recording state
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }
    
    const recordButton = document.getElementById('recordButton');
    const recordStatus = document.getElementById('recordStatus');
    const recordTimer = document.getElementById('recordTimer');
    const pulseRing = document.querySelector('.pulse-ring');
    
    recordButton.classList.remove('recording');
    recordButton.innerHTML = '<i class="las la-microphone"></i>';
    recordStatus.textContent = 'Click to start recording';
    recordTimer.textContent = '00:00';
    pulseRing.classList.remove('active');
    
    if (recordingInterval) {
        clearInterval(recordingInterval);
    }
}

// Encode a recorded Blob to a WAV (16-bit PCM) Blob in the browser using WebAudio
async function encodeBlobToWav(blob) {
    const arrayBuffer = await blob.arrayBuffer();
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) throw new Error('Web Audio API not supported');
    const ctx = new AudioCtx();
    const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));

    const numChannels = Math.min(2, audioBuffer.numberOfChannels);
    const sampleRate = audioBuffer.sampleRate;
    const length = audioBuffer.length * numChannels * 2 + 44;
    const buffer = new ArrayBuffer(length);
    const view = new DataView(buffer);

    /* RIFF identifier */ writeString(view, 0, 'RIFF');
    /* file length */ view.setUint32(4, 36 + audioBuffer.length * numChannels * 2, true);
    /* RIFF type */ writeString(view, 8, 'WAVE');
    /* format chunk identifier */ writeString(view, 12, 'fmt ');
    /* format chunk length */ view.setUint32(16, 16, true);
    /* sample format (raw) */ view.setUint16(20, 1, true);
    /* channel count */ view.setUint16(22, numChannels, true);
    /* sample rate */ view.setUint32(24, sampleRate, true);
    /* byte rate (sampleRate * blockAlign) */ view.setUint32(28, sampleRate * numChannels * 2, true);
    /* block align (channelCount * bytesPerSample) */ view.setUint16(32, numChannels * 2, true);
    /* bits per sample */ view.setUint16(34, 16, true);
    /* data chunk identifier */ writeString(view, 36, 'data');
    /* data chunk length */ view.setUint32(40, audioBuffer.length * numChannels * 2, true);

    // write interleaved PCM16 samples
    let offset = 44;
    const channels = [];
    for (let i = 0; i < numChannels; i++) channels.push(audioBuffer.getChannelData(i));

    for (let i = 0; i < audioBuffer.length; i++) {
        for (let ch = 0; ch < numChannels; ch++) {
            let sample = Math.max(-1, Math.min(1, channels[ch][i]));
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
            offset += 2;
        }
    }

    ctx.close();
    return new Blob([view], { type: 'audio/wav' });
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

function copyText(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        copyToClipboard(element.textContent);
    }
}

async function speakText() {
    if (!window.currentTranslation) {
        showToast('No translation available to speak', 'warning');
        return;
    }
    
    try {
        // If server already returned a TTS URL when translating, play it
        if (window.currentTTS) {
            const audio = new Audio(window.currentTTS);
            await audio.play();
            showToast('Playing audio...', 'info');
            return;
        }

        // Otherwise request server to generate TTS and return the URL
        const response = await fetch('/api/text-to-speech', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: window.currentTranslation })
        });

        const data = await response.json();

        if (data.success && data.url) {
            window.currentTTS = data.url;
            const audio = new Audio(data.url);
            await audio.play();
            showToast('Playing audio...', 'info');
        } else {
            throw new Error(data.error || 'Text-to-speech failed');
        }
    } catch (error) {
        console.error('TTS error:', error);
        showToast(error.message || 'Failed to play audio', 'danger');
    }
}