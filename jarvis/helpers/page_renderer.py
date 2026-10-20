"""
JARVIS Page Renderer — Reader and Live Modes for HUD Display
Renders sanitized external web pages into iframe-ready documents.
"""
import re
import secrets
import urllib.parse
from typing import Dict, Any, Tuple
from html import escape

SCROLL_SHIM = """
addEventListener('message', function (e) {
  var d = e.data;
  if (!d || d.jarvis !== 'scroll') return;
  if (d.to === 'top') { window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
  if (d.to === 'bottom') { window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }); return; }
  window.scrollBy({ top: d.dy || 0, behavior: d.smooth ? 'smooth' : 'auto' });
});
try { parent.postMessage({ jarvis: 'ready' }, '*'); } catch (e) {}
"""

KILL_TAGS = [
    'script', 'style', 'noscript', 'template', 'svg', 'canvas', 'form',
    'iframe', 'object', 'embed', 'applet', 'link', 'meta',
]

def strip_dangerous_html(html: str) -> str:
    out = re.sub(r"<!--[\s\S]*?-->", "", html)
    for tag in KILL_TAGS:
        out = re.sub(rf"<{tag}\b[\s\S]*?</{tag}\s*>", "", out, flags=re.IGNORECASE)
        out = re.sub(rf"<{tag}\b[^>]*/?>", "", out, flags=re.IGNORECASE)

    out = re.sub(r"\son[a-z]+\s*=\s*([\"'])[\s\S]*?\1", "", out, flags=re.IGNORECASE)
    out = re.sub(r"\son[a-z]+\s*=\s*[^\s>]+", "", out, flags=re.IGNORECASE)
    out = re.sub(r"(href|src|action|poster)\s*=\s*([\"'])\s*(javascript|data:text/html|vbscript):[\s\S]*?\2", r'\1="#"', out, flags=re.IGNORECASE)
    return out

def render_live_page(html: str, base_url: str) -> Tuple[str, Dict[str, str]]:
    nonce = secrets.token_hex(16)
    clean = strip_dangerous_html(html)

    # Inject base tag so relative links resolve to origin
    base_tag = f'<base href="{escape(base_url)}" target="_blank">'
    script_tag = f'<script nonce="{nonce}">{SCROLL_SHIM}</script>'

    if "<head>" in clean.lower():
        body = re.sub(r"(<head[^>]*>)", rf"\1{base_tag}{script_tag}", clean, count=1, flags=re.IGNORECASE)
    else:
        body = f"<!DOCTYPE html><html><head>{base_tag}{script_tag}</head><body>{clean}</body></html>"

    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Security-Policy": (
            f"default-src 'none'; img-src http: https: data:; media-src http: https: data:; "
            f"style-src 'unsafe-inline' https:; font-src https: data:; script-src 'nonce-{nonce}'; "
            "sandbox allow-scripts;"
        ),
        "X-Content-Type-Options": "nosniff",
    }
    return body, headers

def render_reader_page(html: str, target_url: str, token: str = "") -> Tuple[str, Dict[str, str]]:
    nonce = secrets.token_hex(16)
    clean = strip_dangerous_html(html)

    # Extract title
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else target_url

    # Extract paragraphs and headings
    paras = re.findall(r"<(?:p|h[1-6]|li|blockquote)[^>]*>(.*?)</(?:p|h[1-6]|li|blockquote)>", clean, re.IGNORECASE | re.DOTALL)
    clean_paras = []
    for p in paras:
        text = re.sub(r"<[^>]+>", "", p).strip()
        if len(text) > 30:
            clean_paras.append(f"<p>{escape(text)}</p>")

    content = "\n".join(clean_paras) if clean_paras else "<p>No readable content extracted from page.</p>"

    token_q = f"&token={urllib.parse.quote(token)}" if token else ""
    parsed_target = urllib.parse.urlparse(target_url)
    domain = parsed_target.netloc

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <script nonce="{nonce}">{SCROLL_SHIM}</script>
  <style>
    body {{
      margin: 0; padding: 24px 32px;
      background: #030810; color: rgba(220, 240, 255, 0.9);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.7; font-size: 15px;
    }}
    .rd-header {{ margin-bottom: 24px; border-bottom: 1px solid rgba(0, 191, 255, 0.3); padding-bottom: 16px; }}
    .rd-domain {{ font-family: monospace; font-size: 11px; color: #00BFFF; text-transform: uppercase; letter-spacing: 2px; }}
    .rd-title {{ font-size: 24px; font-weight: 700; color: #fff; margin: 8px 0 12px 0; }}
    .rd-link {{ font-size: 12px; color: rgba(0, 191, 255, 0.7); text-decoration: none; }}
    .rd-link:hover {{ text-decoration: underline; color: #00BFFF; }}
    p {{ margin-bottom: 16px; }}
  </style>
</head>
<body>
  <div class="rd-header">
    <div class="rd-domain">SOURCE: {escape(domain)}</div>
    <h1 class="rd-title">{escape(title)}</h1>
    <a class="rd-link" href="{escape(target_url)}" target="_blank">Open original page ↗</a>
  </div>
  <div class="rd-body">
    {content}
  </div>
</body>
</html>"""

    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Security-Policy": (
            f"default-src 'none'; img-src http: https: data:; style-src 'unsafe-inline'; "
            f"script-src 'nonce-{nonce}'; sandbox allow-scripts;"
        ),
        "X-Content-Type-Options": "nosniff",
    }
    return body, headers
