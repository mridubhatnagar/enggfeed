    function summaryPage() {
      return {

        flashMessage: '',

        blogId: null,
        summaryDetail: null,
        detailLoading: true,

        showPrereqModal: false,
        prereqLoading: false,
        prereqTopic: '',
        prereqDetail: null,
        prereqShowDeepDive: false,

        showFeedbackModal: false,
        showFeedbackSuccess: false,
        feedbackBlogId: null,
        feedbackDetailType: null,
        feedbackDetailText: '',
        feedbackName: '',
        feedbackEmail: '',
        feedbackWebsite: '',
        feedbackSubmitting: false,

        copied: false,

        async _init() {
          const parts = window.location.pathname.split('/').filter(Boolean);
          this.blogId = decodeURIComponent(parts[parts.length - 1]);
          await this._load();
        },

        async _load() {
          this.detailLoading = true;
          try {
            const res  = await fetch(`/api/v1/blogs/${encodeURIComponent(this.blogId)}/summary`, { credentials: 'include' });
            const json = await res.json();
            if (json.success && json.data) {
              this.summaryDetail = json.data;
            } else {
              this.flashMessage = 'Sorry, we are unable to process your request. Please try again after some time.';
              setTimeout(() => { this.flashMessage = ''; }, 6000);
            }
          } catch (_) {
            this.flashMessage = 'Sorry, we are unable to process your request. Please try again after some time.';
            setTimeout(() => { this.flashMessage = ''; }, 6000);
          } finally {
            this.detailLoading = false;
          }
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

        openDetailFeedbackModal(blogId, type) {
          this.feedbackBlogId     = blogId;
          this.feedbackDetailType = type;
          this.feedbackDetailText = '';
          this.feedbackName       = '';
          this.feedbackEmail      = '';
          this.feedbackWebsite    = '';
          this.showFeedbackModal  = true;
        },

        async submitFeedback() {
          if (this.feedbackSubmitting) return;
          this.feedbackSubmitting = true;
          try {
            const result = await this._postFeedback(this.feedbackBlogId, this.feedbackDetailType, this.feedbackDetailText.trim());
            if (!result.success) { this._showFeedbackError(result); return; }
            this.showFeedbackModal   = false;
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

      };
    }
