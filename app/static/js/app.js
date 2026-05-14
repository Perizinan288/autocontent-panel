const API = '';
let currentClipSource = '';

// ---- Navigation ----
function showPage(page) {
    document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');
    document.querySelector(`[data-page="${page}"]`).classList.add('active');

    if (page === 'dashboard') loadDashboard();
    if (page === 'contents') loadContents();
    if (page === 'schedule') loadSchedules();
    if (page === 'upload') loadUploadOptions();
    if (page === 'templates') loadTemplates();
    if (page === 'platforms') loadPlatformStatus();

    if (window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('open');
    }
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// ---- Toast ----
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ---- Loading ----
function showLoading(text = 'Loading...') {
    document.getElementById('loadingText').textContent = text;
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

// ---- Modals ----
function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }
function openCreateModal() { openModal('createModal'); }
function openScheduleModal() {
    loadScheduleOptions();
    openModal('scheduleModal');
}
function openTemplateModal() { openModal('templateModal'); }

// ---- API Calls ----
async function apiCall(url, method = 'GET', data = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (data) opts.body = JSON.stringify(data);
    const res = await fetch(API + url, opts);
    return res.json();
}

// ---- Dashboard ----
async function loadDashboard() {
    try {
        const stats = await apiCall('/api/content/stats/summary');
        document.getElementById('stat-total').textContent = stats.total_contents || 0;
        document.getElementById('stat-published').textContent = stats.published || 0;
        document.getElementById('stat-scheduled').textContent = stats.scheduled || 0;
        document.getElementById('stat-draft').textContent = stats.drafts || 0;
    } catch (e) {
        // Stats endpoint may fail if no data yet
    }

    try {
        const contents = await apiCall('/api/content?limit=5');
        const tbody = document.getElementById('recentContentsTable');
        if (contents.items && contents.items.length > 0) {
            tbody.innerHTML = contents.items.map(c => `
                <tr>
                    <td>${escapeHtml(c.title)}</td>
                    <td><span class="platform-badge platform-${c.platform}">${c.platform}</span></td>
                    <td><span class="badge badge-${c.status}">${c.status}</span></td>
                    <td>${formatDate(c.created_at)}</td>
                    <td>
                        <div class="action-btns">
                            <button class="action-btn" onclick="viewContent(${c.id})" title="Lihat">&#128065;</button>
                            <button class="action-btn delete" onclick="deleteContent(${c.id})" title="Hapus">&#128465;</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-secondary);padding:40px;">Belum ada konten. Klik "Generate Konten Baru" untuk mulai!</td></tr>';
        }
    } catch (e) {
        // Ignore
    }

    loadPlatformStatus();
}

// ---- Generate Content ----
async function generateContent(save = false) {
    const niche = document.getElementById('genNiche').value.trim();
    if (!niche) { showToast('Masukkan niche/topik dulu!', 'error'); return; }

    const data = {
        niche: niche,
        platform: document.getElementById('genPlatform').value,
        content_type: document.getElementById('genType').value,
        language: document.getElementById('genLang').value,
        tone: document.getElementById('genTone').value,
        count: parseInt(document.getElementById('genCount').value),
    };

    showLoading('Generating konten dengan AI...');
    try {
        const url = save ? '/api/generate/content/save' : '/api/generate/content';
        const result = await apiCall(url, 'POST', data);

        document.getElementById('generateResults').style.display = 'block';
        const area = document.getElementById('resultsArea');
        area.innerHTML = '';

        (result.items || []).forEach((item, i) => {
            const div = document.createElement('div');
            div.className = 'result-item';
            div.innerHTML = `
                <h4>${i + 1}. ${escapeHtml(item.title || '')}</h4>
                <p><strong>Hook:</strong> ${escapeHtml(item.hook || '')}</p>
                <p><strong>Caption:</strong> ${escapeHtml(item.caption || '')}</p>
                <p><strong>Script:</strong> ${escapeHtml(item.script || '')}</p>
                <p><strong>Hashtags:</strong> ${escapeHtml(item.hashtags || '')}</p>
                <p><strong>CTA:</strong> ${escapeHtml(item.cta || '')}</p>
                <div class="meta">
                    ${save ? '<span class="badge badge-published">Tersimpan</span>' : ''}
                    <span class="platform-badge platform-${data.platform}">${data.platform}</span>
                </div>
            `;
            area.appendChild(div);
        });

        showToast(save ? 'Konten di-generate dan disimpan!' : 'Konten berhasil di-generate!', 'success');
    } catch (e) {
        showToast('Gagal generate konten: ' + e.message, 'error');
    }
    hideLoading();
}

function clearResults() {
    document.getElementById('resultsArea').innerHTML = '';
    document.getElementById('generateResults').style.display = 'none';
}

// ---- Contents ----
async function loadContents() {
    const status = document.getElementById('filterStatus')?.value || '';
    const platform = document.getElementById('filterPlatform')?.value || '';
    let url = '/api/content?limit=50';
    if (status) url += '&status=' + status;
    if (platform) url += '&platform=' + platform;

    try {
        const result = await apiCall(url);
        const grid = document.getElementById('contentsList');

        if (result.items && result.items.length > 0) {
            grid.innerHTML = result.items.map(c => `
                <div class="content-card">
                    <div class="content-card-header">
                        <div class="content-card-title">${escapeHtml(c.title)}</div>
                        <span class="badge badge-${c.status}">${c.status}</span>
                    </div>
                    <div class="content-card-body">
                        ${escapeHtml((c.caption || c.description || '').substring(0, 120))}${(c.caption || c.description || '').length > 120 ? '...' : ''}
                    </div>
                    <div class="content-card-footer">
                        <span class="platform-badge platform-${c.platform}">${c.platform}</span>
                        <button class="btn btn-sm btn-secondary" onclick="viewContent(${c.id})">&#128065; Detail</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteContent(${c.id})">&#128465;</button>
                    </div>
                </div>
            `).join('');
        } else {
            grid.innerHTML = '<div class="empty-state"><div class="icon">&#128196;</div><h3>Belum Ada Konten</h3><p>Generate konten baru atau tambah manual</p></div>';
        }
    } catch (e) {
        showToast('Gagal memuat konten', 'error');
    }
}

async function createContent() {
    const data = {
        title: document.getElementById('createTitle').value,
        description: document.getElementById('createDesc').value,
        caption: document.getElementById('createCaption').value,
        hashtags: document.getElementById('createHashtags').value,
        script: document.getElementById('createScript').value,
        platform: document.getElementById('createPlatform').value,
        content_type: document.getElementById('createType').value,
    };

    if (!data.title) { showToast('Judul wajib diisi!', 'error'); return; }

    try {
        await apiCall('/api/content', 'POST', data);
        closeModal('createModal');
        showToast('Konten berhasil ditambah!', 'success');
        loadContents();
        loadDashboard();
    } catch (e) {
        showToast('Gagal membuat konten', 'error');
    }
}

async function viewContent(id) {
    try {
        const c = await apiCall('/api/content/' + id);
        const modal = document.getElementById('createModal');
        document.getElementById('createTitle').value = c.title || '';
        document.getElementById('createDesc').value = c.description || '';
        document.getElementById('createCaption').value = c.caption || '';
        document.getElementById('createHashtags').value = c.hashtags || '';
        document.getElementById('createScript').value = c.script || '';
        document.getElementById('createPlatform').value = c.platform || 'all';
        document.getElementById('createType').value = c.content_type || 'video';
        openModal('createModal');
    } catch (e) {
        showToast('Gagal memuat detail konten', 'error');
    }
}

async function deleteContent(id) {
    if (!confirm('Hapus konten ini?')) return;
    try {
        await apiCall('/api/content/' + id, 'DELETE');
        showToast('Konten dihapus!', 'success');
        loadContents();
        loadDashboard();
    } catch (e) {
        showToast('Gagal menghapus konten', 'error');
    }
}

// ---- Video Clipper ----
async function uploadClipSource() {
    const fileInput = document.getElementById('clipSourceFile');
    if (!fileInput.files.length) { showToast('Pilih file video dulu!', 'error'); return; }

    showLoading('Uploading video...');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const res = await fetch(API + '/api/clips/upload', { method: 'POST', body: formData });
        const result = await res.json();

        currentClipSource = result.file_path;
        const info = result.info;

        document.getElementById('videoInfo').style.display = 'block';
        document.getElementById('videoInfoText').innerHTML = `
            <strong>File:</strong> ${result.file_name}<br>
            <strong>Durasi:</strong> ${Math.round(info.duration)} detik (${(info.duration / 60).toFixed(1)} menit)<br>
            <strong>Resolusi:</strong> ${info.width}x${info.height}<br>
            <strong>Ukuran:</strong> ${info.size_mb.toFixed(1)} MB
        `;
        document.getElementById('clipOptions').style.display = 'block';
        showToast('Video berhasil diupload!', 'success');
    } catch (e) {
        showToast('Gagal upload video', 'error');
    }
    hideLoading();
}

async function autoClipVideo() {
    if (!currentClipSource) { showToast('Upload video dulu!', 'error'); return; }

    showLoading('Memotong video menjadi clips...');
    try {
        const result = await apiCall('/api/clips/auto', 'POST', {
            source_file: currentClipSource,
            max_duration: parseFloat(document.getElementById('clipMaxDuration').value),
            min_duration: parseFloat(document.getElementById('clipMinDuration').value),
        });

        document.getElementById('clipResults').style.display = 'block';
        const area = document.getElementById('clipsArea');

        if (result.clips && result.clips.length > 0) {
            area.innerHTML = result.clips.map((clip, i) => `
                <div class="result-item">
                    <h4>Clip #${i + 1}</h4>
                    <p>
                        <strong>Durasi:</strong> ${clip.duration.toFixed(1)} detik |
                        <strong>Start:</strong> ${clip.start_time.toFixed(1)}s |
                        <strong>End:</strong> ${clip.end_time.toFixed(1)}s
                    </p>
                    <p><strong>File:</strong> ${clip.file_name}</p>
                </div>
            `).join('');
            showToast(`${result.clips.length} clips berhasil dibuat!`, 'success');
        } else {
            area.innerHTML = '<div class="empty-state"><p>Tidak ada clips yang dihasilkan.</p></div>';
        }
    } catch (e) {
        showToast('Gagal memotong video', 'error');
    }
    hideLoading();
}

// ---- Upload ----
async function loadUploadOptions() {
    try {
        const result = await apiCall('/api/content?limit=100');
        const select = document.getElementById('uploadContentSelect');
        select.innerHTML = '<option value="">-- Pilih Konten --</option>';
        (result.items || []).forEach(c => {
            select.innerHTML += `<option value="${c.id}">${escapeHtml(c.title)} [${c.status}]</option>`;
        });
    } catch (e) {
        // Ignore
    }
}

async function uploadContent() {
    const contentId = document.getElementById('uploadContentSelect').value;
    const platform = document.getElementById('uploadPlatformSelect').value;

    if (!contentId) { showToast('Pilih konten dulu!', 'error'); return; }

    showLoading('Mengupload konten ke ' + platform + '...');
    try {
        let url = `/api/upload/${platform}/${contentId}`;
        const result = await apiCall(url, 'POST');

        document.getElementById('uploadResultCard').style.display = 'block';
        const area = document.getElementById('uploadResults');
        area.innerHTML = `<div class="result-item">
            <h4>Upload Berhasil!</h4>
            <p>${JSON.stringify(result, null, 2)}</p>
        </div>`;
        showToast('Upload berhasil!', 'success');
    } catch (e) {
        showToast('Gagal upload: ' + e.message, 'error');
    }
    hideLoading();
}

// ---- Schedules ----
async function loadSchedules() {
    try {
        const result = await apiCall('/api/schedules');
        const tbody = document.getElementById('schedulesTable');

        if (result.items && result.items.length > 0) {
            tbody.innerHTML = result.items.map(s => `
                <tr>
                    <td>${escapeHtml(s.content_title || 'Unknown')}</td>
                    <td><span class="platform-badge platform-${s.platform}">${s.platform}</span></td>
                    <td>${formatDate(s.scheduled_at)}</td>
                    <td><span class="badge badge-${s.status}">${s.status}</span></td>
                    <td>
                        <div class="action-btns">
                            ${s.status === 'pending' ? `<button class="action-btn delete" onclick="cancelSchedule(${s.id})" title="Batal">&#10060;</button>` : ''}
                            <button class="action-btn delete" onclick="deleteSchedule(${s.id})" title="Hapus">&#128465;</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-secondary);padding:40px;">Belum ada jadwal posting.</td></tr>';
        }
    } catch (e) {
        // Ignore
    }
}

async function loadScheduleOptions() {
    try {
        const result = await apiCall('/api/content?limit=100');
        const select = document.getElementById('scheduleContentSelect');
        select.innerHTML = '<option value="">-- Pilih Konten --</option>';
        (result.items || []).forEach(c => {
            select.innerHTML += `<option value="${c.id}">${escapeHtml(c.title)}</option>`;
        });
    } catch (e) {
        // Ignore
    }
}

async function createSchedule() {
    const contentId = document.getElementById('scheduleContentSelect').value;
    const platform = document.getElementById('schedulePlatform').value;
    const dateTime = document.getElementById('scheduleDateTime').value;

    if (!contentId || !dateTime) { showToast('Lengkapi semua field!', 'error'); return; }

    try {
        await apiCall('/api/schedules', 'POST', {
            content_id: parseInt(contentId),
            platform: platform,
            scheduled_at: dateTime,
        });
        closeModal('scheduleModal');
        showToast('Jadwal berhasil dibuat!', 'success');
        loadSchedules();
    } catch (e) {
        showToast('Gagal membuat jadwal', 'error');
    }
}

async function cancelSchedule(id) {
    if (!confirm('Batalkan jadwal ini?')) return;
    try {
        await apiCall('/api/schedules/' + id + '/cancel', 'POST');
        showToast('Jadwal dibatalkan', 'success');
        loadSchedules();
    } catch (e) {
        showToast('Gagal membatalkan jadwal', 'error');
    }
}

async function deleteSchedule(id) {
    if (!confirm('Hapus jadwal ini?')) return;
    try {
        await apiCall('/api/schedules/' + id, 'DELETE');
        showToast('Jadwal dihapus', 'success');
        loadSchedules();
    } catch (e) {
        showToast('Gagal menghapus jadwal', 'error');
    }
}

// ---- Platforms ----
async function loadPlatformStatus() {
    try {
        const platforms = await apiCall('/api/upload/platforms');
        const container = document.getElementById('platformStatus');
        if (!container) return;

        const platformNames = { youtube: 'YouTube', instagram: 'Instagram', facebook: 'Facebook', tiktok: 'TikTok' };
        const platformIcons = { youtube: '&#128308;', instagram: '&#128248;', facebook: '&#128309;', tiktok: '&#127926;' };

        container.innerHTML = Object.entries(platforms).map(([key, val]) => `
            <div class="platform-card" style="padding: 16px;">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="font-size:28px;">${platformIcons[key] || '&#128279;'}</span>
                    <div>
                        <h4 style="font-size:16px;">${platformNames[key] || key}</h4>
                        <span class="${val.connected ? 'connected' : 'disconnected'}">
                            ${val.connected ? '&#9989; Terhubung' : '&#10060; Belum terhubung'}
                        </span>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        // Ignore
    }
}

async function connectYouTube() {
    const clientId = document.getElementById('ytClientId').value;
    const clientSecret = document.getElementById('ytClientSecret').value;

    if (!clientId || !clientSecret) { showToast('Isi Client ID dan Client Secret!', 'error'); return; }

    try {
        await apiCall('/api/upload/platforms/connect', 'POST', {
            platform: 'youtube',
            credentials: { client_id: clientId, client_secret: clientSecret },
        });

        const authResult = await apiCall('/api/upload/auth/youtube');
        if (authResult.auth_url) {
            window.open(authResult.auth_url, '_blank');
            showToast('Buka tab baru untuk authorize YouTube', 'info');
        }
        document.getElementById('ytStatus').innerHTML = '<span class="connected">Connecting...</span>';
    } catch (e) {
        showToast('Gagal menghubungkan YouTube', 'error');
    }
}

async function connectInstagram() {
    const token = document.getElementById('igAccessToken').value;
    const accountId = document.getElementById('igAccountId').value;

    if (!token || !accountId) { showToast('Isi Access Token dan Account ID!', 'error'); return; }

    try {
        await apiCall('/api/upload/platforms/connect', 'POST', {
            platform: 'instagram',
            credentials: { access_token: token, ig_user_id: accountId },
        });
        document.getElementById('igStatus').innerHTML = '<span class="connected">&#9989; Terhubung</span>';
        showToast('Instagram berhasil dihubungkan!', 'success');
    } catch (e) {
        showToast('Gagal menghubungkan Instagram', 'error');
    }
}

async function connectFacebook() {
    const token = document.getElementById('fbPageToken').value;
    const pageId = document.getElementById('fbPageId').value;

    if (!token || !pageId) { showToast('Isi Page Token dan Page ID!', 'error'); return; }

    try {
        await apiCall('/api/upload/platforms/connect', 'POST', {
            platform: 'facebook',
            credentials: { page_access_token: token, page_id: pageId },
        });
        document.getElementById('fbStatus').innerHTML = '<span class="connected">&#9989; Terhubung</span>';
        showToast('Facebook berhasil dihubungkan!', 'success');
    } catch (e) {
        showToast('Gagal menghubungkan Facebook', 'error');
    }
}

async function connectTikTok() {
    const clientKey = document.getElementById('ttClientKey').value;
    const clientSecret = document.getElementById('ttClientSecret').value;

    if (!clientKey || !clientSecret) { showToast('Isi Client Key dan Client Secret!', 'error'); return; }

    try {
        await apiCall('/api/upload/platforms/connect', 'POST', {
            platform: 'tiktok',
            credentials: { client_key: clientKey, client_secret: clientSecret },
        });
        document.getElementById('ttStatus').innerHTML = '<span class="connected">&#9989; Terhubung</span>';
        showToast('TikTok berhasil dihubungkan!', 'success');
    } catch (e) {
        showToast('Gagal menghubungkan TikTok', 'error');
    }
}

// ---- Templates ----
async function loadTemplates() {
    try {
        const result = await apiCall('/api/generate/templates');
        const container = document.getElementById('templatesList');

        if (result.items && result.items.length > 0) {
            container.innerHTML = result.items.map(t => `
                <div class="result-item">
                    <h4>${escapeHtml(t.name)}</h4>
                    <p><strong>Niche:</strong> ${escapeHtml(t.niche || '-')} | <strong>Platform:</strong> ${t.platform} | <strong>Type:</strong> ${t.content_type}</p>
                    <p>${escapeHtml(t.prompt_template.substring(0, 200))}...</p>
                    <div class="meta">
                        <button class="btn btn-sm btn-danger" onclick="deleteTemplate(${t.id})">&#128465; Hapus</button>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="empty-state"><div class="icon">&#128221;</div><h3>Belum Ada Template</h3><p>Buat template untuk mempercepat generate konten</p></div>';
        }
    } catch (e) {
        // Ignore
    }
}

async function createTemplate() {
    const data = {
        name: document.getElementById('templateName').value,
        niche: document.getElementById('templateNiche').value,
        prompt_template: document.getElementById('templatePrompt').value,
        platform: document.getElementById('templatePlatform').value,
        content_type: document.getElementById('templateType').value,
    };

    if (!data.name || !data.prompt_template) { showToast('Isi nama dan prompt template!', 'error'); return; }

    try {
        await apiCall('/api/generate/templates', 'POST', data);
        closeModal('templateModal');
        showToast('Template berhasil dibuat!', 'success');
        loadTemplates();
    } catch (e) {
        showToast('Gagal membuat template', 'error');
    }
}

async function deleteTemplate(id) {
    if (!confirm('Hapus template ini?')) return;
    try {
        await apiCall('/api/generate/templates/' + id, 'DELETE');
        showToast('Template dihapus', 'success');
        loadTemplates();
    } catch (e) {
        showToast('Gagal menghapus template', 'error');
    }
}

// ---- Utilities ----
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
        return dateStr;
    }
}

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
});
