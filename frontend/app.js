/**
 * AgentIA v2 - Code Standardizer
 * Frontend simplifie
 */

const state = {
    jobId: null,
    files: [],
    analysis: null,
    processed: null,
    selectedFile: null,
    currentTab: 'code'
};

const $ = sel => document.querySelector(sel);
const $$ = sel => document.querySelectorAll(sel);

const el = {
    llmStatus: $('#llm-status'),
    pageTitle: $('#page-title'),
    pageDescription: $('#page-description'),
    
    // Import section
    importSection: $('#import-section'),
    importLocal: $('#import-local'),
    importGithub: $('#import-github'),
    
    uploadZone: $('#upload-zone'),
    filesContent: $('#files-content'),
    filesCount: $('#files-count'),
    fileInput: $('#file-input'),
    cardUpload: $('#card-upload'),
    filesList: $('#files-list'),
    btnClear: $('#btn-clear'),
    
    // GitHub
    githubUrl: $('#github-url'),
    githubToken: $('#github-token'),
    githubBranch: $('#github-branch'),
    btnGithubImport: $('#btn-github-import'),
    
    cardOptions: $('#card-options'),
    optPep8: $('#opt-pep8'),
    optDocstrings: $('#opt-docstrings'),
    optMarkdown: $('#opt-markdown'),
    optProfiling: $('#opt-profiling'),
    optGraph: $('#opt-graph'),
    
    // AI Configuration
    aiConfigSection: $('#ai-config-section'),
    aiTypeOllama: $('input[name="ai-type"][value="ollama"]'),
    aiTypeApi: $('input[name="ai-type"][value="api"]'),
    ollamaConfig: $('#ollama-config'),
    apiConfig: $('#api-config'),
    ollamaModel: $('#ollama-model'),
    apiUrl: $('#api-url'),
    apiKey: $('#api-key'),
    apiModel: $('#api-model'),
    
    btnProcess: $('#btn-process'),
    
    cardStats: $('#card-stats'),
    scoreValue: $('#score-value'),
    scoreCircle: $('#score-circle'),
    scoreStatus: $('#score-status'),
    statFiles: $('#stat-files'),
    statFunctions: $('#stat-functions'),
    statClasses: $('#stat-classes'),
    statIssues: $('#stat-issues'),
    
    cardPreview: $('#card-preview'),
    fileSelector: $('#file-selector'),
    previewCode: $('#preview-code'),
    previewReport: $('#preview-report'),
    previewGraph: $('#preview-graph'),
    codeOriginal: $('#code-original'),
    codeCorrected: $('#code-corrected'),
    scoreBefore: $('#score-before'),
    scoreAfter: $('#score-after'),
    iframeReport: $('#iframe-report'),
    iframeGraph: $('#iframe-graph'),
    
    cardResults: $('#card-results'),
    resultFiles: $('#result-files'),
    resultImprovement: $('#result-improvement'),
    btnDownload: $('#btn-download'),
    btnReport: $('#btn-report'),
    btnProjectGraph: $('#btn-project-graph'),
    btnRestart: $('#btn-restart'),
    btnDownloadFile: $('#btn-download-file'),
    
    overlay: $('#overlay'),
    loaderText: $('#loader-text'),
    loaderHint: $('#loader-hint'),
    modal: $('#modal'),
    modalClose: $('#modal-close'),
    modalIframe: $('#modal-iframe')
};

// API
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
    
    async github(url, token, branch) {
        const res = await fetch('/api/github', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, token, branch })
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Erreur lors de l\'import GitHub');
        }
        return res.json();
    },
    
    async analyze(jobId) {
        const res = await fetch('/api/analyze/' + jobId);
        return res.json();
    },
    
    async process(jobId, options) {
        const params = new URLSearchParams({
            pep8: options.pep8,
            docstrings: options.docstrings,
            generate_markdown: options.generate_markdown,
            profiling: options.profiling,
            dependency_graph: options.graph,
            ai_type: options.aiType,
            ollama_model: options.ollamaModel,
            api_url: options.apiUrl,
            api_key: options.apiKey,
            api_model: options.apiModel
        });
        const res = await fetch('/api/process/' + jobId + '?' + params, { method: 'POST' });
        return res.json();
    },
    
    async preview(jobId, filename) {
        const res = await fetch('/api/preview/' + jobId + '/' + filename);
        return res.json();
    },
    
    reportUrl: (jobId, filename) => filename ? '/api/report/' + jobId + '/' + filename : '/api/report/' + jobId,
    graphUrl: (jobId, filename) => filename ? '/api/graph/' + jobId + '/' + filename : '/api/graph/' + jobId,
    downloadUrl: jobId => '/api/download/' + jobId,
    downloadFile: (jobId, filename) => '/api/download/' + jobId + '/' + filename
};

// Utils

function updateScoreRing(score) {
    el.scoreCircle.style.strokeDashoffset = 283 - (score / 100) * 283;
}

function getScoreStatus(score) {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Acceptable';
    return 'A améliorer';
}

function updateNav(step) {
    $$('.nav-item').forEach((item, i) => {
        item.classList.remove('active', 'completed');
        if (i + 1 === step) item.classList.add('active');
        else if (i + 1 < step) item.classList.add('completed');
    });
}

function showLoading(text, hint) {
    el.loaderText.textContent = text || 'Chargement...';
    el.loaderHint.textContent = hint || '';
    el.overlay.hidden = false;
}

function hideLoading() {
    el.overlay.hidden = true;
}

function renderFilesList(files, processed) {
    const processedMap = new Map();
    if (processed) processed.forEach(p => processedMap.set(p.file, p));
    
    el.filesList.innerHTML = files.map((file, i) => {
        const p = processedMap.get(file.file || file);
        const filename = file.file || file;
        
        let scoreHtml = '';
        if (p && p.score_before !== undefined) {
            const cls = (p.score_after - p.score_before) > 0 ? 'improved' : '';
            scoreHtml = '<div class="file-score ' + cls + '">' + p.score_before + ' → ' + p.score_after + '</div>';
        } else if (file.score) {
            scoreHtml = '<div class="file-score">' + file.score + '</div>';
        }
        
        return '<div class="file-item ' + (i === 0 ? 'active' : '') + '" data-file="' + filename + '">' +
            '<div class="file-icon">📄</div>' +
            '<div class="file-info"><div class="file-name">' + filename + '</div></div>' +
            scoreHtml + '</div>';
    }).join('');
    
    el.filesList.querySelectorAll('.file-item').forEach(item => {
        item.addEventListener('click', () => selectFile(item.dataset.file));
    });
    
    el.fileSelector.innerHTML = files.map(f => {
        const fn = f.file || f;
        return '<option value="' + fn + '">' + fn + '</option>';
    }).join('');
}

function renderStats(data) {
    let funcs = 0, classes = 0, issues = 0;
    data.files.forEach(f => {
        funcs += f.functions.length;
        classes += f.classes.length;
        issues += f.issues;
    });
    
    el.scoreValue.textContent = data.average_score;
    updateScoreRing(data.average_score);
    el.scoreStatus.textContent = getScoreStatus(data.average_score);
    el.statFiles.textContent = data.total_files;
    el.statFunctions.textContent = funcs;
    el.statClasses.textContent = classes;
    el.statIssues.textContent = issues;
}

function renderResults(data) {
    const count = data.processed.length;
    let totalImp = 0;
    data.processed.forEach(p => {
        if (p.score_before !== undefined) totalImp += (p.score_after - p.score_before);
    });
    
    el.resultFiles.textContent = count;
    el.resultImprovement.textContent = (totalImp >= 0 ? '+' : '') + Math.round(totalImp / count);
}

async function selectFile(filename) {
    state.selectedFile = filename;
    
    // Mise à jour visuelle liste
    el.filesList.querySelectorAll('.file-item').forEach(item => {
        item.classList.toggle('active', item.dataset.file === filename);
    });
    el.fileSelector.value = filename;
    
    // Configuration des boutons d'action (Nouveau)
    el.btnDownloadFile.onclick = () => {
        window.location.href = api.downloadFile(state.jobId, filename);
    };
    
    // Chargement contenu
    try {
        const preview = await api.preview(state.jobId, filename);
        
        el.codeOriginal.textContent = preview.original || '';
        el.codeCorrected.textContent = preview.corrected || '(En attente)';

        if (preview.score_before !== null) el.scoreBefore.textContent = preview.score_before;
        if (preview.score_after !== null) el.scoreAfter.textContent = preview.score_after;
        
        el.iframeReport.src = api.reportUrl(state.jobId, filename);
        el.iframeGraph.src = api.graphUrl(state.jobId, filename);
    } catch (err) {
        console.error('Preview error:', err);
    }
}
function switchTab(tab) {
    state.currentTab = tab;
    
    $$('.preview-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    
    el.previewCode.hidden = tab !== 'code';
    el.previewReport.hidden = tab !== 'report';
    el.previewGraph.hidden = tab !== 'graph';
}

function switchImportSource(source) {
    // Afficher le bon panneau de détails
    el.importLocal.hidden = source !== 'local';
    el.importGithub.hidden = source !== 'github';
}

function showFilesContent(count) {
    // Cacher la section d'import et montrer la liste des fichiers
    el.importSection.hidden = true;
    el.filesContent.hidden = false;
    el.filesCount.textContent = count + ' fichier' + (count > 1 ? 's' : '');
}

function showImportSection() {
    // Montrer la section d'import et cacher la liste des fichiers
    el.importSection.hidden = false;
    el.filesContent.hidden = true;
    // Remettre sur local par défaut
    $('input[name="import-source"][value="local"]').checked = true;
    switchImportSource('local');
}

async function handleGithubImport() {
    const url = el.githubUrl.value.trim();
    const token = el.githubToken.value.trim();
    const branch = el.githubBranch.value.trim() || 'main';
    
    if (!url) {
        alert('Veuillez entrer l\'URL du repository GitHub');
        return;
    }
    
    // Validation basique de l'URL
    if (!url.includes('github.com') && !url.includes('/')) {
        alert('URL invalide. Utilisez le format: https://github.com/user/repo');
        return;
    }
    
    try {
        el.btnGithubImport.disabled = true;
        showLoading('Clonage du repository...', url);
        
        const result = await api.github(url, token, branch);
        state.jobId = result.job_id;
        
        showLoading('Analyse en cours...', result.count + ' fichier(s) Python');
        const analysis = await api.analyze(state.jobId);
        state.analysis = analysis;
        
        renderFilesList(analysis.files);
        renderStats(analysis);
        
        // Afficher la liste des fichiers
        showFilesContent(analysis.total_files);
        
        // Activer le bouton de traitement
        el.btnProcess.disabled = false;
        
        el.pageTitle.textContent = 'Repository importé';
        el.pageDescription.textContent = result.repo + ' • ' + analysis.total_files + ' fichier(s) • Score: ' + analysis.average_score + '/100';
        updateNav(2);
        
        if (analysis.files.length > 0) selectFile(analysis.files[0].file);
    } catch (err) {
        console.error(err);
        alert('Erreur: ' + err.message);
    } finally {
        el.btnGithubImport.disabled = false;
        hideLoading();
    }
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
    
    // Revenir à la section d'import
    showImportSection();
    
    // Réinitialiser les listes et contenus
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
    el.resultFiles.textContent = '0';
    el.resultImprovement.textContent = '+0';
    el.fileInput.value = '';
    
    // Réinitialiser les options de traitement
    el.optPep8.checked = true;
    el.optDocstrings.checked = true;
    el.optMarkdown.checked = false;
    el.optProfiling.checked = false;
    el.optGraph.checked = true;
    
    // Réinitialiser la config IA (Ollama par défaut)
    $('input[name="ai-type"][value="ollama"]').checked = true;
    el.ollamaConfig.hidden = false;
    el.apiConfig.hidden = true;
    
    // Réinitialiser les champs GitHub
    el.githubUrl.value = '';
    el.githubToken.value = '';
    el.githubBranch.value = 'main';
    
    // Réinitialiser les iframes
    el.iframeReport.src = '';
    el.iframeGraph.src = '';
    
    // Désactiver les boutons de résultats
    el.btnDownload.disabled = true;
    el.btnReport.disabled = true;
    el.btnProjectGraph.disabled = true;
    el.btnProcess.disabled = true;
    
    el.pageTitle.textContent = 'Importer vos fichiers';
    el.pageDescription.textContent = 'Glissez-déposez vos fichiers Python ou un ZIP';
    updateNav(1);
    switchTab('code');
}

async function handleFiles(fileList) {
    const files = Array.from(fileList).filter(f => f.name.endsWith('.py') || f.name.endsWith('.zip'));
    
    if (!files.length) {
        alert('Sélectionnez des fichiers Python (.py) ou un ZIP.');
        return;
    }
    
    try {
        showLoading('Upload des fichiers...', 'Préparation');
        const result = await api.upload(files);
        state.jobId = result.job_id;
        
        showLoading('Analyse en cours...', result.count + ' fichier(s)');
        const analysis = await api.analyze(state.jobId);
        state.analysis = analysis;
        
        renderFilesList(analysis.files);
        renderStats(analysis);
        
        // Afficher la liste des fichiers
        showFilesContent(analysis.total_files);
        
        // Activer le bouton de traitement
        el.btnProcess.disabled = false;
        
        el.pageTitle.textContent = 'Analyse complète';
        el.pageDescription.textContent = analysis.total_files + ' fichier(s) • Score: ' + analysis.average_score + '/100';
        updateNav(2);
        
        if (analysis.files.length > 0) selectFile(analysis.files[0].file);
    } catch (err) {
        console.error(err);
        alert('Erreur: ' + err.message);
    } finally {
        hideLoading();
    }
}

async function handleProcess() {
    if (!state.jobId) return;
    
    const options = {
        pep8: el.optPep8.checked,
        docstrings: el.optDocstrings.checked,
        generate_markdown: el.optMarkdown.checked,
        profiling: el.optProfiling.checked,
        graph: el.optGraph.checked,
        aiType: $('input[name="ai-type"]:checked').value,
        ollamaModel: el.ollamaModel.value,
        apiUrl: el.apiUrl.value,
        apiKey: el.apiKey.value,
        apiModel: el.apiModel.value
    };
    
    const hints = [];
    if (options.pep8) hints.push('PEP8');
    if (options.docstrings) hints.push('Docstrings');
    if (options.generate_markdown) hints.push('Documentation.md');
    if (options.profiling) hints.push('Profiling');
    if (options.graph) hints.push('Graphes');
    
    try {
        el.btnProcess.disabled = true;
        showLoading('Traitement en cours...', hints.join(' + '));
        
        const result = await api.process(state.jobId, options);
        state.processed = result;
        
        renderFilesList(state.analysis.files, result.processed);
        renderResults(result);
        
        // Activer les boutons de résultats
        el.btnDownload.disabled = false;
        el.btnReport.disabled = false;
        el.btnProjectGraph.disabled = false;
        
        el.pageTitle.textContent = 'Traitement terminé';
        el.pageDescription.textContent = result.count + ' fichier(s) traité(s)';
        updateNav(4);
        
        if (state.selectedFile) selectFile(state.selectedFile);
    } catch (err) {
        console.error(err);
        alert('Erreur: ' + err.message);
    } finally {
        el.btnProcess.disabled = false;
        hideLoading();
    }
}

async function init() {
    try {
        const status = await api.status();
        el.llmStatus.classList.add('connected');
        el.llmStatus.querySelector('.status-text').textContent = 
            status.llm.backend === 'api' ? 'API: ' + status.llm.model : 'Ollama: ' + status.llm.model;
    } catch {
        el.llmStatus.querySelector('.status-text').textContent = 'Déconnecté';
    }
    
    // Upload zone
    el.uploadZone.addEventListener('click', () => el.fileInput.click());
    el.uploadZone.addEventListener('dragover', e => { e.preventDefault(); el.uploadZone.classList.add('dragover'); });
    el.uploadZone.addEventListener('dragleave', () => el.uploadZone.classList.remove('dragover'));
    el.uploadZone.addEventListener('drop', e => {
        e.preventDefault();
        el.uploadZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    el.fileInput.addEventListener('change', e => handleFiles(e.target.files));
    
    // Import source radio buttons (Local / GitHub)
    $$('input[name="import-source"]').forEach(radio => {
        radio.addEventListener('change', () => switchImportSource(radio.value));
    });
    
    // GitHub import
    el.btnGithubImport.addEventListener('click', handleGithubImport);
    
    // AI Configuration
    $$('input[name="ai-type"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const isOllama = radio.value === 'ollama';
            el.ollamaConfig.hidden = !isOllama;
            el.apiConfig.hidden = isOllama;
        });
    });
    
    // Buttons
    el.btnClear.addEventListener('click', reset);
    el.btnProcess.addEventListener('click', handleProcess);
    el.btnDownload.addEventListener('click', () => { if (state.jobId) window.location.href = api.downloadUrl(state.jobId); });
    el.btnReport.addEventListener('click', () => { if (state.jobId) openModal(api.reportUrl(state.jobId)); });
    el.btnProjectGraph.addEventListener('click', () => { if (state.jobId) openModal(api.graphUrl(state.jobId)); });
    el.btnRestart.addEventListener('click', reset);
    
    // Selector & Tabs
    el.fileSelector.addEventListener('change', e => selectFile(e.target.value));
    $$('.preview-tab').forEach(tab => tab.addEventListener('click', () => switchTab(tab.dataset.tab)));
    
    // Modal
    el.modalClose.addEventListener('click', closeModal);
    $('.modal-backdrop').addEventListener('click', closeModal);
    
    updateNav(1);
}

document.addEventListener('DOMContentLoaded', init);