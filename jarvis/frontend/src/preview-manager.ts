/**
 * Live preview iframe — suspend when hidden, lazy activate on URL set.
 */

export class PreviewManager {
  private iframe: HTMLIFrameElement;
  private sidebar: HTMLElement | null;
  private activeUrl: string | null = null;
  private suspended = true;

  constructor(iframeId = 'preview-frame', sidebarId = 'process-sidebar') {
    this.iframe = document.getElementById(iframeId) as HTMLIFrameElement;
    this.sidebar = document.getElementById(sidebarId);

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries[0]?.isIntersecting ?? false;
        if (!visible && !this.suspended) this.suspend();
        else if (visible && this.activeUrl && this.suspended) this.resume();
      },
      { threshold: 0.1 }
    );
    if (this.sidebar) observer.observe(this.sidebar);
  }

  show(url: string) {
    this.activeUrl = url;
    this.suspended = false;
    if (this.sidebar) {
      this.sidebar.style.right = '0';
      this.sidebar.style.width = 'min(70vw, 900px)';
    }
    this.iframe.style.display = 'block';
    if (this.iframe.src !== url) {
      this.iframe.src = url;
    }
  }

  suspend() {
    if (!this.activeUrl) return;
    this.suspended = true;
    this.iframe.src = 'about:blank';
  }

  resume() {
    if (!this.activeUrl) return;
    this.suspended = false;
    this.iframe.src = this.activeUrl;
  }

  hide() {
    this.activeUrl = null;
    this.suspended = true;
    this.iframe.style.display = 'none';
    this.iframe.src = 'about:blank';
    if (this.sidebar) {
      this.sidebar.style.right = '-600px';
    }
  }
}
