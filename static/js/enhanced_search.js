// Enhanced Search with Real-time Suggestions and Filters
class EnhancedSearch {
    constructor() {
        this.searchInput = null;
        this.suggestionsContainer = null;
        this.filtersContainer = null;
        this.resultsContainer = null;
        this.currentQuery = '';
        this.currentFilters = {};
        this.suggestions = [];
        this.filters = {};
        this.debounceTimer = null;
        this.init();
    }
    
    init() {
        this.setupSearchInput();
        this.setupSuggestionsContainer();
        this.setupFiltersContainer();
        this.setupResultsContainer();
        this.loadFilters();
        this.bindEvents();
    }
    
    setupSearchInput() {
        // Find or create search input
        this.searchInput = document.querySelector('input[name="q"]');
        if (!this.searchInput) {
            console.warn('Search input not found');
            return;
        }
        
        // Add enhanced search classes
        this.searchInput.classList.add('enhanced-search-input');
        this.searchInput.setAttribute('autocomplete', 'off');
        this.searchInput.setAttribute('placeholder', 'Search updates, SOPs, lessons... (type to see suggestions)');
    }
    
    setupSuggestionsContainer() {
        // Create suggestions container
        this.suggestionsContainer = document.createElement('div');
        this.suggestionsContainer.className = 'search-suggestions';
        this.suggestionsContainer.style.display = 'none';
        
        // Insert after search input
        if (this.searchInput && this.searchInput.parentNode) {
            this.searchInput.parentNode.insertBefore(this.suggestionsContainer, this.searchInput.nextSibling);
        }
    }
    
    setupFiltersContainer() {
        // Create filters container
        this.filtersContainer = document.createElement('div');
        this.filtersContainer.className = 'search-filters';
        this.filtersContainer.innerHTML = `
            <div class="filters-header">
                <h4>Filters</h4>
                <button class="clear-filters-btn">Clear All</button>
            </div>
            <div class="filter-group">
                <label>Category:</label>
                <select class="filter-select" data-filter="category">
                    <option value="">All Categories</option>
                    <option value="updates">Updates</option>
                    <option value="sops">SOPs</option>
                    <option value="lessons">Lessons</option>
                </select>
            </div>
            <div class="filter-group">
                <label>Process:</label>
                <select class="filter-select" data-filter="process">
                    <option value="">All Processes</option>
                </select>
            </div>
            <div class="filter-group">
                <label>Department:</label>
                <select class="filter-select" data-filter="department">
                    <option value="">All Departments</option>
                </select>
            </div>
            <div class="filter-group">
                <label>Tags:</label>
                <div class="tags-container">
                    <input type="text" class="tags-input" placeholder="Type tags...">
                    <div class="selected-tags"></div>
                </div>
            </div>
        `;
        
        // Insert after search form
        const searchForm = document.querySelector('.search-form');
        if (searchForm && searchForm.parentNode) {
            searchForm.parentNode.insertBefore(this.filtersContainer, searchForm.nextSibling);
        }
    }
    
    setupResultsContainer() {
        // Find existing results container or create one
        this.resultsContainer = document.querySelector('.results-container') || 
                               document.querySelector('.search-results-root');
    }
    
    async loadFilters() {
        try {
            const response = await fetch('/api/search/filters');
            this.filters = await response.json();
            this.populateFilterOptions();
        } catch (error) {
            console.error('Error loading filters:', error);
        }
    }
    
    populateFilterOptions() {
        // Populate process filter
        const processSelect = this.filtersContainer.querySelector('[data-filter="process"]');
        if (processSelect && this.filters.processes) {
            this.filters.processes.forEach(process => {
                const option = document.createElement('option');
                option.value = process;
                option.textContent = process;
                processSelect.appendChild(option);
            });
        }
        
        // Populate department filter
        const deptSelect = this.filtersContainer.querySelector('[data-filter="department"]');
        if (deptSelect && this.filters.departments) {
            this.filters.departments.forEach(dept => {
                const option = document.createElement('option');
                option.value = dept;
                option.textContent = dept;
                deptSelect.appendChild(option);
            });
        }
    }
    
    bindEvents() {
        if (!this.searchInput) return;
        
        // Search input events
        this.searchInput.addEventListener('input', (e) => {
            this.handleSearchInput(e.target.value);
        });
        
        this.searchInput.addEventListener('focus', () => {
            this.showSuggestions();
        });
        
        this.searchInput.addEventListener('blur', () => {
            // Delay hiding suggestions to allow for clicks
            setTimeout(() => this.hideSuggestions(), 200);
        });
        
        // Filter events
        this.filtersContainer.addEventListener('change', (e) => {
            if (e.target.classList.contains('filter-select')) {
                this.handleFilterChange(e.target.dataset.filter, e.target.value);
            }
        });
        
        // Tags input events
        const tagsInput = this.filtersContainer.querySelector('.tags-input');
        if (tagsInput) {
            tagsInput.addEventListener('input', (e) => {
                this.handleTagsInput(e.target.value);
            });
            
            tagsInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ',') {
                    e.preventDefault();
                    this.addTag(e.target.value);
                    e.target.value = '';
                }
            });
        }
        
        // Clear filters button
        const clearBtn = this.filtersContainer.querySelector('.clear-filters-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearFilters();
            });
        }
        
        // Click outside to hide suggestions
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && !this.suggestionsContainer.contains(e.target)) {
                this.hideSuggestions();
            }
        });
    }
    
    async handleSearchInput(query) {
        this.currentQuery = query;
        
        // Clear previous timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // Debounce search suggestions
        this.debounceTimer = setTimeout(async () => {
            if (query.length >= 2) {
                await this.fetchSuggestions(query);
                this.showSuggestions();
            } else {
                this.hideSuggestions();
            }
        }, 300);
    }
    
    async fetchSuggestions(query) {
        try {
            const response = await fetch(`/api/search/suggestions?q=${encodeURIComponent(query)}&limit=8`);
            const data = await response.json();
            this.suggestions = data.suggestions || [];
            this.renderSuggestions();
        } catch (error) {
            console.error('Error fetching suggestions:', error);
            this.suggestions = [];
        }
    }
    
    renderSuggestions() {
        if (!this.suggestionsContainer) return;
        
        if (this.suggestions.length === 0) {
            this.suggestionsContainer.innerHTML = '<div class="no-suggestions">No suggestions found</div>';
            return;
        }
        
        const suggestionsHTML = this.suggestions.map(suggestion => `
            <div class="suggestion-item" data-text="${suggestion.text}">
                <div class="suggestion-text">${this.highlightQuery(suggestion.text, this.currentQuery)}</div>
                <div class="suggestion-meta">
                    <span class="suggestion-type">${suggestion.type}</span>
                    <span class="suggestion-count">${suggestion.count}</span>
                </div>
            </div>
        `).join('');
        
        this.suggestionsContainer.innerHTML = suggestionsHTML;
        
        // Add click events to suggestions
        this.suggestionsContainer.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', () => {
                this.selectSuggestion(item.dataset.text);
            });
        });
    }
    
    highlightQuery(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }
    
    selectSuggestion(text) {
        if (this.searchInput) {
            this.searchInput.value = text;
            this.searchInput.focus();
            this.hideSuggestions();
            this.performSearch();
        }
    }
    
    showSuggestions() {
        if (this.suggestionsContainer && this.suggestions.length > 0) {
            this.suggestionsContainer.style.display = 'block';
        }
    }
    
    hideSuggestions() {
        if (this.suggestionsContainer) {
            this.suggestionsContainer.style.display = 'none';
        }
    }
    
    handleFilterChange(filterName, value) {
        this.currentFilters[filterName] = value;
        this.performSearch();
    }
    
    handleTagsInput(value) {
        // Could show tag suggestions here
    }
    
    addTag(tag) {
        if (!tag.trim()) return;
        
        if (!this.currentFilters.tags) {
            this.currentFilters.tags = [];
        }
        
        if (!this.currentFilters.tags.includes(tag.trim())) {
            this.currentFilters.tags.push(tag.trim());
            this.renderSelectedTags();
            this.performSearch();
        }
    }
    
    removeTag(tag) {
        if (this.currentFilters.tags) {
            this.currentFilters.tags = this.currentFilters.tags.filter(t => t !== tag);
            this.renderSelectedTags();
            this.performSearch();
        }
    }
    
    renderSelectedTags() {
        const selectedTagsContainer = this.filtersContainer.querySelector('.selected-tags');
        if (!selectedTagsContainer) return;
        
        if (!this.currentFilters.tags || this.currentFilters.tags.length === 0) {
            selectedTagsContainer.innerHTML = '';
            return;
        }
        
        const tagsHTML = this.currentFilters.tags.map(tag => `
            <span class="selected-tag">
                ${tag}
                <button class="remove-tag" onclick="enhancedSearch.removeTag('${tag}')">&times;</button>
            </span>
        `).join('');
        
        selectedTagsContainer.innerHTML = tagsHTML;
    }
    
    clearFilters() {
        this.currentFilters = {};
        
        // Reset filter selects
        this.filtersContainer.querySelectorAll('.filter-select').forEach(select => {
            select.value = '';
        });
        
        // Clear tags
        const tagsInput = this.filtersContainer.querySelector('.tags-input');
        if (tagsInput) tagsInput.value = '';
        
        this.renderSelectedTags();
        this.performSearch();
    }
    
    async performSearch() {
        if (!this.currentQuery.trim()) return;
        
        const params = new URLSearchParams({
            q: this.currentQuery,
            ...this.currentFilters
        });
        
        try {
            const response = await fetch(`/api/search?${params}`);
            const data = await response.json();
            this.displayResults(data);
        } catch (error) {
            console.error('Error performing search:', error);
            this.displayError('Search failed. Please try again.');
        }
    }
    
    displayResults(data) {
        if (!this.resultsContainer) return;
        
        // Update results display
        // This would integrate with your existing results display logic
        console.log('Search results:', data);
        
        // Emit custom event for other components to handle
        const event = new CustomEvent('searchResultsUpdated', { detail: data });
        document.dispatchEvent(event);
    }
    
    displayError(message) {
        if (!this.resultsContainer) return;
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'search-error';
        errorDiv.textContent = message;
        
        // Clear previous results and show error
        this.resultsContainer.innerHTML = '';
        this.resultsContainer.appendChild(errorDiv);
    }
}

// Initialize enhanced search when DOM is loaded
let enhancedSearch;
document.addEventListener('DOMContentLoaded', function() {
    enhancedSearch = new EnhancedSearch();
});

// Export for global access
window.enhancedSearch = enhancedSearch;
