/**
 * AgentIA v2 - Code Standardizer
 * Frontend Application - Improved
 */

// ============================================
// State
// ============================================

const state = {
    jobId: null,
    files: [],
    analysis: null,
    processed: null,
    selectedFile: null
};

// ============================================
// DOM
// ============================================

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const el = {
    // Status
    llmStatus: $('#llm-status'),
    
    // Header
    pageTitle: $('#page-title'),
    pageDescription: $('#page-description'),
    
    // Nav
    navFilesCount: $('#nav-files-count'),
    
    // Upload
    uploadZone: $('#upload-zone'),
    fileInput: $('#file-input'),
    cardUpload: $('#card-upload'),
    cardFiles: $('#card-files'),
    filesList: $('#files-list'),
    btnClear: $('#btn-clear'),
    
    // Options
    cardOptions: $('#card-options'),
    optDocstrings: $('#opt-docstrings'),
    btnProcess: $('#btn-process'),
    
    // Stats
    cardStats: $('#card-stats'),
    scoreValue: $('#score-value'),
    scoreCircle: $('#score-circle'),
    scoreStatus: $('#score-status'),
    statFiles: $('#stat-files'),
    statFunctions: $('#stat-functions'),
    statClasses: $('#stat-classes'),
    statIssues: $('#stat-issues'),
    
    // Preview
    cardPreview: $('#card-preview'),
    fileSelector: $('#file-selector'),
    previewCompare: $('#preview-compare'),
    previewReport: $('#preview-report'),
    codeOriginal: $('#code-original'),
    codeCorrected: $('#code-corrected'),
    scoreBefore: $('#score-before'),
    scoreAfter: $('#score-after'),
    reportIframe: $('#report-iframe'),
    
    // Results
    cardResults: $('#card-results'),
    resultFiles: $('#result-files'),
    resultImprovement: $('#result-improvement'),
    resultDocstrings: $('#result-docstrings'),
    btnDownload: $('#btn-download'),
    btnReport: $('#btn-report'),
    btnRestart: $('#btn-restart'),
    
    // Overlay & Modal
    overlay: $('#overlay'),
    loaderText: $('#loader-text'),
    loaderHint: $('#loader-hint'),
    modal: $('#modal'),
    modalClose: $('#modal-close'),
    modalIframe: $('#modal-iframe')
};

// ============================================
// API
// ============================================

const api = {
    async status() {
        const res = await fetch('/api/status');
        return res.json();
    },
    
    async upload(files) {
        const formData = new FormData();
        files.forEach(f => formData.append('files', f));
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        return res.json();
    },
    
    async analyze(jobId) {
        const res = await fetch(`/api/analyze/${jobId}`);
        return res.json();
    },
    
    async process(jobId, addDocstrings) {
        const res = await fetch(`/api/process/${jobId}?add_docstrings=${addDocstrings}`, { method: 'POST' });
        return res.json();
    },
    
    async preview(jobId, filename) {
        const res = await fetch(`/api/preview/${jobId}/${filename}`);
        return res.json();
    },
    
    reportUrl(jobId, filename = null) {
        return filename 
            ? `/api/report/${jobId}/${filename}`
            : `/api/report/${jobId}`;
    },
    
    downloadUrl(jobId) {
        return `/api/download/${jobId}`;
    }
};

// ============================================
// Utilities
// ============================================

function truncateCode(code, maxLines = 25) {
    if (!code) return '';
    const lines = code.split('\n');
    if (lines.length <= maxLines) return code;
    
    const start = lines.slice(0, 12).join('\n');
    const end = lines.slice(-10).join('\n');
    const hidden = lines.length - 22;
    
    return `${start}\n\n    /* ... ${hidden} lignes masquées ... */\n\n${end}`;
}

function updateScoreRing(score) {
    const circumference = 283; // 2 * PI * 45
    const offset = circumference - (score / 100) * circumference;
    el.scoreCircle.style.strokeDashoffset = offset;
}

function getScoreStatus(score) {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Acceptable';
    return 'À améliorer';
}

function updateNav(step, completed = false) {
    $$('.nav-item').forEach((item, index) => {
        item.classList.remove('active', 'completed');
        if (index + 1 === step) {
            item.classList.add('active');
        } else if (index + 1 < step || completed) {
            item.classList.add('completed');
        }
    });
}

// ============================================
// UI Functions
// ============================================

function showLoading(text, hint = '') {
    el.loaderText.textContent = text;
    el.loaderHint.textContent = hint;
    el.overlay.hidden = false;
}

function hideLoading() {
    el.overlay.hidden = true;
}

function updateHeader(title, description) {
    el.pageTitle.textContent = title;
    el.pageDescription.textContent = description;
}

function renderFilesList(files, processed = null) {
    const processedMap = new Map();
    if (processed) {
        processed.forEach(p => processedMap.set(p.file, p));
    }
    
    el.filesList.innerHTML = files.map((file, index) => {
        const p = processedMap.get(file.file || file);
        const filename = file.file || file;
        const score = file.score || 0;
        
        let scoreHtml = '';
        if (p && p.score_before !== undefined) {
            const improvement = p.score_after - p.score_before;
            const impClass = improvement > 0 ? 'improved' : '';
            scoreHtml = `
                <div class="file-score ${impClass}">
                    <span>${p.score_before}</span>
                    <span class="score-arrow">→</span>
                    <span>${p.score_after}</span>
                </div>
            `;
        } else if (score) {
            scoreHtml = `<div class="file-score">${score}</div>`;
        }
        
        return `
            <div class="file-item ${index === 0 ? 'active' : ''}" data-file="${filename}">
                <div class="file-icon">📄</div>
                <div class="file-info">
                    <div class="file-name">${filename}</div>
                    <div class="file-meta">${file.lines || ''} ${file.lines ? 'lignes' : ''}</div>
                </div>
                ${scoreHtml}
            </div>
        `;
    }).join('');
    
    // Add click handlers
    el.filesList.querySelectorAll('.file-item').forEach(item => {
        item.addEventListener('click', () => selectFile(item.dataset.file));
    });
    
    // Update selector
    el.fileSelector.innerHTML = files.map(f => {
        const filename = f.file || f;
        return `<option value="${filename}">${filename}</option>`;
    }).join('');
}

function renderStats(data) {
    let totalFunctions = 0;
    let totalClasses = 0;
    let totalIssues = 0;
    
    data.files.forEach(f => {
        totalFunctions += f.functions.length;
        totalClasses += f.classes.length;
        totalIssues += f.issues;
    });
    
    el.scoreValue.textContent = data.average_score;
    updateScoreRing(data.average_score);
    el.scoreStatus.textContent = getScoreStatus(data.average_score);
    
    el.statFiles.textContent = data.total_files;
    el.statFunctions.textContent = totalFunctions;
    el.statClasses.textContent = totalClasses;
    el.statIssues.textContent = totalIssues;
}

function renderResults(data) {
    const filesCount = data.processed.length;
    const docstringsCount = data.processed.filter(p => p.has_docstrings).length;
    
    // Calculate average improvement
    let totalImprovement = 0;
    data.processed.forEach(p => {
        if (p.score_before !== undefined && p.score_after !== undefined) {
            totalImprovement += (p.score_after - p.score_before);
        }
    });
    const avgImprovement = Math.round(totalImprovement / filesCount);
    
    el.resultFiles.textContent = filesCount;
    el.resultImprovement.textContent = avgImprovement >= 0 ? `+${avgImprovement}` : avgImprovement;
    el.resultDocstrings.textContent = docstringsCount;
}

async function selectFile(filename) {
    state.selectedFile = filename;
    
    // Update active state
    el.filesList.querySelectorAll('.file-item').forEach(item => {
        item.classList.toggle('active', item.dataset.file === filename);
    });
    
    // Update selector
    el.fileSelector.value = filename;
    
    // Load preview
    try {
        const preview = await api.preview(state.jobId, filename);
        
        // Truncate code for preview
        el.codeOriginal.textContent = truncateCode(preview.original, 25);
        el.codeCorrected.textContent = truncateCode(preview.corrected, 25) || '(En attente de traitement)';
        
        // Update scores if processed
        if (state.processed) {
            const fileData = state.processed.processed.find(p => p.file === filename);
            if (fileData && fileData.score_before !== undefined) {
                el.scoreBefore.textContent = fileData.score_before;
                el.scoreAfter.textContent = fileData.score_after;
            }
        } else if (state.analysis) {
            const fileData = state.analysis.files.find(f => f.file === filename);
            if (fileData) {
                el.scoreBefore.textContent = fileData.score;
                el.scoreAfter.textContent = '--';
            }
        }
        
        // Load report if available
        if (preview.corrected) {
            el.reportIframe.src = api.reportUrl(state.jobId, filename);
        }
        
    } catch (err) {
        console.error('Preview error:', err);
    }
}

function switchPreviewTab(tab) {
    $$('.preview-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tab);
    });
    
    el.previewCompare.hidden = tab !== 'compare';
    el.previewReport.hidden = tab !== 'report';
}

function openModal(url) {
    el.modalIframe.src = url;
    el.modal.hidden = false;
}

function closeModal() {
    el.modal.hidden = true;
    el.modalIframe.src = '';
}

function reset() {
    state.jobId = null;
    state.files = [];
    state.analysis = null;
    state.processed = null;
    state.selectedFile = null;
    
    // Reset UI
    el.cardFiles.hidden = true;
    el.cardOptions.hidden = true;
    el.cardPreview.hidden = true;
    el.cardResults.hidden = true;
    el.cardUpload.hidden = false;
    
    el.filesList.innerHTML = '';
    el.fileSelector.innerHTML = '';
    el.codeOriginal.textContent = '';
    el.codeCorrected.textContent = '';
    el.scoreBefore.textContent = '--';
    el.scoreAfter.textContent = '--';
    el.scoreValue.textContent = '--';
    el.scoreStatus.textContent = 'En attente';
    updateScoreRing(0);
    
    el.statFiles.textContent = '0';
    el.statFunctions.textContent = '0';
    el.statClasses.textContent = '0';
    el.statIssues.textContent = '0';
    
    el.navFilesCount.textContent = '';
    el.fileInput.value = '';
    
    updateHeader('Importer vos fichiers', 'Glissez-déposez vos fichiers Python ou un ZIP');
    updateNav(1);
}

// ============================================
// Handlers
// ============================================

async function handleFiles(fileList) {
    const files = Array.from(fileList).filter(f => 
        f.name.endsWith('.py') || f.name.endsWith('.zip')
    );
    
    if (files.length === 0) {
        alert('Sélectionnez des fichiers Python (.py) ou un ZIP.');
        return;
    }
    
    try {
        showLoading('Upload des fichiers...', 'Analyse en préparation');
        
        const result = await api.upload(files);
        state.jobId = result.job_id;
        state.files = result.files;
        
        el.navFilesCount.textContent = result.count;
        
        showLoading('Analyse en cours...', `${result.count} fichier(s) détecté(s)`);
        
        const analysis = await api.analyze(state.jobId);
        state.analysis = analysis;
        
        // Update UI
        renderFilesList(analysis.files);
        renderStats(analysis);
        
        el.cardUpload.hidden = true;
        el.cardFiles.hidden = false;
        el.cardOptions.hidden = false;
        el.cardPreview.hidden = false;
        
        updateHeader('Analyse complète', `${analysis.total_files} fichier(s) analysé(s) - Score moyen: ${analysis.average_score}/100`);
        updateNav(2);
        
        // Select first file
        if (analysis.files.length > 0) {
            selectFile(analysis.files[0].file);
        }
        
    } catch (err) {
        console.error(err);
        alert('Erreur: ' + err.message);
    } finally {
        hideLoading();
    }
}

async function handleProcess() {
    if (!state.jobId) return;
    
    const addDocstrings = el.optDocstrings.checked;
    
    try {
        el.btnProcess.disabled = true;
        
        const hint = addDocstrings 
            ? 'Correction PEP8 + Génération des docstrings IA'
            : 'Correction PEP8';
        showLoading('Traitement en cours...', hint);
        
        const result = await api.process(state.jobId, addDocstrings);
        state.processed = result;
        
        // Update UI
        renderFilesList(state.analysis.files, result.processed);
        renderResults(result);
        
        el.cardOptions.hidden = true;
        el.cardResults.hidden = false;
        
        updateHeader('Traitement terminé', `${result.count} fichier(s) traité(s) avec succès`);
        updateNav(4, true);
        
        // Refresh preview
        if (state.selectedFile) {
            selectFile(state.selectedFile);
        }
        
    } catch (err) {
        console.error(err);
        alert('Erreur: ' + err.message);
    } finally {
        el.btnProcess.disabled = false;
        hideLoading();
    }
}

// ============================================
// Init
// ============================================

async function init() {
    // Check API status
    try {
        const status = await api.status();
        el.llmStatus.classList.add('connected');
        
        if (status.llm.backend === 'api') {
            el.llmStatus.classList.add('api');
            el.llmStatus.querySelector('.status-text').textContent = `API: ${status.llm.model}`;
        } else {
            el.llmStatus.querySelector('.status-text').textContent = `Ollama: ${status.llm.model}`;
        }
    } catch (err) {
        el.llmStatus.querySelector('.status-text').textContent = 'Déconnecté';
    }
    
    // Upload events
    el.uploadZone.addEventListener('click', () => el.fileInput.click());
    
    el.uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        el.uploadZone.classList.add('dragover');
    });
    
    el.uploadZone.addEventListener('dragleave', () => {
        el.uploadZone.classList.remove('dragover');
    });
    
    el.uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        el.uploadZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    
    el.fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
    
    // Buttons
    el.btnClear.addEventListener('click', reset);
    el.btnProcess.addEventListener('click', handleProcess);
    
    el.btnDownload.addEventListener('click', () => {
        if (state.jobId) {
            window.location.href = api.downloadUrl(state.jobId);
        }
    });
    
    el.btnReport.addEventListener('click', () => {
        if (state.jobId) {
            openModal(api.reportUrl(state.jobId));
        }
    });
    
    el.btnRestart.addEventListener('click', reset);
    
    // File selector
    el.fileSelector.addEventListener('change', (e) => {
        selectFile(e.target.value);
    });
    
    // Preview tabs
    $$('.preview-tab').forEach(tab => {
        tab.addEventListener('click', () => switchPreviewTab(tab.dataset.tab));
    });
    
    // Modal
    el.modalClose.addEventListener('click', closeModal);
    $('.modal-backdrop').addEventListener('click', closeModal);
    
    // Initialize nav
    updateNav(1);
}

// Start
document.addEventListener('DOMContentLoaded', init);