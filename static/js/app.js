    function app() {
      return {

        flashMessage: '',

        feedLoading: false,
        scrollLoading: false,
        blogs: [],          // array of { id, ...BlogItem } from /api/v1/blogs
        sources: [],        // array of BlogSource from /api/v1/sources
        tags: [],           // array of { tag, count } from /api/v1/tags
        activeSources: [],  // array of source names
        activeTags: [],     // array of tag names

        // Infinite scroll
        currentPage: 1,
        allLoaded: false,
        pageSize: 12,

        showPrereqModal: false,
        prereqLoading: false,
        prereqTopic: '',
        prereqDetail: null,        // PrerequisiteDetail from /api/v1/prerequisites/{topic}
        prereqShowDeepDive: false,

        showFeedbackSuccess: false,
        showFeedbackModal: false,
        feedbackBlogId: null,
        feedbackMode: null,        // 'card' | 'detail'
        feedbackDetailType: null,  // 'summary' | 'simplify'
        feedbackTagText: '',
        feedbackPrereqText: '',
        feedbackDetailText: '',
        feedbackName: '',
        feedbackEmail: '',
        feedbackWebsite: '',
        feedbackSubmitting: false,

        copied: false,

        async _init() {
          // Read URL params first so bookmarked/shared URLs restore correctly
          this._readUrlParams();

          await Promise.all([
            this._fetchSources(),
            this._fetchTags(),
          ]);

          await this._fetchBlogs();

          // Wire up infinite scroll after initial render
          this._initInfiniteScroll();
        },

        async _fetchSources() {
          try {
            const res = await fetch('/api/v1/sources');
            const json = await res.json();
            if (json.success && json.data) {
              this.sources = json.data;
            }
          } catch (_) {}
        },

        async _fetchTags() {
          try {
            const res = await fetch('/api/v1/tags');
            const json = await res.json();
            if (json.success && json.data) {
              this.tags = json.data;
            }
          } catch (_) {}
        },

        sourceToFaviconDomain(sourceName) {
          const map = {
            'Cloudflare':        'cloudflare.com',
            'GitHub':            'github.com',
            'Meta':              'meta.com',
            'AWS':               'aws.amazon.com',
            'Slack Engineering': 'slack.com',
            'Netflix':           'netflix.com',
            'Airbnb':            'airbnb.com',
            'Dropbox':           'dropbox.com',
            'Fly.io':            'fly.io',
            'Discord':           'discord.com',
            'Spotify':           'spotify.com',
            'Google Developers': 'developers.google.com',
            'Stripe':            'stripe.com',
          };
          return map[sourceName] || (sourceName.toLowerCase().replace(/\s+/g, '') + '.com');
        },

        async _fetchBlogs() {
          this.blogs = [];
          this.currentPage = 1;
          this.allLoaded = false;
          await this._fetchPage();
        },

        async _fetchPage() {
          if (this.allLoaded) return;
          if (this.currentPage === 1) {
            this.feedLoading = true;
          } else {
            this.scrollLoading = true;
          }
          try {
            const qs = this._buildBlogParams();
            const res = await fetch('/api/v1/blogs?' + qs, { credentials: 'include' });
            const json = await res.json();
            if (json.success && json.data) {
              const d = json.data;
              const newBlogs = Object.entries(d.blogs).map(([id, blog]) => ({ id, ...blog }));
              this.blogs = [...this.blogs, ...newBlogs];
              if (d.page >= d.total_pages || newBlogs.length === 0) {
                this.allLoaded = true;
              }
            } else {
              this.allLoaded = true;
            }
          } catch (_) {
            this.allLoaded = true;
          } finally {
            this.feedLoading = false;
            this.scrollLoading = false;
          }
        },

        async _loadNextPage() {
          if (this.allLoaded || this.feedLoading || this.scrollLoading) return;
          this.currentPage += 1;
          await this._fetchPage();
        },

        _initInfiniteScroll() {
          const sentinel = document.getElementById('scroll-sentinel');
          if (!sentinel) return;
          const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && !this.allLoaded) {
              this._loadNextPage();
            }
          }, { rootMargin: '200px' });
          observer.observe(sentinel);
        },

        _buildBlogParams() {
          const p = new URLSearchParams();
          p.set('page', String(this.currentPage));
          p.set('count', String(this.pageSize));
          if (this.activeSources.length) p.set('source', this.activeSources.join(','));
          if (this.activeTags.length)    p.set('tag',    this.activeTags.join(','));
          return p.toString();
        },

        toggleSource(sourceName) {
          const idx = this.activeSources.indexOf(sourceName);
          this.activeSources = idx === -1
            ? [...this.activeSources, sourceName]
            : this.activeSources.filter(s => s !== sourceName);
          this._pushUrl();
          this._fetchBlogs();
        },

        toggleTag(tagName) {
          const idx = this.activeTags.indexOf(tagName);
          this.activeTags = idx === -1
            ? [...this.activeTags, tagName]
            : this.activeTags.filter(t => t !== tagName);
          this._pushUrl();
          this._fetchBlogs();
        },

        filterByTag(tag) {
          this.activeTags    = [tag];
          this.activeSources = [];
          this._pushUrl();
          this._fetchBlogs();
        },

        clearFilters() {
          this.activeSources = [];
          this.activeTags    = [];
          this._pushUrl();
          this._fetchBlogs();
        },

        async openPrereqModal(topicName) {
          this.prereqTopic        = topicName;
          this.prereqDetail       = null;
          this.prereqShowDeepDive = false;
          this.prereqLoading      = true;
          this.showPrereqModal    = true;
          try {
            const res  = await fetch(`/api/v1/prerequisites/${encodeURIComponent(topicName)}`, { credentials: 'include' });
            const json = await res.json();
            if (json.success && json.data) {
              this.prereqDetail = json.data;
            }
          } catch (_) {}
          finally {
            this.prereqLoading = false;
          }
        },

        _pushUrl() {
          const p = new URLSearchParams();
          if (this.activeSources.length) p.set('source', this.activeSources.join(','));
          if (this.activeTags.length)    p.set('tag',    this.activeTags.join(','));
          const qs = p.toString();
          history.pushState({}, '', qs ? '/?' + qs : '/');
        },

        _readUrlParams() {
          const p = new URLSearchParams(window.location.search);
          const src = p.get('source');
          this.activeSources = src ? src.split(',').filter(Boolean) : [];
          const tag = p.get('tag');
          this.activeTags = tag ? tag.split(',').filter(Boolean) : [];
        },

        openCardFeedbackModal(blogId) {
          this.feedbackBlogId    = blogId;
          this.feedbackMode      = 'card';
          this.feedbackTagText   = '';
          this.feedbackPrereqText = '';
          this.feedbackName      = '';
          this.feedbackEmail     = '';
          this.feedbackWebsite   = '';
          this.showFeedbackModal = true;
        },

        openDetailFeedbackModal(blogId, type) {
          this.feedbackBlogId    = blogId;
          this.feedbackMode      = 'detail';
          this.feedbackDetailType = type;
          this.feedbackDetailText = '';
          this.feedbackName      = '';
          this.feedbackEmail     = '';
          this.feedbackWebsite   = '';
          this.showFeedbackModal = true;
        },

        async submitFeedback() {
          if (this.feedbackSubmitting) return;
          this.feedbackSubmitting = true;
          try {
            if (this.feedbackMode === 'card') {
              const requests = [];
              if (this.feedbackTagText.trim())
                requests.push(this._postFeedback(this.feedbackBlogId, 'tag', this.feedbackTagText.trim()));
              if (this.feedbackPrereqText.trim())
                requests.push(this._postFeedback(this.feedbackBlogId, 'prerequisite', this.feedbackPrereqText.trim()));
              if (requests.length === 0) { this.showFeedbackModal = false; return; }
              const results = await Promise.all(requests);
              const failed = results.find(r => !r.success);
              if (failed) { this._showFeedbackError(failed); return; }
            } else {
              const result = await this._postFeedback(this.feedbackBlogId, this.feedbackDetailType, this.feedbackDetailText.trim());
              if (!result.success) { this._showFeedbackError(result); return; }
            }
            this.showFeedbackModal = false;
            this.showFeedbackSuccess = true;
          } finally {
            this.feedbackSubmitting = false;
          }
        },

        async _postFeedback(blogId, type, content) {
          try {
            const res = await fetch('/api/v1/feedback', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({
                blog_id: blogId,
                type,
                content,
                name: this.feedbackName.trim() || null,
                email: this.feedbackEmail.trim() || null,
                website: this.feedbackWebsite.trim() || null,
              }),
            });
            return await res.json();
          } catch (_) {
            return { success: false, error: { code: 500, message: 'Network error. Please try again.' } };
          }
        },

        _showFeedbackError(result) {
          this.showFeedbackModal = false;
          const code = result?.error?.code;
          if (code === 429) {
            this.flashMessage = "You've reached your feedback limit. Please try again later.";
          } else if (code === 422) {
            this.flashMessage = result?.error?.message || 'Feedback must be between 10 and 500 characters.';
          } else {
            this.flashMessage = 'Failed to submit feedback. Please try again.';
          }
          setTimeout(() => { this.flashMessage = ''; }, 6000);
        },

        handleEsc() {
          if (this.showFeedbackSuccess) { this.showFeedbackSuccess = false; return; }
          if (this.showFeedbackModal)   { this.showFeedbackModal   = false; return; }
          if (this.showPrereqModal)     { this.showPrereqModal     = false; return; }
        },

        copyUrl(url) {
          navigator.clipboard.writeText(url).then(() => {
            this.copied = true;
            setTimeout(() => { this.copied = false; }, 2000);
          });
        },

        formatDate(isoString) {
          if (!isoString) return '';
          try {
            return new Date(isoString).toLocaleDateString('en-US', {
              year: 'numeric', month: 'long', day: 'numeric',
            });
          } catch (_) {
            return isoString;
          }
        },

        formatDateShort(isoString) {
          if (!isoString) return '';
          try {
            return new Date(isoString).toLocaleDateString('en-US', {
              year: 'numeric', month: 'short', day: 'numeric',
            });
          } catch (_) {
            return isoString;
          }
        },

      }; // end return
    } // end app()

    function openCardFeedbackModal(blogId) {
      const data = Alpine.$data(document.querySelector('[x-data]'));
      data.feedbackBlogId     = blogId;
      data.feedbackMode       = 'card';
      data.feedbackTagText    = '';
      data.feedbackPrereqText = '';
      data.showFeedbackModal  = true;
    }
