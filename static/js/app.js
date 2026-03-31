    function app() {
      return {

        // ── Auth ────────────────────────────────────────────────
        user: null,

        // ── View state: 'feed' | 'summary' | 'simplify' ────────
        currentView: 'feed',

        // ── Flash message ───────────────────────────────────────
        flashMessage: '',

        // ── Feed state ──────────────────────────────────────────
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

        // ── Detail (summary / simplify) ─────────────────────────
        detailLoading: false,
        currentBlogId: null,
        summaryDetail: null,   // SummaryDetail from /api/v1/blogs/{id}/summary
        simplifyDetail: null,  // SimplifyDetail from /api/v1/blogs/{id}/simplify

        // ── Prerequisites modal ─────────────────────────────────
        showPrereqModal: false,
        prereqLoading: false,
        prereqTopic: '',
        prereqDetail: null,        // PrerequisiteDetail from /api/v1/prerequisites/{topic}
        prereqShowDeepDive: false,

        // ── Sign In modal ───────────────────────────────────────
        showSigninModal: false,

        // ── Share / copy feedback ───────────────────────────────
        copied: false,

        // ────────────────────────────────────────────────────────
        // Initialisation
        // ────────────────────────────────────────────────────────
        async _init() {
          // Read URL params first so bookmarked/shared URLs restore correctly
          this._readUrlParams();

          // Fire auth check, sources, and tags fetch in parallel
          await Promise.all([
            this._fetchUser(),
            this._fetchSources(),
            this._fetchTags(),
          ]);

          // Load blog cards (auth state affects tags/prereqs returned)
          await this._fetchBlogs();

          // Wire up infinite scroll after initial render
          this._initInfiniteScroll();
        },

        // ────────────────────────────────────────────────────────
        // Auth
        // ────────────────────────────────────────────────────────
        async _fetchUser() {
          try {
            const res = await fetch('/auth/me', { credentials: 'include' });
            if (res.ok) {
              const json = await res.json();
              if (json.success && json.data) {
                this.user = json.data;
              }
            }
            // 401 = guest — silently ignored
          } catch (_) {
            // Network error — treat as guest
          }
        },

        async signOut() {
          try {
            await fetch('/auth/logout', { method: 'POST', credentials: 'include' });
          } catch (_) {}
          this.user = null;
          this.goFeed();
          // Re-fetch so tags/prereqs disappear from cards immediately
          await this._fetchBlogs();
        },

        initials(name) {
          if (!name) return '?';
          return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();
        },

        // ────────────────────────────────────────────────────────
        // Sources
        // ────────────────────────────────────────────────────────
        async _fetchSources() {
          try {
            const res = await fetch('/api/v1/sources');
            const json = await res.json();
            if (json.success && json.data) {
              this.sources = json.data;
            }
          } catch (_) {}
        },

        // ────────────────────────────────────────────────────────
        // Tags
        // ────────────────────────────────────────────────────────
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

        // ────────────────────────────────────────────────────────
        // Feed / blog listing
        // ────────────────────────────────────────────────────────
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

        filterByTagFromDetail(tag) {
          // Navigate back to feed then apply tag filter
          this.goFeed();
          this.$nextTick(() => this.filterByTag(tag));
        },

        clearFilters() {
          this.activeSources = [];
          this.activeTags    = [];
          this._pushUrl();
          this._fetchBlogs();
        },

        // ────────────────────────────────────────────────────────
        // Summary page
        // ────────────────────────────────────────────────────────
        async openSummary(blogId) {
          this.currentBlogId  = blogId;
          this.summaryDetail  = null;
          this.currentView    = 'summary';
          this.detailLoading  = true;
          window.scrollTo({ top: 0, behavior: 'instant' });
          history.pushState({ view: 'summary', blogId }, '', `/summary/${encodeURIComponent(blogId)}`);
          try {
            const res  = await fetch(`/api/v1/blogs/${encodeURIComponent(blogId)}/summary`, { credentials: 'include' });
            const json = await res.json();
            if (json.success && json.data) {
              this.summaryDetail = json.data;
            } else {
              this._handleDetailError();
            }
          } catch (_) {
            this._handleDetailError();
          } finally {
            this.detailLoading = false;
          }
        },

        // ────────────────────────────────────────────────────────
        // Simplify page
        // ────────────────────────────────────────────────────────
        async openSimplify(blogId) {
          this.currentBlogId  = blogId;
          this.simplifyDetail = null;
          this.currentView    = 'simplify';
          this.detailLoading  = true;
          window.scrollTo({ top: 0, behavior: 'instant' });
          history.pushState({ view: 'simplify', blogId }, '', `/simplify/${encodeURIComponent(blogId)}`);
          try {
            const res  = await fetch(`/api/v1/blogs/${encodeURIComponent(blogId)}/simplify`, { credentials: 'include' });
            const json = await res.json();
            if (json.success && json.data) {
              this.simplifyDetail = json.data;
            } else {
              this._handleDetailError();
            }
          } catch (_) {
            this._handleDetailError();
          } finally {
            this.detailLoading = false;
          }
        },

        _handleDetailError() {
          // On error: stay on (or return to) feed, show flash message
          this.goFeed();
          this.flashMessage = 'Sorry, we are unable to process your request. Please try again after some time.';
          setTimeout(() => { this.flashMessage = ''; }, 6000);
        },

        // ────────────────────────────────────────────────────────
        // Prerequisites modal
        // ────────────────────────────────────────────────────────
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

        // ────────────────────────────────────────────────────────
        // Navigation helpers
        // ────────────────────────────────────────────────────────
        goFeed() {
          this.currentView = 'feed';
          this._pushUrl();
          window.scrollTo({ top: 0, behavior: 'instant' });
        },

        // ────────────────────────────────────────────────────────
        // URL sync (history.pushState)
        // ────────────────────────────────────────────────────────
        _pushUrl() {
          const p = new URLSearchParams();
          if (this.activeSources.length) p.set('source', this.activeSources.join(','));
          if (this.activeTags.length)    p.set('tag',    this.activeTags.join(','));
          const qs = p.toString();
          history.pushState({}, '', qs ? '/?' + qs : '/');
        },

        _readUrlParams() {
          const p = new URLSearchParams(window.location.search);
          const error = p.get('error');
          if (error === 'not_allowed') {
            this.flashMessage = 'Your account is not authorised to access this app.';
            setTimeout(() => { this.flashMessage = ''; }, 6000);
            history.replaceState({}, '', '/');
          } else if (error === 'auth_failed') {
            this.flashMessage = 'Sign-in failed. Please try again.';
            setTimeout(() => { this.flashMessage = ''; }, 6000);
            history.replaceState({}, '', '/');
          }
          const src = p.get('source');
          this.activeSources = src ? src.split(',').filter(Boolean) : [];
          const tag = p.get('tag');
          this.activeTags = tag ? tag.split(',').filter(Boolean) : [];
        },

        // ────────────────────────────────────────────────────────
        // Global Escape key handler
        // ────────────────────────────────────────────────────────
        handleEsc() {
          if (this.showPrereqModal) { this.showPrereqModal = false; return; }
          if (this.showSigninModal) { this.showSigninModal = false; return; }
        },

        // ────────────────────────────────────────────────────────
        // Formatting helpers
        // ────────────────────────────────────────────────────────
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
