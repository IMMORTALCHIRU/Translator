// ===================================
// History Page JavaScript
// ===================================

let currentPage = 1;
let totalPages = 1;
let allTranslations = [];

document.addEventListener('DOMContentLoaded', function() {
    loadHistory();
    
    // Pagination
    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadHistory();
        }
    });
    
    document.getElementById('nextPage').addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            loadHistory();
        }
    });
    
    // Search functionality
    const searchInput = document.getElementById('searchHistory');
    let searchTimeout;
    
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            filterHistory(this.value);
        }, 500);
    });
});

async function loadHistory() {
    const historyList = document.getElementById('historyList');
    
    try {
        const response = await fetch(`/api/history?page=${currentPage}&per_page=20`);
        const data = await response.json();
        
        if (data.success) {
            allTranslations = data.translations;
            totalPages = data.total_pages;
            
            // Update stats
            document.getElementById('totalTranslations').textContent = data.total;
            
            // Display translations
            displayTranslations(data.translations);
            
            // Update pagination
            updatePagination();
        } else {
            throw new Error(data.error || 'Failed to load history');
        }
    } catch (error) {
        console.error('Error loading history:', error);
        historyList.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                <i class="las la-exclamation-circle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                <p>Failed to load translation history</p>
            </div>
        `;
    }
}

function displayTranslations(translations) {
    const historyList = document.getElementById('historyList');
    
    if (translations.length === 0) {
        historyList.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                <i class="las la-inbox" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                <p>No translations found</p>
            </div>
        `;
        return;
    }
    
    historyList.innerHTML = translations.map(trans => `
        <div class="history-item">
            <div class="history-header">
                <div class="history-meta">
                    <span class="meta-tag">
                        <i class="las la-calendar"></i>
                        ${formatDate(trans.created_at)}
                    </span>
                    <span class="meta-tag">
                        <i class="las la-arrow-right"></i>
                        ${getLanguageName(trans.source_language)} → ${getLanguageName(trans.target_language)}
                    </span>
                </div>
                <button class="btn-icon" onclick="deleteTranslation('${trans._id}')" title="Delete">
                    <i class="las la-trash"></i>
                </button>
            </div>
            
            <div class="history-content">
                <div class="history-text">
                    <strong>Original:</strong>
                    ${trans.original_text}
                </div>
                <div class="history-text">
                    <strong>Translation:</strong>
                    ${trans.translated_text}
                </div>
            </div>
        </div>
    `).join('');
}

function updatePagination() {
    const prevButton = document.getElementById('prevPage');
    const nextButton = document.getElementById('nextPage');
    const pageInfo = document.getElementById('pageInfo');
    const pagination = document.getElementById('pagination');
    
    prevButton.disabled = currentPage === 1;
    nextButton.disabled = currentPage === totalPages;
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    
    pagination.style.display = totalPages > 1 ? 'flex' : 'none';
}

function filterHistory(searchTerm) {
    if (!searchTerm) {
        displayTranslations(allTranslations);
        return;
    }
    
    const filtered = allTranslations.filter(trans => 
        trans.original_text.toLowerCase().includes(searchTerm.toLowerCase()) ||
        trans.translated_text.toLowerCase().includes(searchTerm.toLowerCase())
    );
    
    displayTranslations(filtered);
}

async function deleteTranslation(translationId) {
    if (!confirm('Are you sure you want to delete this translation?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/history/${translationId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Translation deleted successfully', 'success');
            loadHistory(); // Reload history
        } else {
            throw new Error(data.error || 'Failed to delete translation');
        }
    } catch (error) {
        console.error('Error deleting translation:', error);
        showToast(error.message || 'Failed to delete translation', 'danger');
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return 'Today';
    } else if (diffDays === 1) {
        return 'Yesterday';
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else {
        return date.toLocaleDateString();
    }
}

function getLanguageName(code) {
    const languages = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'zh': 'Chinese',
        'ja': 'Japanese',
        'ko': 'Korean',
        'ar': 'Arabic'
    };
    return languages[code] || code.toUpperCase();
}