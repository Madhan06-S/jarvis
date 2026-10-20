import DOMPurify from 'dompurify';

/**
 * The safety boundary for model-authored markup.
 * Everything JARVIS composes for the screen passes through here — panel bodies,
 * HUD cards, and blade markup.
 *
 * Untrusted HTML from external sources or LLM output is strictly sanitized,
 * scripts/styles are stripped, class names are restricted to the HUD design-system,
 * and remote/local media URLs are rewritten through authenticated proxies.
 */

const DISK_PATH =
  /^\/(Users|home|root|Volumes|Applications|System|Library|private|tmp|var|opt|mnt|media|srv|data)\//;

function getAuthToken(): string {
  return localStorage.getItem('jarvis_token') || '';
}

function getProxyBase(): string {
  return '/api/proxy';
}

function rewriteSrc(el: Element, attr: 'src' | 'poster', route: 'img' | 'media') {
  const raw = el.getAttribute(attr) ?? '';
  if (!raw) return;

  const token = getAuthToken();
  const tokenQuery = token ? `&token=${encodeURIComponent(token)}` : '';
  const proxyBase = getProxyBase();

  const path = raw.replace(/^file:\/\//, '');
  if (DISK_PATH.test(path)) {
    el.setAttribute(attr, `${proxyBase}/${route}?path=${encodeURIComponent(path)}${tokenQuery}`);
    return;
  }

  if (!/^https?:\/\//i.test(raw)) return;
  // Already routed through our proxy
  if (raw.includes('/api/proxy/')) return;

  el.setAttribute(attr, `${proxyBase}/${route}?url=${encodeURIComponent(raw)}${tokenQuery}`);
}

function rewriteMedia(root: Element) {
  root.querySelectorAll('img').forEach((img) => rewriteSrc(img, 'src', 'img'));
  root.querySelectorAll('video').forEach((video) => {
    rewriteSrc(video, 'src', 'media');
    rewriteSrc(video, 'poster', 'img');
  });
  root.querySelectorAll('source').forEach((source) => {
    const type = source.getAttribute('type') ?? '';
    rewriteSrc(source, 'src', /^image\//i.test(type) ? 'img' : 'media');
  });
}

/**
 * Closed list of allowed video embed hosts (YouTube cookieless & Vimeo player).
 */
const EMBED_HOSTS: Record<string, RegExp> = {
  'www.youtube-nocookie.com': /^\/embed\/[\w-]+/,
  'www.youtube.com': /^\/embed\/[\w-]+/,
  'player.vimeo.com': /^\/video\/\d+/,
};

const YT_ID = /^[\w-]{6,20}$/;

function toEmbedUrl(url: URL): URL | null {
  const host = url.hostname.toLowerCase().replace(/^(?:www|m|music)\./, '');
  let id = '';
  if (host === 'youtube.com' && url.pathname === '/watch') {
    id = url.searchParams.get('v') ?? '';
  } else if (host === 'youtu.be') {
    id = url.pathname.slice(1);
  }
  if (!YT_ID.test(id)) return null;
  return new URL(`https://www.youtube-nocookie.com/embed/${id}`);
}

function rewriteEmbeds(root: Element) {
  root.querySelectorAll('iframe').forEach((frame) => {
    let url: URL;
    try {
      url = new URL(frame.getAttribute('src') ?? '', document.baseURI);
    } catch {
      frame.remove();
      return;
    }
    const embed = toEmbedUrl(url) ?? url;
    const path = EMBED_HOSTS[embed.hostname.toLowerCase()];
    if (!path || !path.test(embed.pathname)) {
      frame.remove();
      return;
    }
    embed.protocol = 'https:';
    frame.setAttribute('src', embed.toString());
  });
}

const EMBED_FEATURES = new Set([
  'accelerometer',
  'autoplay',
  'clipboard-write',
  'encrypted-media',
  'fullscreen',
  'gyroscope',
  'picture-in-picture',
  'web-share',
]);

function hardenMedia(root: Element) {
  root.querySelectorAll('img, video, iframe').forEach((el) => {
    el.setAttribute('referrerpolicy', 'no-referrer');
  });

  root.querySelectorAll('video').forEach((video) => {
    video.setAttribute('controls', '');
    video.setAttribute('preload', 'metadata');
    video.setAttribute('playsinline', '');
  });

  root.querySelectorAll('iframe[allow]').forEach((frame) => {
    const kept = (frame.getAttribute('allow') ?? '')
      .split(';')
      .map((part) => part.trim().split(/\s+/)[0].toLowerCase())
      .filter((feature) => EMBED_FEATURES.has(feature));
    if (kept.length) frame.setAttribute('allow', kept.join('; '));
    else frame.removeAttribute('allow');
  });
}

/**
 * Strict class allowlist for HUD layout and components.
 */
const ALLOWED_CLASSES = new Set([
  'hud-rows',
  'hud-row',
  'hud-idx',
  'hud-main',
  'hud-label',
  'hud-sub',
  'hud-tag',
  'hud-metric',
  'hud-unit',
  'hud-note',
  'hud-img',
  'hud-caption',
  'hud-grid',
  'hud-bar',
  'hud-dim',
  'hud-hot',
  'hud-gallery',
  'hud-thumb',
  'hud-video',
  'hud-embed',
  'hud-figure',
]);

function narrowClasses(root: Element) {
  root.querySelectorAll('[class]').forEach((el) => {
    const kept = (el.getAttribute('class') ?? '')
      .split(/\s+/)
      .filter((c) => ALLOWED_CLASSES.has(c));
    if (kept.length) el.setAttribute('class', kept.join(' '));
    else el.removeAttribute('class');
  });
}

/**
 * Sanitizes AI-authored HTML using DOMPurify with class allowlist,
 * style property narrowing (only custom property --v), and safe media rewrites.
 */
export function sanitisePanelHtml(html: string): string {
  const clean = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'div',
      'span',
      'p',
      'ul',
      'ol',
      'li',
      'img',
      'b',
      'strong',
      'em',
      'i',
      'br',
      'small',
      'table',
      'thead',
      'tbody',
      'tr',
      'td',
      'th',
      'code',
      'pre',
      'video',
      'source',
      'iframe',
    ],
    ALLOWED_ATTR: [
      'class',
      'src',
      'alt',
      'style',
      'controls',
      'poster',
      'loop',
      'muted',
      'playsinline',
      'preload',
      'width',
      'height',
      'allow',
      'allowfullscreen',
      'referrerpolicy',
      'type',
      'title',
    ],
    ADD_URI_SAFE_ATTR: [
      'controls',
      'loop',
      'muted',
      'playsinline',
      'preload',
      'width',
      'height',
      'allow',
      'allowfullscreen',
      'referrerpolicy',
      'type',
    ],
    ALLOWED_URI_REGEXP: /^(?:data:(?:image|video|audio)\/|file:\/\/|https?:\/\/|\/)/i,
  });

  const doc = new DOMParser().parseFromString(clean, 'text/html');

  // style attribute survives ONLY for progress custom property --v
  doc.body.querySelectorAll('[style]').forEach((el) => {
    const style = el.getAttribute('style') ?? '';
    const v = /--v:\s*([\d.]+)/.exec(style);
    if (v) el.setAttribute('style', `--v:${v[1]}`);
    else el.removeAttribute('style');
  });

  narrowClasses(doc.body);
  rewriteMedia(doc.body);
  rewriteEmbeds(doc.body);
  hardenMedia(doc.body);

  return doc.body.innerHTML;
}
