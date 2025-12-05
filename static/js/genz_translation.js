// ===================================
// GenZ Slang Translation Page JavaScript
// ===================================

let selectedFile = null;
let mediaRecorder = null;
let audioChunks = [];
let recordingInterval = null;
let recordingSeconds = 0;
let translationMode = 'slang-to-english';

document.addEventListener('DOMContentLoaded', function() {
    initializePage();
});

function initializePage() {
    // Mode selector - now supports auto-detection
    const modeBtns = document.querySelectorAll('.mode-btn');
    modeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            modeBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            translationMode = this.dataset.mode; // 'auto', 'to_english', 'to_genz'
            updatePlaceholder();
            resetResults();
        });
    });
    
    // Method tabs switching
    const methodTabs = document.querySelectorAll('.method-tab');
    const methodContents = document.querySelectorAll('.method-content');
    
    methodTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const method = this.dataset.method;
            
            methodTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            methodContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === method + 'Method') {
                    content.classList.add('active');
                }
            });
            
            resetTranslation();
        });
    });
    
    // Text input handling
    const inputText = document.getElementById('inputText');
    const charCount = document.getElementById('charCount');
    
    inputText.addEventListener('input', function() {
        const length = this.value.length;
        charCount.textContent = length;
        
        if (length > 500) {
            this.value = this.value.substring(0, 500);
            charCount.textContent = 500;
        }
    });
    
    // File upload handling (only if upload elements exist)
    if (document.getElementById('uploadArea')) {
        setupFileUpload();
    }
    
    // Record button
    const recordButton = document.getElementById('recordButton');
    recordButton.addEventListener('click', toggleRecording);
    
    // Translate button
    const translateButton = document.getElementById('translateButton');
    translateButton.addEventListener('click', performTranslation);
    
    // Load slang dictionary
    loadSlangDictionary();
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

function updatePlaceholder() {
    const inputText = document.getElementById('inputText');
    if (translationMode === 'auto') {
        inputText.placeholder = 'Type GenZ slang OR standard English... I\'ll figure out which one! 🤖';
    } else if (translationMode === 'to_english') {
        inputText.placeholder = 'Type your GenZ slang here... e.g., "That party was lit, no cap!"';
    } else {
        inputText.placeholder = 'Type standard English... I\'ll convert it to GenZ slang! e.g., "That was amazing!"';
    }
}

function setupFileUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const audioFileInput = document.getElementById('audioFile');

    if (!uploadArea || !audioFileInput) return;

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

function handleFileSelect(file) {
    if (!file.type.startsWith('audio/')) {
        showToast('Please select an audio file', 'danger');
        return;
    }
    
    selectedFile = file;
    
    document.getElementById('uploadArea').style.display = 'none';
    const fileInfo = document.getElementById('fileInfo');
    fileInfo.style.display = 'flex';
    document.getElementById('fileName').textContent = file.name;
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
    document.getElementById('inputText').value = '';
    document.getElementById('charCount').textContent = '0';
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
            
            mediaRecorder.addEventListener('stop', () => {
                const mimeType = mediaRecorder && mediaRecorder.mimeType ? mediaRecorder.mimeType : 'audio/webm';
                const ext = mimeType.includes('webm') ? 'webm' : (mimeType.includes('ogg') ? 'ogg' : (mimeType.includes('wav') ? 'wav' : (mimeType.includes('mpeg') || mimeType.includes('mp3') ? 'mp3' : 'webm')));
                const audioBlob = new Blob(audioChunks, { type: mimeType });
                selectedFile = new File([audioBlob], `recording.${ext}`, { type: mimeType });

                stream.getTracks().forEach(track => track.stop());
            });
            
            mediaRecorder.start();
            recordingSeconds = 0;
            
            recordButton.classList.add('recording');
            recordButton.innerHTML = '<i class="las la-stop"></i>';
            recordStatus.textContent = 'Recording... Click to stop';
            pulseRing.classList.add('active');
            
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
        mediaRecorder.stop();
        clearInterval(recordingInterval);
        
        recordButton.classList.remove('recording');
        recordButton.innerHTML = '<i class="las la-microphone"></i>';
        recordStatus.textContent = 'Recording saved! Click to record again';
        pulseRing.classList.remove('active');
        
        showToast('Recording saved successfully', 'success');
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
    const inputText = document.getElementById('inputText').value.trim();
    
    if (!inputText) {
        showToast('Please enter some text to translate', 'warning');
        return;
    }
    
    const translateButton = document.getElementById('translateButton');
    const spinner = document.getElementById('translateSpinner');
    
    translateButton.disabled = true;
    spinner.style.display = 'inline-block';
    resetResults();
    
    try {
        const response = await fetch('/api/genz/translate-text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: inputText,
                mode: translationMode
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
    
    const translateButton = document.getElementById('translateButton');
    const spinner = document.getElementById('translateSpinner');
    
    translateButton.disabled = true;
    spinner.style.display = 'inline-block';
    resetResults();
    
    try {
        const formData = new FormData();
        formData.append('audio', selectedFile);
        formData.append('mode', translationMode);
        
        const response = await fetch('/api/genz/translate-audio', {
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
    const explanationsCard = document.getElementById('explanationsCard');
    const explanationsList = document.getElementById('explanationsList');
    
    originalText.textContent = data.original_text;
    translatedText.textContent = data.translated_text;
    
    // Store for TTS
    window.currentTranslation = data.translated_text;
    
    // Display slang explanations if available
    if ((data.explanations && data.explanations.length > 0) || (data.substitutions && data.substitutions.length > 0)) {
        explanationsCard.style.display = 'block';
        explanationsList.innerHTML = '';
        
        // Show explanations for slang-to-english
        if (data.explanations && data.explanations.length > 0) {
            data.explanations.forEach(exp => {
                const expItem = document.createElement('div');
                expItem.className = 'explanation-item';
                expItem.innerHTML = `
                    <div class="slang-term">${exp.slang}</div>
                    <div class="slang-meaning">
                        <i class="las la-arrow-right"></i> ${exp.meaning}
                    </div>
                `;
                explanationsList.appendChild(expItem);
            });
        }
        
        // Show substitutions for english-to-genz
        if (data.substitutions && data.substitutions.length > 0) {
            data.substitutions.forEach(sub => {
                const subItem = document.createElement('div');
                subItem.className = 'explanation-item';
                subItem.innerHTML = `
                    <div class="slang-term">"${sub.original}"</div>
                    <div class="slang-meaning">
                        <i class="las la-arrow-right"></i> "${sub.replacement}" (GenZ slang)
                    </div>
                `;
                explanationsList.appendChild(subItem);
            });
        }
    } else {
        explanationsCard.style.display = 'none';
    }
    
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
    clearTextInput();
    resetResults();
    
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
        const response = await fetch('/api/text-to-speech', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: window.currentTranslation })
        });

        const data = await response.json();

        if (data.success && data.url) {
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

// Slang Dictionary Functions
async function loadSlangDictionary() {
    try {
        const response = await fetch('/api/genz/dictionary');
        const data = await response.json();
        
        if (data.success) {
            window.slangDictionary = data.slang_list;
        }
    } catch (error) {
        console.error('Error loading slang dictionary:', error);
    }
}

function toggleSlangDictionary() {
    const modal = document.getElementById('slangDictionaryModal');
    const isVisible = modal.style.display === 'flex';
    
    if (isVisible) {
        modal.style.display = 'none';
    } else {
        modal.style.display = 'flex';
        displaySlangDictionary(window.slangDictionary || []);
    }
}

function displaySlangDictionary(slangList) {
    const slangListDiv = document.getElementById('slangList');
    
    if (slangList.length === 0) {
        slangListDiv.innerHTML = '<p class="no-results">No slang terms found</p>';
        return;
    }
    
    slangListDiv.innerHTML = '';
    
    slangList.forEach(item => {
        const slangItem = document.createElement('div');
        slangItem.className = 'slang-dictionary-item';
        slangItem.innerHTML = `
            <div class="slang-term-dict">${item.slang}</div>
            <div class="slang-meaning-dict">${item.meaning}</div>
        `;
        slangListDiv.appendChild(slangItem);
    });
}

function searchSlang() {
    const query = document.getElementById('slangSearch').value.toLowerCase();
    
    if (!window.slangDictionary) return;
    
    if (query === '') {
        displaySlangDictionary(window.slangDictionary);
        return;
    }
    
    const filtered = window.slangDictionary.filter(item => 
        item.slang.toLowerCase().includes(query) || 
        item.meaning.toLowerCase().includes(query)
    );
    
    displaySlangDictionary(filtered);
}

// Click outside modal to close
document.addEventListener('click', function(e) {
    const modal = document.getElementById('slangDictionaryModal');
    if (e.target === modal) {
        toggleSlangDictionary();
    }
});
