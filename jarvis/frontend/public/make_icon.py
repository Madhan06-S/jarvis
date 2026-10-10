"""
Iron Man full-body silhouette icon — transparent background.
Redraws the exact black silhouette with white line details from the reference.
Scales cleanly at all sizes.
"""
from PIL import Image, ImageDraw
import os

def draw_silhouette(size):
    s = size
    # Transparent background
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    BLACK = (0, 0, 0, 255)
    WHITE = (255, 255, 255, 255)
    TRANS = (0, 0, 0, 0)

    def p(x, y):
        return (int(x * s), int(y * s))

    def poly(pts, fill):
        d.polygon([p(x, y) for x, y in pts], fill=fill)

    def ellipse(x1, y1, x2, y2, fill, outline=None, ow=1):
        d.ellipse([p(x1,y1), p(x2,y2)], fill=fill,
                  outline=outline, width=ow)

    def line(pts, fill, width=1):
        d.line([p(x,y) for x,y in pts], fill=fill, width=max(1,width))

    lw = max(1, int(s * 0.012))   # line width scales with size
    lw2 = max(1, int(s * 0.008))

    # ═══════════════════════════════════════════════════════
    # BODY — main silhouette (black filled)
    # ═══════════════════════════════════════════════════════

    # === TORSO ===
    poly([
        (0.32, 0.28), (0.68, 0.28),
        (0.72, 0.34), (0.74, 0.55),
        (0.70, 0.68), (0.62, 0.72),
        (0.55, 0.74), (0.50, 0.75),
        (0.45, 0.74), (0.38, 0.72),
        (0.30, 0.68), (0.26, 0.55),
        (0.28, 0.34),
    ], BLACK)

    # === HEAD ===
    # Neck
    poly([
        (0.42, 0.22), (0.58, 0.22),
        (0.60, 0.28), (0.40, 0.28),
    ], BLACK)

    # Helmet main shape
    poly([
        (0.34, 0.06), (0.66, 0.06),
        (0.72, 0.10), (0.74, 0.16),
        (0.72, 0.22), (0.68, 0.26),
        (0.60, 0.28), (0.40, 0.28),
        (0.32, 0.26), (0.28, 0.22),
        (0.26, 0.16), (0.28, 0.10),
    ], BLACK)

    # Top of helmet (flat top with notch)
    poly([
        (0.38, 0.02), (0.62, 0.02),
        (0.64, 0.06), (0.36, 0.06),
    ], BLACK)

    # Top center notch (white gap)
    poly([
        (0.44, 0.02), (0.56, 0.02),
        (0.57, 0.05), (0.43, 0.05),
    ], WHITE)

    # === SHOULDERS ===
    # Left shoulder
    poly([
        (0.10, 0.26), (0.32, 0.26),
        (0.34, 0.30), (0.32, 0.42),
        (0.26, 0.48), (0.14, 0.48),
        (0.08, 0.42), (0.06, 0.34),
        (0.08, 0.28),
    ], BLACK)

    # Right shoulder
    poly([
        (0.68, 0.26), (0.90, 0.26),
        (0.92, 0.28), (0.94, 0.34),
        (0.92, 0.42), (0.86, 0.48),
        (0.74, 0.48), (0.68, 0.42),
        (0.66, 0.30),
    ], BLACK)

    # === UPPER ARMS ===
    # Left upper arm
    poly([
        (0.06, 0.42), (0.20, 0.42),
        (0.22, 0.48), (0.20, 0.60),
        (0.14, 0.64), (0.08, 0.60),
        (0.04, 0.52),
    ], BLACK)

    # Right upper arm
    poly([
        (0.80, 0.42), (0.94, 0.42),
        (0.96, 0.52), (0.92, 0.60),
        (0.86, 0.64), (0.80, 0.60),
        (0.78, 0.48),
    ], BLACK)

    # === FOREARMS ===
    # Left forearm
    poly([
        (0.06, 0.60), (0.20, 0.60),
        (0.22, 0.66), (0.20, 0.76),
        (0.14, 0.80), (0.06, 0.76),
        (0.04, 0.68),
    ], BLACK)

    # Right forearm
    poly([
        (0.80, 0.60), (0.94, 0.60),
        (0.96, 0.68), (0.94, 0.76),
        (0.86, 0.80), (0.80, 0.76),
        (0.78, 0.66),
    ], BLACK)

    # === FISTS ===
    # Left fist
    poly([
        (0.06, 0.76), (0.20, 0.76),
        (0.22, 0.80), (0.20, 0.88),
        (0.10, 0.90), (0.04, 0.86),
        (0.04, 0.80),
    ], BLACK)
    # Left thumb
    poly([
        (0.18, 0.82), (0.24, 0.80),
        (0.24, 0.86), (0.18, 0.88),
    ], BLACK)

    # Right fist
    poly([
        (0.80, 0.76), (0.94, 0.76),
        (0.96, 0.80), (0.96, 0.86),
        (0.90, 0.90), (0.80, 0.88),
        (0.78, 0.80),
    ], BLACK)
    # Right thumb
    poly([
        (0.76, 0.80), (0.82, 0.80),
        (0.82, 0.86), (0.76, 0.84),
    ], BLACK)

    # === LOWER BODY / HIPS ===
    poly([
        (0.36, 0.72), (0.64, 0.72),
        (0.66, 0.78), (0.62, 0.86),
        (0.55, 0.90), (0.45, 0.90),
        (0.38, 0.86), (0.34, 0.78),
    ], BLACK)

    # === LEGS (partial, cropped at bottom) ===
    # Left leg
    poly([
        (0.36, 0.86), (0.48, 0.86),
        (0.48, 0.98), (0.36, 0.98),
    ], BLACK)
    # Right leg
    poly([
        (0.52, 0.86), (0.64, 0.86),
        (0.64, 0.98), (0.52, 0.98),
    ], BLACK)
    # Crotch gap
    poly([
        (0.46, 0.86), (0.54, 0.86),
        (0.54, 0.94), (0.50, 0.96),
        (0.46, 0.94),
    ], (0, 0, 0, 0))

    # ═══════════════════════════════════════════════════════
    # WHITE LINE DETAILS (armor panel lines)
    # ═══════════════════════════════════════════════════════

    # --- FACE ---
    # Eye slits (white angular shapes)
    poly([
        (0.34, 0.14), (0.46, 0.12),
        (0.47, 0.17), (0.35, 0.19),
    ], WHITE)
    poly([
        (0.54, 0.12), (0.66, 0.14),
        (0.65, 0.19), (0.53, 0.17),
    ], WHITE)

    # Nose/mouth detail
    poly([
        (0.44, 0.20), (0.56, 0.20),
        (0.57, 0.23), (0.53, 0.25),
        (0.47, 0.25), (0.43, 0.23),
    ], WHITE)

    # Chin line
    line([(0.40, 0.26), (0.60, 0.26)], WHITE, lw2)

    # --- CHEST ---
    # Arc reactor (circle)
    ellipse(0.43, 0.38, 0.57, 0.52, WHITE)
    ellipse(0.45, 0.40, 0.55, 0.50, BLACK)

    # Shoulder circles (joint details)
    ellipse(0.24, 0.30, 0.34, 0.40, WHITE)
    ellipse(0.26, 0.32, 0.32, 0.38, BLACK)
    ellipse(0.66, 0.30, 0.76, 0.40, WHITE)
    ellipse(0.68, 0.32, 0.74, 0.38, BLACK)

    # Chest panel lines (horizontal arcs)
    line([(0.34, 0.54), (0.50, 0.52), (0.66, 0.54)], WHITE, lw2)
    line([(0.34, 0.58), (0.50, 0.56), (0.66, 0.58)], WHITE, lw2)
    line([(0.36, 0.62), (0.50, 0.60), (0.64, 0.62)], WHITE, lw2)

    # Neck V-line
    line([(0.46, 0.28), (0.50, 0.34), (0.54, 0.28)], WHITE, lw2)

    # Collar lines
    line([(0.34, 0.30), (0.42, 0.28)], WHITE, lw2)
    line([(0.58, 0.28), (0.66, 0.30)], WHITE, lw2)

    # --- ARMS ---
    # Left arm panel lines
    line([(0.08, 0.50), (0.18, 0.50)], WHITE, lw2)
    line([(0.06, 0.64), (0.18, 0.62)], WHITE, lw2)
    line([(0.08, 0.70), (0.18, 0.68)], WHITE, lw2)

    # Right arm panel lines
    line([(0.82, 0.50), (0.92, 0.50)], WHITE, lw2)
    line([(0.82, 0.62), (0.94, 0.64)], WHITE, lw2)
    line([(0.82, 0.68), (0.92, 0.70)], WHITE, lw2)

    # --- HIPS ---
    # Hip panel lines
    line([(0.38, 0.74), (0.44, 0.76)], WHITE, lw2)
    line([(0.56, 0.76), (0.62, 0.74)], WHITE, lw2)
    line([(0.38, 0.78), (0.44, 0.80)], WHITE, lw2)
    line([(0.56, 0.80), (0.62, 0.78)], WHITE, lw2)

    return img


# ── Generate all sizes ───────────────────────────────────────
sizes = [16, 32, 48, 64, 128, 256]
frames = [draw_silhouette(sz) for sz in sizes]

base_dir = os.path.dirname(os.path.abspath(__file__))
out_ico  = os.path.join(base_dir, "favicon.ico")
out_png  = os.path.join(base_dir, "favicon_preview.png")

frames[-1].save(out_ico, format="ICO",
                sizes=[(sz, sz) for sz in sizes],
                append_images=frames[:-1])
frames[-1].save(out_png)
frames[1].save(os.path.join(base_dir, "preview_32.png"))
frames[2].save(os.path.join(base_dir, "preview_48.png"))

print(f"✅  favicon.ico   → {out_ico}")
print(f"✅  preview.png   → {out_png}")
