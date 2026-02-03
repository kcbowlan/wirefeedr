# animations.py - Visual effects, animation loop, typewriter, boot sequence, gradient buttons

import tkinter as tk
from tkinter import ttk
import math
import random

from PIL import Image, ImageDraw, ImageTk

from config import DARK_THEME
from constants import FLAP_CHARS
import ticker


def start_animation_loop(app):
    """Start the unified animation loop."""
    stop_animation_loop(app)
    app._anim_frame = 0
    # Reset idle status cycling to start fresh
    app._idle_active = True
    app._idle_pause_until = 0
    app._idle_char_pos = 0
    app._idle_display_frames = 0
    anim_tick(app)


def stop_animation_loop(app):
    """Stop all animations."""
    if app._anim_id:
        app.root.after_cancel(app._anim_id)
        app._anim_id = None


def anim_tick(app):
    """Master animation tick at ~30fps."""
    app._anim_frame += 1

    # Ticker
    if app._ticker_running:
        ticker.ticker_step(app)

    # Glitch effect (overrides pulse)
    animate_glitch(app)

    # Pulsing borders (skipped during glitch/flash)
    pulse_borders(app)

    # Sash flash
    animate_sash_flash(app)

    # Header glitch
    animate_header_glitch(app)

    # Feed glows
    animate_feed_glows(app)

    # Title glow
    animate_title_glow(app)

    # Bias balance pulse
    if app._anim_frame % 2 == 0:  # 15fps is plenty for this
        ticker.animate_bias_pulse(app)

    # Trending word cloud
    ticker.animate_trending(app)

    # Neon sweep line
    draw_title_neon_line(app)

    # Status bar cursor blink + clock
    animate_status_bar(app)

    # Typewriter effect
    animate_typewriter(app)

    # Matrix rain (every frame for smooth motion)
    animate_rain(app)

    # Static noise bursts
    animate_static_noise(app)

    # Phosphor afterglow (ticker edges) — redraw every 15 frames to stay on top
    if app._anim_frame % 15 == 0 and app._ticker_running:
        draw_ticker_phosphor(app)

    app._anim_id = app.root.after(33, lambda: anim_tick(app))


def lerp_color(hex1, hex2, t):
    """Linearly interpolate between two hex colors."""
    r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
    r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def create_gradient_image(app, width, height, color1, color2, cache_key=None):
    """Create a diagonal gradient image (top-left=color1, bottom-right=color2).

    Returns a PIL.ImageTk.PhotoImage. Stored in _gradient_cache to prevent GC.
    """
    if width < 1 or height < 1:
        return None
    r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
    r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    # Draw diagonal lines from top-right to bottom-left; each line shares the same
    # diagonal distance factor (0..1) which maps to the color blend.
    max_d = width + height - 2 if (width + height - 2) > 0 else 1
    for d in range(width + height - 1):
        t = d / max_d
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        color = f"#{r:02x}{g:02x}{b:02x}"
        # Each anti-diagonal line: from (d,0) toward (0,d)
        x0 = min(d, width - 1)
        y0 = d - x0
        x1 = max(d - (height - 1), 0)
        y1 = d - x1
        draw.line([(x0, y0), (x1, y1)], fill=color)
    photo = ImageTk.PhotoImage(img)
    key = cache_key or id(photo)
    app._gradient_cache[key] = photo
    return photo


def pulse_borders(app):
    """Animate panel borders with sine-wave pulsing at different intervals."""
    if app._glitch_active or app._sash_flash_active:
        return
    for widget, color_key, period in app._neon_panels:
        t_val = (math.sin(app._anim_frame * (2 * math.pi / period)) + 1) / 2
        bright = DARK_THEME[color_key]
        dim = DARK_THEME[color_key + "_dim"]
        color = lerp_color(dim, bright, t_val)
        widget.configure(highlightbackground=color)


def animate_title_glow(app):
    """Subtle color cycle on the WIREFEEDR title + chromatic aberration flicker."""
    if not hasattr(app, '_title_canvas') or app._title_canvas is None:
        return
    canvas = app._title_canvas
    t_val = (math.sin(app._anim_frame * (2 * math.pi / 180)) + 1) / 2
    color = lerp_color(DARK_THEME["cyan"], DARK_THEME["magenta"], t_val)
    canvas.itemconfigure(app._title_main, fill=color)
    # Chromatic aberration flicker — brief burst at random intervals (5s-1m)
    cx = canvas.winfo_width() // 2
    cy = canvas.winfo_height() // 2
    if cx <= 0 or cy <= 0:
        return
    if not hasattr(app, '_ab_flicker_next'):
        app._ab_flicker_next = app._anim_frame + random.randint(150, 1800)
        app._ab_flicker_end = 0
    if app._ab_flicker_end and app._anim_frame < app._ab_flicker_end:
        # Active flicker — jitter the offsets
        jitter = random.choice([-2, -1, 1, 2])
        canvas.coords(app._title_ab_red, cx - 3 + jitter, cy)
        canvas.coords(app._title_ab_cyan, cx + 3 - jitter, cy)
    elif app._ab_flicker_end and app._anim_frame >= app._ab_flicker_end:
        # Flicker just ended — snap back, schedule next
        canvas.coords(app._title_ab_red, cx - 2, cy)
        canvas.coords(app._title_ab_cyan, cx + 2, cy)
        app._ab_flicker_end = 0
        app._ab_flicker_next = app._anim_frame + random.randint(150, 1800)
    elif app._anim_frame >= app._ab_flicker_next:
        # Start a new flicker burst
        app._ab_flicker_end = app._anim_frame + 6


def draw_title_neon_line(app):
    """Draw two animated neon sweeps chasing around window frame with diagonal gradient colors."""
    top = app._border_top
    bottom = app._border_bottom
    left = app._border_left
    right = app._border_right

    w = top.winfo_width()
    h = left.winfo_height()
    if w < 10 or h < 10:
        return

    t = DARK_THEME
    thickness = 2

    # Full cycle = 300 frames (~10s)
    cycle = app._anim_frame % 300
    pos1 = cycle / 300.0  # Wave 1 position (0 to 1)
    pos2 = (pos1 + 0.5) % 1.0  # Wave 2, opposite side

    perimeter = 2 * w + 2 * h
    max_diag = w + h if (w + h) > 0 else 1  # for diagonal factor normalization

    # Initialize segments on resize -- store (rid, seg_pos, diag_factor)
    if not hasattr(app, '_border_seg_count') or app._border_seg_count != (w, h):
        app._border_seg_count = (w, h)
        for canvas in [top, bottom, left, right]:
            canvas.delete("all")
        app._border_ids = {'top': [], 'bottom': [], 'left': [], 'right': []}

        # Top: left to right -- y=0, x varies
        for x in range(0, w, 4):
            rid = top.create_rectangle(x, 0, x + 4, thickness, fill=t["bg"], outline="")
            diag = x / max_diag  # top-left=0, top-right=~0.5
            app._border_ids['top'].append((rid, x / perimeter, diag))

        # Right: top to bottom -- x=w, y varies
        for y in range(0, h, 4):
            rid = right.create_rectangle(0, y, thickness, y + 4, fill=t["bg"], outline="")
            diag = (w + y) / max_diag  # top-right=~0.5, bottom-right=1.0
            app._border_ids['right'].append((rid, (w + y) / perimeter, min(diag, 1.0)))

        # Bottom: right to left -- y=h, x varies (reversed)
        for x in range(w, 0, -4):
            rid = bottom.create_rectangle(x - 4, 0, x, thickness, fill=t["bg"], outline="")
            diag = (x + h) / max_diag  # bottom-right=1.0, bottom-left=~0.5
            app._border_ids['bottom'].append((rid, (w + h + (w - x)) / perimeter, min(diag, 1.0)))

        # Left: bottom to top -- x=0, y varies (reversed)
        for y in range(h, 0, -4):
            rid = left.create_rectangle(0, y - 4, thickness, y, fill=t["bg"], outline="")
            diag = y / max_diag  # bottom-left=~0.5, top-left=0
            app._border_ids['left'].append((rid, (2 * w + h + (h - y)) / perimeter, diag))

    # Update all segments with dual wave colors + diagonal gradient
    base_color = t["bg"]
    cyan = t["cyan"]
    magenta = t["magenta"]
    for side in ['top', 'right', 'bottom', 'left']:
        canvas = {'top': top, 'right': right, 'bottom': bottom, 'left': left}[side]
        for rid, seg_pos, diag in app._border_ids[side]:
            # Each wave's peak color varies by diagonal position
            wave_color = lerp_color(cyan, magenta, diag)

            # Distance to wave 1
            dist1 = min(abs(seg_pos - pos1), 1.0 - abs(seg_pos - pos1))
            bright1 = max(0, 1.0 - dist1 * 8)

            # Distance to wave 2
            dist2 = min(abs(seg_pos - pos2), 1.0 - abs(seg_pos - pos2))
            bright2 = max(0, 1.0 - dist2 * 8)

            # Blend: both waves use the same position-based color
            total_bright = max(bright1, bright2)
            if total_bright > 0:
                color = lerp_color(base_color, wave_color, total_bright)
            else:
                color = base_color

            canvas.itemconfigure(rid, fill=color)


def animate_status_bar(app):
    """Blink the cursor, update clock, and cycle idle messages."""
    # Cursor blink
    visible = (app._anim_frame // 16) % 2 == 0
    app._cursor_label.configure(
        fg=DARK_THEME["cyan"] if visible else DARK_THEME["status_bg"]
    )

    # Check if we should resume idle cycling
    if not app._idle_active and app._anim_frame >= app._idle_pause_until:
        app._idle_active = True
        app._idle_char_pos = 0
        app._idle_display_frames = 0

    # Idle message typewriter cycling
    if app._idle_active:
        current_message = app._idle_messages[app._idle_message_index]
        full_text = f"... {current_message}"  # Leading dots only

        if app._idle_char_pos < len(full_text):
            # Typewriter effect: add 4 characters every frame (fast typing)
            app._idle_char_pos = min(app._idle_char_pos + 4, len(full_text))
            partial = full_text[:app._idle_char_pos]
            app.status_bar.configure(text=partial)
        else:
            # Message complete, display for random interval then move to next
            app._idle_display_frames += 1
            # Random intervals: 3s, 5s, 7s, 9s, 12s (at 30fps)
            if not hasattr(app, '_idle_current_duration'):
                app._idle_current_duration = random.choice([90, 150, 210, 270, 360])
            if app._idle_display_frames > app._idle_current_duration:
                # Move to next message with new random duration
                app._idle_message_index = (app._idle_message_index + 1) % len(app._idle_messages)
                app._idle_char_pos = 0
                app._idle_display_frames = 0
                app._idle_current_duration = random.choice([90, 150, 210, 270, 360])


# -- Hover glow (Feature 3) -----------------------------------------------

def on_article_hover(app, event):
    """Apply hover highlight to article row under cursor."""
    item = app.articles_tree.identify_row(event.y)
    if item == app._hover_item:
        return
    if app._hover_item:
        try:
            tags = list(app.articles_tree.item(app._hover_item, "tags") or ())
            if "hover" in tags:
                tags.remove("hover")
                app.articles_tree.item(app._hover_item, tags=tags)
        except tk.TclError:
            pass
    app._hover_item = item
    if item:
        try:
            tags = list(app.articles_tree.item(item, "tags") or ())
            if "hover" not in tags:
                tags.append("hover")
                app.articles_tree.item(item, tags=tags)
        except tk.TclError:
            pass


def on_article_leave(app, event):
    """Clear hover when mouse leaves articles tree."""
    if app._hover_item:
        try:
            tags = list(app.articles_tree.item(app._hover_item, "tags") or ())
            if "hover" in tags:
                tags.remove("hover")
                app.articles_tree.item(app._hover_item, tags=tags)
        except tk.TclError:
            pass
        app._hover_item = None


# -- Glitch effect (Feature 1) --------------------------------------------

def start_glitch(app):
    """Activate a pulse sweep effect on refresh start."""
    app._glitch_active = True
    app._glitch_start_frame = app._anim_frame
    app._glitch_duration = 30  # ~1s at 30fps
    # Trigger static noise burst alongside glitch
    app._static_noise_next = app._anim_frame


def animate_glitch(app):
    """Two bright pulses that sweep across panels, then fade."""
    if not app._glitch_active:
        return
    elapsed = app._anim_frame - app._glitch_start_frame
    if elapsed < 0:
        elapsed += 3600
    if elapsed >= app._glitch_duration:
        app._glitch_active = False
        return
    t = elapsed / app._glitch_duration
    # Two pulses using a sine wave
    import math
    pulse = abs(math.sin(t * math.pi * 2.5))
    # Fade out over time
    envelope = 1.0 - (t ** 0.7)
    brightness = pulse * envelope
    # Overshoot to white on the first pulse
    accent_colors = {"cyan": DARK_THEME["cyan_dim"], "magenta": DARK_THEME["magenta_dim"]}
    hot_colors = {"cyan": "#aaffff", "magenta": "#ffaaff"}
    for widget, color_key, _ in app._neon_panels:
        dim = accent_colors.get(color_key, DARK_THEME["cyan_dim"])
        hot = hot_colors.get(color_key, "#aaffff")
        color = lerp_color(dim, hot, brightness)
        widget.configure(highlightbackground=color)
    # Pulse treeview backgrounds
    tree_bg = lerp_color(DARK_THEME["bg"], "#102838", brightness)
    style = ttk.Style()
    style.configure("Treeview", fieldbackground=tree_bg, background=tree_bg)


# -- Sash flash (Feature 4) -----------------------------------------------

def on_sash_press(app, event):
    """Detect if press is on a PanedWindow sash."""
    try:
        result = str(event.widget.identify(event.x, event.y))
        app._sash_dragging = "sash" in result or "separator" in result
    except Exception:
        # Fallback: check if click is near a sash coordinate
        try:
            paned = event.widget
            for i in range(len(paned.panes()) - 1):
                sx, sy = paned.sash_coord(i)
                orient = str(paned.cget("orient"))
                if orient == "horizontal":
                    if abs(event.y - sy) < 8:
                        app._sash_dragging = True
                        return
                else:
                    if abs(event.x - sx) < 8:
                        app._sash_dragging = True
                        return
        except Exception:
            pass
        app._sash_dragging = False


def on_sash_release(app, event):
    """Trigger border flash on sash release."""
    if app._sash_dragging:
        app._sash_flash_active = True
        app._sash_flash_end_frame = (app._anim_frame + 10) % 3600
        app._sash_dragging = False


def animate_sash_flash(app):
    """Fade panel borders from white back to normal after sash release."""
    if not app._sash_flash_active:
        return
    remaining = (app._sash_flash_end_frame - app._anim_frame) % 3600
    if remaining > 10 or remaining == 0:
        app._sash_flash_active = False
        return
    t = remaining / 10.0
    flash_color = lerp_color(DARK_THEME["cyan"], "#ffffff", t)
    for widget, _, _ in app._neon_panels:
        widget.configure(highlightbackground=flash_color)


# -- Header glitch effect -------------------------------------------------

_HEADER_PANELS = [
    ("_feeds_header", "FEEDS"),
    ("_articles_header", None),    # dynamic text — read from canvas
    ("_preview_header", "PREVIEW"),
    ("_trending_header", "TRENDING"),
]


def animate_header_glitch(app):
    """Rare brief text glitch on panel headers: char scramble + offset jitter."""
    if app._header_glitch_active:
        # Advance glitch frame
        app._header_glitch_frame += 1
        canvas = getattr(app, app._header_glitch_target, None)
        if canvas is None or app._header_glitch_frame > app._header_glitch_duration:
            # End glitch — restore
            _header_glitch_end(app)
            return
        # Scramble characters — only ~15% chance per char for subtle effect
        original = app._header_glitch_original
        scrambled = []
        for ch in original:
            if ch == " ":
                scrambled.append(" ")
            elif random.random() < 0.15:
                scrambled.append(random.choice(FLAP_CHARS))
            else:
                scrambled.append(ch)
        scrambled_text = "".join(scrambled)
        # Apply to canvas
        text_items = canvas.find_withtag("header_text")
        if text_items:
            tid = text_items[0]
            canvas.itemconfigure(tid, text=scrambled_text)
            # Subtle offset jitter (±1px)
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            jitter_x = random.randint(-1, 1)
            canvas.coords(tid, w // 2 + jitter_x, h // 2)
            # Subtle color flicker — mostly cyan, occasional hint of magenta
            color = random.choices(
                [DARK_THEME["cyan"], DARK_THEME["magenta"]],
                weights=[85, 15],
            )[0]
            canvas.itemconfigure(tid, fill=color)
    else:
        # Trigger check
        if app._anim_frame >= app._header_glitch_next:
            # Pick a random header
            attr, static_text = random.choice(_HEADER_PANELS)
            canvas = getattr(app, attr, None)
            if canvas is None:
                return
            # Read current text from canvas
            text_items = canvas.find_withtag("header_text")
            if not text_items:
                return
            original = canvas.itemcget(text_items[0], "text")
            if not original:
                original = static_text or ""
            app._header_glitch_active = True
            app._header_glitch_frame = 0
            app._header_glitch_duration = random.randint(8, 12)
            app._header_glitch_target = attr
            app._header_glitch_original = original
            # Schedule next glitch (15-30s at 30fps)
            app._header_glitch_next = app._anim_frame + random.randint(450, 900)


def _header_glitch_end(app):
    """Restore header after glitch ends."""
    canvas = getattr(app, app._header_glitch_target, None)
    if canvas is not None:
        text_items = canvas.find_withtag("header_text")
        if text_items:
            tid = text_items[0]
            canvas.itemconfigure(tid, text=app._header_glitch_original)
            # Reset position to center
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            canvas.coords(tid, w // 2, h // 2)
            # Restore color — all headers use cyan text
            canvas.itemconfigure(tid, fill=DARK_THEME["cyan"])
    app._header_glitch_active = False
    app._header_glitch_target = None
    app._header_glitch_original = ""


# -- Feed glow (Feature 2) ------------------------------------------------

def snapshot_feed_counts(app):
    """Capture unread counts before refresh to detect new articles."""
    feeds = app.storage.get_feeds()
    app._pre_refresh_counts = {
        feed["id"]: app.storage.get_article_count(feed["id"], unread_only=True)
        for feed in feeds
    }


def detect_new_article_feeds(app):
    """Start glow on feeds that received new articles."""
    feeds = app.storage.get_feeds()
    for feed in feeds:
        old_count = app._pre_refresh_counts.get(feed["id"], 0)
        new_count = app.storage.get_article_count(feed["id"], unread_only=True)
        if new_count > old_count:
            iid = f"feed_{feed['id']}"
            app._glowing_feeds[iid] = (app._anim_frame + 90) % 3600


def animate_feed_glows(app):
    """Pulse foreground color of feeds with new articles."""
    if not app._glowing_feeds:
        return
    expired = []
    t_val = (math.sin(app._anim_frame * (2 * math.pi / 60)) + 1) / 2
    color = lerp_color(DARK_THEME["cyan_dim"], DARK_THEME["cyan"], t_val)
    for iid, end_frame in app._glowing_feeds.items():
        if app._anim_frame == end_frame:
            expired.append(iid)
            continue
        try:
            tag_name = f"glow_{iid}"
            app.feeds_tree.tag_configure(tag_name, foreground=color)
            current_tags = list(app.feeds_tree.item(iid, "tags") or ())
            if tag_name not in current_tags:
                current_tags.append(tag_name)
                app.feeds_tree.item(iid, tags=current_tags)
        except tk.TclError:
            expired.append(iid)
    for iid in expired:
        del app._glowing_feeds[iid]
        try:
            tag_name = f"glow_{iid}"
            current_tags = list(app.feeds_tree.item(iid, "tags") or ())
            if tag_name in current_tags:
                current_tags.remove(tag_name)
                app.feeds_tree.item(iid, tags=current_tags)
        except tk.TclError:
            pass


# -- Typewriter effect (Feature 5) ----------------------------------------

def start_typewriter(app, text, article_id):
    """Begin typewriter animation for article preview."""
    cancel_typewriter(app)
    app._typewriter_active = True
    app._typewriter_full_text = text
    app._typewriter_words = text.split(" ")
    app._typewriter_pos = 0
    app._typewriter_article_id = article_id


def cancel_typewriter(app):
    """Cancel in-progress typewriter animation."""
    app._typewriter_active = False
    app._typewriter_words = []
    app._typewriter_pos = 0
    app._typewriter_article_id = None
    app._typewriter_pending_highlight = False
    app._typewriter_full_text = ""


def animate_typewriter(app):
    """Insert next chunk of words into preview with live highlighting."""
    import highlighting

    if not app._typewriter_active:
        return
    if app.selected_article_id != app._typewriter_article_id:
        cancel_typewriter(app)
        return
    if app._typewriter_pos >= len(app._typewriter_words):
        finish_typewriter(app)
        return
    end_pos = min(app._typewriter_pos + app._typewriter_chunk_size,
                  len(app._typewriter_words))
    app._typewriter_pos = end_pos
    # Rebuild text from words typed so far, apply full highlighting
    partial_text = " ".join(app._typewriter_words[:app._typewriter_pos])
    app.preview_text.configure(state=tk.NORMAL)
    app.preview_text.delete("1.0", tk.END)
    highlighting.apply_highlighting(app, app.preview_text, partial_text)
    app.preview_text.configure(state=tk.DISABLED)
    app.preview_text.see(tk.END)


def finish_typewriter(app):
    """Finalize typewriter -- add related articles."""
    app._typewriter_active = False
    # Clear previous related article targets
    app._related_article_targets = {}

    # Related articles
    article_id = app._typewriter_article_id
    if hasattr(app, "cluster_map") and article_id in app.cluster_map:
        cluster = app.cluster_map[article_id]
        if cluster["count"] > 1:
            app.preview_text.configure(state=tk.NORMAL)
            # Header in yellow with instruction
            start = app.preview_text.index(tk.END)
            app.preview_text.insert(tk.END, "\n\n─── RELATED ARTICLES ───\n───── Click to Read ─────\n\n")
            app.preview_text.tag_add("related_header", start, tk.END)
            app.preview_text.tag_add("related_header", start, tk.END)

            # Related items in yellow (clickable)
            for i, related in enumerate(cluster["articles"][1:]):
                source = related.get("feed_name", "Unknown")
                score = related.get("noise_score", 0)
                related_id = related.get("id")

                # Create unique tag for this related article
                tag_name = f"related_link_{related_id}"

                # Store the article ID for this tag
                app._related_article_targets[tag_name] = related_id

                # Configure tag appearance (no underline)
                app.preview_text.tag_configure(
                    tag_name,
                    foreground=DARK_THEME["neon_yellow"]
                )

                # Get position before insert
                line_start = app.preview_text.index("end-1c")

                # Insert the text
                text = f"  [{source}] {related['title']} ({score})\n"
                app.preview_text.insert(tk.END, text)

                # Apply tag to the inserted text
                line_end = app.preview_text.index("end-1c")
                app.preview_text.tag_add(tag_name, line_start, line_end)

            app.preview_text.configure(state=tk.DISABLED)

            # Bind handlers for related links
            app.preview_text.bind("<Button-1>", lambda e: on_preview_click(app, e), add=True)
            app.preview_text.bind("<Motion>", lambda e: on_preview_motion(app, e), add=True)

    app._typewriter_article_id = None


def on_preview_click(app, event):
    """Handle clicks on the preview text, checking for related article links."""
    # Get the index at click position
    index = app.preview_text.index(f"@{event.x},{event.y}")
    # Check all tags at this position
    tags = app.preview_text.tag_names(index)
    for tag in tags:
        if tag.startswith("related_link_") and tag in app._related_article_targets:
            article_id = app._related_article_targets[tag]
            navigate_to_article(app, article_id)
            return


def on_preview_motion(app, event):
    """Change cursor when hovering over related article links."""
    index = app.preview_text.index(f"@{event.x},{event.y}")
    tags = app.preview_text.tag_names(index)
    is_link = any(tag.startswith("related_link_") for tag in tags)
    app.preview_text.configure(cursor="hand2" if is_link else "")


def navigate_to_article(app, article_id):
    """Navigate to and display a specific article."""
    if not article_id:
        return
    # Find and select the article in the tree
    for item in app.articles_tree.get_children():
        if int(item) == article_id:
            app.articles_tree.selection_set(item)
            app.articles_tree.see(item)
            app._on_article_select(None)
            return
    # Article not in current view - fetch and display directly
    article = app.storage.get_article(article_id)
    if article:
        app._display_article(article)


# -- Boot sequence ---------------------------------------------------------

def play_boot_sequence(app):
    """Play cyberpunk boot-up animation."""
    app._boot_overlay = tk.Canvas(
        app.root, bg=DARK_THEME["bg"], highlightthickness=0
    )
    app._boot_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
    app.root.update_idletasks()
    tk.Misc.lift(app._boot_overlay)

    app._boot_lines = [
        "WIREFEEDR v2.4",
        "INITIALIZING NEURAL FEED PARSER",
        "CONNECTING TO NEWS GRID",
        "BIAS DETECTION MATRIX: ONLINE",
        "SIGNAL LOCKED. WELCOME, OPERATOR.",
    ]
    app._boot_step = 0

    app.root.after(200, lambda: boot_next_line(app))


def boot_next_line(app):
    """Start typing the next boot line character-by-character."""
    if app._boot_step >= len(app._boot_lines):
        app.root.after(400, lambda: boot_fade_out(app))
        return

    y = 200 + app._boot_step * 28
    text = app._boot_lines[app._boot_step]
    color = DARK_THEME["cyan"] if app._boot_step < len(app._boot_lines) - 1 else DARK_THEME["magenta"]

    # Create text item with empty string, then type into it
    text_id = app._boot_overlay.create_text(
        60, y, text="", fill=color, anchor=tk.W,
        font=("Consolas", 11, "bold")
    )
    app._boot_char_pos = 0
    app._boot_current_text = text
    app._boot_text_id = text_id
    boot_type_char(app)


def boot_type_char(app):
    """Type one character of the current boot line."""
    app._boot_char_pos += 3
    partial = app._boot_current_text[:app._boot_char_pos]
    app._boot_overlay.itemconfigure(app._boot_text_id, text=partial + "_")

    if app._boot_char_pos >= len(app._boot_current_text):
        # Line done — remove cursor, pause, then next line
        app._boot_overlay.itemconfigure(app._boot_text_id, text=app._boot_current_text)
        app._boot_step += 1
        app.root.after(60, lambda: boot_next_line(app))
    else:
        app.root.after(5, lambda: boot_type_char(app))


def boot_fade_out(app):
    """Remove boot overlay and start animations."""
    app._boot_overlay.destroy()
    start_animation_loop(app)



# -- Gradient buttons ------------------------------------------------------

def on_toolbar_configure(app, event):
    """Redraw toolbar gradient on resize."""
    w = event.width
    h = event.height
    if w < 10 or h < 2:
        return
    photo = create_gradient_image(app, w, h, "#0a1028", "#280a18", cache_key="toolbar_grad")
    if photo:
        app._toolbar_canvas.delete("all")
        app._toolbar_canvas.create_image(0, 0, anchor=tk.NW, image=photo)


def draw_panel_header(app, canvas, text, color1, color2, cache_key):
    """Draw a gradient background and centered text on a panel header canvas."""
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w < 10 or h < 2:
        return
    photo = create_gradient_image(app, w, h, color1, color2, cache_key=cache_key)
    if photo:
        canvas.delete("all")
        canvas.create_image(0, 0, anchor=tk.NW, image=photo, tags="bg")
        canvas.create_text(
            w // 2, h // 2, text=text, fill=DARK_THEME["cyan"],
            font=("Consolas", 9, "bold"), anchor=tk.CENTER, tags="header_text"
        )


def create_gradient_button(app, parent, text, command, disabled=False):
    """Create a canvas-based button with diagonal gradient fill.

    Returns the canvas widget. Stores an '_enabled' attribute for state management.
    """
    t = DARK_THEME
    font = ("Consolas", 9)
    # Measure text to size the canvas
    tmp = tk.Label(parent, text=text, font=font)
    tmp.update_idletasks()
    text_w = tmp.winfo_reqwidth()
    text_h = tmp.winfo_reqheight()
    tmp.destroy()
    pad_x, pad_y = 12, 4
    btn_w = text_w + pad_x * 2
    btn_h = text_h + pad_y * 2

    canvas = tk.Canvas(parent, width=btn_w, height=btn_h,
                       highlightthickness=0, bg=t["bg_tertiary"], cursor="hand2")
    canvas._btn_text = text
    canvas._btn_command = command
    canvas._btn_w = btn_w
    canvas._btn_h = btn_h
    canvas._btn_enabled = not disabled

    # Draw initial state
    draw_gradient_btn(app, canvas, hover=False)

    # Bindings
    canvas.bind("<Enter>", lambda e, c=canvas: on_grad_btn_enter(app, c))
    canvas.bind("<Leave>", lambda e, c=canvas: on_grad_btn_leave(app, c))
    canvas.bind("<Button-1>", lambda e, c=canvas: on_grad_btn_click(app, c))

    return canvas


def draw_gradient_btn(app, canvas, hover=False):
    """Redraw a gradient button's background and text."""
    w = canvas._btn_w
    h = canvas._btn_h
    enabled = canvas._btn_enabled
    t = DARK_THEME

    if not enabled:
        c1, c2 = "#0c0c18", "#180c14"
        text_color = t["fg_secondary"]
    elif hover:
        c1, c2 = "#2a1250", "#50122a"
        text_color = t["fg_highlight"]
    else:
        c1, c2 = "#0a1028", "#280a18"
        text_color = t["cyan"]

    key = f"gbtn_{id(canvas)}_{hover}_{enabled}"
    photo = create_gradient_image(app, w, h, c1, c2, cache_key=key)
    canvas.delete("all")
    if photo:
        canvas.create_image(0, 0, anchor=tk.NW, image=photo)
    canvas.create_text(
        w // 2, h // 2, text=canvas._btn_text, fill=text_color,
        font=("Consolas", 9), anchor=tk.CENTER
    )


def on_grad_btn_enter(app, canvas):
    if canvas._btn_enabled:
        draw_gradient_btn(app, canvas, hover=True)


def on_grad_btn_leave(app, canvas):
    draw_gradient_btn(app, canvas, hover=False)


def on_grad_btn_click(app, canvas):
    if canvas._btn_enabled and canvas._btn_command:
        canvas._btn_command()


# -- Matrix rain (preview placeholder) ------------------------------------

# Rain character pool — katakana, greek, cyrillic, symbols, digits
_RAIN_CHARS = (
    "\u30a2\u30a4\u30a6\u30a8\u30aa\u30ab\u30ad\u30af\u30b1\u30b3"  # katakana
    "\u30b5\u30b7\u30b9\u30bb\u30bd\u30bf\u30c1\u30c4\u30c6\u30c8"
    "\u30ca\u30cb\u30cc\u30cd\u30ce\u30cf\u30d2\u30d5\u30d8\u30db"
    "\u30de\u30df\u30e0\u30e1\u30e2\u30e4\u30e6\u30e8\u30e9\u30ea"
    "\u30eb\u30ec\u30ed\u30ef\u30f2\u30f3"
    "\u0394\u0398\u039b\u039e\u03a0\u03a3\u03a6\u03a8\u03a9"          # greek
    "\u0414\u0416\u0418\u041b\u042f\u0424\u0426\u0428\u0429\u042d"    # cyrillic
    "\u2206\u2207\u221e\u2261\u2248\u2234\u2237\u22c5\u2302"          # math/symbols
    "0123456789"
)

# Color gradient for rain trails: bright head -> fading tail (cyan/magenta, subtle)
_RAIN_COLORS_CYAN = ["#2a6677", "#1a4455", "#0f2d3a", "#081c25", "#04111a"]
_RAIN_COLORS_MAGENTA = ["#6a2a6a", "#441a44", "#2d0f2d", "#1c081c", "#110411"]


def on_rain_configure(app, event):
    """Recalculate rain columns when canvas resizes."""
    if not app._rain_active or not app._rain_canvas:
        return
    w = event.width
    h = event.height
    if w < 10 or h < 10:
        return
    new_col_count = max(1, w // app._rain_col_width)
    old_col_count = len(app._rain_columns)
    if new_col_count == old_col_count:
        return
    # Rebuild columns
    canvas = app._rain_canvas
    canvas.delete("all")
    app._rain_columns = []
    for i in range(new_col_count):
        app._rain_columns.append({
            "drops": [],
            "spawn_cooldown": random.randint(0, 60),  # staggered start
        })
    _draw_rain_placeholder_text(app)


def _draw_rain_placeholder_text(app):
    """Draw 'SELECT ARTICLE TO VIEW' centered on rain canvas with backdrop."""
    canvas = app._rain_canvas
    if not canvas or not canvas.winfo_exists():
        return
    canvas.delete("placeholder")
    canvas.update_idletasks()
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w < 10 or h < 10:
        return
    cx, cy = w // 2, h // 2
    text = "SELECT ARTICLE TO VIEW"
    # Backdrop rectangle
    font = ("Consolas", 12, "bold")
    # Measure text by creating temporary item
    tid = canvas.create_text(cx, cy, text=text, font=font, fill="", anchor=tk.CENTER)
    bbox = canvas.bbox(tid)
    canvas.delete(tid)
    if bbox:
        pad = 16
        canvas.create_rectangle(
            bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad,
            fill=DARK_THEME["bg_tertiary"], outline=DARK_THEME["cyan"],
            width=1, tags="placeholder"
        )
    canvas.create_text(
        cx, cy, text=text, font=font,
        fill=DARK_THEME["cyan"], anchor=tk.CENTER, tags="placeholder"
    )


def animate_rain(app):
    """Advance the matrix rain animation one step."""
    if not app._rain_active or not app._rain_canvas:
        return
    canvas = app._rain_canvas
    if not canvas.winfo_exists():
        return
    try:
        w = canvas.winfo_width()
        h = canvas.winfo_height()
    except tk.TclError:
        return
    if w < 10 or h < 10:
        return

    bg_color = DARK_THEME["bg_tertiary"]

    for col_idx, col in enumerate(app._rain_columns):
        x = col_idx * app._rain_col_width + app._rain_col_width // 2

        # Spawn new drops (subtle — low chance, long cooldowns)
        col["spawn_cooldown"] -= 1
        if col["spawn_cooldown"] <= 0 and random.random() < 0.01:
            length = random.randint(3, 10)
            speed = random.uniform(0.7, 2.0)
            colors = random.choice([_RAIN_COLORS_CYAN, _RAIN_COLORS_MAGENTA])
            drop = {
                "y": -length * app._rain_row_height,
                "speed": speed,
                "length": length,
                "chars": [random.choice(_RAIN_CHARS) for _ in range(length)],
                "char_ids": [],
                "colors": colors,
            }
            col["drops"].append(drop)
            col["spawn_cooldown"] = random.randint(30, 90)

        # Update existing drops
        expired = []
        for drop in col["drops"]:
            drop["y"] += drop["speed"]

            # Mutate a random char every 4 frames
            if app._anim_frame % 4 == 0 and drop["chars"]:
                idx = random.randint(0, len(drop["chars"]) - 1)
                drop["chars"][idx] = random.choice(_RAIN_CHARS)

            # Remove old canvas items
            for cid in drop["char_ids"]:
                try:
                    canvas.delete(cid)
                except tk.TclError:
                    pass
            drop["char_ids"] = []

            # Draw trail characters
            head_y = drop["y"]
            drop_colors = drop.get("colors", _RAIN_COLORS_CYAN)
            for i in range(drop["length"]):
                cy = head_y - i * app._rain_row_height
                if cy < -app._rain_row_height or cy > h + app._rain_row_height:
                    continue
                # Color: head is bright, tail fades
                color_idx = min(i, len(drop_colors) - 1)
                color = drop_colors[color_idx]
                char = drop["chars"][i] if i < len(drop["chars"]) else "?"
                cid = canvas.create_text(
                    x, cy, text=char, fill=color,
                    font=app._rain_font, anchor=tk.CENTER
                )
                drop["char_ids"].append(cid)

            # Check if drop has scrolled off the bottom
            tail_y = head_y - (drop["length"] - 1) * app._rain_row_height
            if tail_y > h + app._rain_row_height:
                expired.append(drop)

        # Clean up expired drops
        for drop in expired:
            for cid in drop["char_ids"]:
                try:
                    canvas.delete(cid)
                except tk.TclError:
                    pass
            col["drops"].remove(drop)

    # Fade placeholder text between cyan and magenta
    t_val = (math.sin(app._anim_frame * (2 * math.pi / 180)) + 1) / 2
    ph_color = lerp_color(DARK_THEME["cyan"], DARK_THEME["magenta"], t_val)
    for item_id in canvas.find_withtag("placeholder"):
        item_type = canvas.type(item_id)
        if item_type == "text":
            canvas.itemconfigure(item_id, fill=ph_color)
        elif item_type == "rectangle":
            canvas.itemconfigure(item_id, outline=ph_color)

    # Keep placeholder text on top
    canvas.tag_raise("placeholder")


# -- Static noise bursts ---------------------------------------------------

_NOISE_DIM_COLORS = ["#2a2a3e", "#303048", "#383850", "#252538", "#2e2e44"]
_NOISE_ACCENT_COLORS = [DARK_THEME["cyan_dim"], DARK_THEME["magenta_dim"]]


def animate_static_noise(app):
    """Manage static noise bursts — called each anim_tick."""
    if app._static_noise_active:
        app._static_noise_frame += 1
        if app._static_noise_frame >= app._static_noise_duration:
            _end_static_noise(app)
            return
        # Destroy previous frame's pixels, spawn new ones at random positions
        for w in app._static_noise_canvases:
            try:
                w.destroy()
            except tk.TclError:
                pass
        app._static_noise_canvases = []
        for panel in app._static_noise_panels:
            try:
                if not panel.winfo_exists():
                    continue
                pw = panel.winfo_width()
                ph = panel.winfo_height()
                if pw < 20 or ph < 20:
                    continue
                count = random.randint(15, 30)
                for _ in range(count):
                    size = random.randint(2, 6)
                    x = random.randint(0, pw - size)
                    y = random.randint(0, ph - size)
                    if random.random() < 0.10:
                        color = random.choice(_NOISE_ACCENT_COLORS)
                    else:
                        color = random.choice(_NOISE_DIM_COLORS)
                    pixel = tk.Frame(panel, width=size, height=size, bg=color,
                                     highlightthickness=0, bd=0)
                    pixel.place(x=x, y=y, width=size, height=size)
                    app._static_noise_canvases.append(pixel)
            except tk.TclError:
                pass
    else:
        if app._anim_frame >= app._static_noise_next:
            _start_static_noise(app)


def _start_static_noise(app):
    """Pick 1-3 panels, begin noise burst with scattered pixel widgets."""
    candidates = []
    if hasattr(app, 'feeds_frame'):
        candidates.append(app.feeds_frame)
    if hasattr(app, 'articles_frame'):
        candidates.append(app.articles_frame)
    if hasattr(app, 'preview_frame'):
        candidates.append(app.preview_frame)
    if not candidates:
        return
    count = random.randint(1, min(3, len(candidates)))
    app._static_noise_panels = random.sample(candidates, count)
    app._static_noise_canvases = []
    app._static_noise_active = True
    app._static_noise_frame = 0
    app._static_noise_duration = random.randint(15, 25)
    app._static_noise_next = app._anim_frame + random.randint(600, 1200)


def _end_static_noise(app):
    """Destroy noise pixel widgets and reset state."""
    for w in app._static_noise_canvases:
        try:
            w.destroy()
        except tk.TclError:
            pass
    app._static_noise_canvases = []
    app._static_noise_panels = []
    app._static_noise_active = False
    app._static_noise_frame = 0


# -- Phosphor afterglow (ticker edges) -------------------------------------

_PHOSPHOR_GLOW_WIDTH = 55  # px wide on each edge
_PHOSPHOR_STEPS = 18       # number of gradient steps per edge


def draw_ticker_phosphor(app):
    """Draw smooth phosphor glow at left/right edges of the ticker canvas."""
    canvas = app.ticker_canvas
    if canvas is None:
        return
    try:
        w = canvas.winfo_width()
        h = canvas.winfo_height()
    except tk.TclError:
        return
    if w < 100 or h < 5:
        return

    canvas.delete("phosphor_glow")

    bg = DARK_THEME["bg_secondary"]
    bar_w = max(1, _PHOSPHOR_GLOW_WIDTH // _PHOSPHOR_STEPS)
    pulse = 0.85 + 0.15 * math.sin(app._anim_frame * 0.04)

    for i in range(_PHOSPHOR_STEPS):
        t = i / _PHOSPHOR_STEPS  # 0 at edge, 1 at inner
        # Quadratic falloff for smoother fade
        intensity = (1.0 - t) ** 2 * 0.65 * pulse

        # Left edge: cyan
        color_l = lerp_color(bg, DARK_THEME["cyan"], intensity)
        x = i * bar_w
        canvas.create_rectangle(
            x, 0, x + bar_w, h, fill=color_l, outline="", tags="phosphor_glow"
        )

        # Right edge: magenta
        color_r = lerp_color(bg, DARK_THEME["magenta"], intensity)
        x = w - (i + 1) * bar_w
        canvas.create_rectangle(
            x, 0, x + bar_w, h, fill=color_r, outline="", tags="phosphor_glow"
        )

    # Draw glow behind text so ticker items remain visible
    canvas.tag_lower("phosphor_glow")


# -- Konami code easter egg ------------------------------------------------

def konami_check(app, event):
    """Track key presses and trigger easter egg on Konami code match."""
    if app._konami_active:
        return
    app._konami_seq.append(event.keysym)
    app._konami_seq = app._konami_seq[-10:]
    if app._konami_seq == app._konami_code:
        app._konami_seq = []
        _konami_trigger(app)


def _konami_trigger(app):
    """Create full-screen overlay with static burst, then type secret message."""
    app._konami_active = True
    try:
        w = app.root.winfo_width()
        h = app.root.winfo_height()
    except tk.TclError:
        app._konami_active = False
        return

    overlay = tk.Canvas(app.root, bg="#000000", highlightthickness=0)
    overlay.place(x=0, y=0, width=w, height=h)
    app._konami_overlay = overlay

    # Brief static noise burst on overlay
    noise_colors = ["#2a2a3e", "#303048", "#383850", "#252538", "#2e2e44"]
    accent_colors = [DARK_THEME["cyan_dim"], DARK_THEME["magenta_dim"]]
    for _ in range(80):
        size = random.randint(2, 6)
        x = random.randint(0, w - size)
        y = random.randint(0, h - size)
        color = random.choice(accent_colors) if random.random() < 0.10 else random.choice(noise_colors)
        overlay.create_rectangle(x, y, x + size, y + size, fill=color, outline="")

    app.root.after(200, lambda: _konami_type_message(app))


def _konami_type_message(app):
    """Clear static and begin typing the secret message."""
    try:
        overlay = app._konami_overlay
        overlay.delete("all")
    except tk.TclError:
        app._konami_active = False
        return

    app._konami_lines = ["//ACCESS DENIED\\\\"]
    app._konami_step = 0
    _konami_next_line(app)


def _konami_next_line(app):
    """Start typing the next message line character-by-character."""
    if app._konami_step >= len(app._konami_lines):
        app.root.after(1500, lambda: _konami_fade_out(app))
        return

    try:
        overlay = app._konami_overlay
        w = overlay.winfo_width()
        h = overlay.winfo_height()
    except tk.TclError:
        app._konami_active = False
        return

    text = app._konami_lines[app._konami_step]
    y = h // 2 + app._konami_step * 28

    text_id = overlay.create_text(
        w // 2, y, text="", fill=DARK_THEME["magenta"], anchor=tk.CENTER,
        font=("Consolas", 16, "bold")
    )
    app._konami_char_pos = 0
    app._konami_current_text = text
    app._konami_text_id = text_id
    _konami_type_char(app)


def _konami_type_char(app):
    """Type one chunk of the current message line."""
    app._konami_char_pos += 2
    partial = app._konami_current_text[:app._konami_char_pos]
    try:
        app._konami_overlay.itemconfigure(app._konami_text_id, text=partial + "_")
    except tk.TclError:
        app._konami_active = False
        return

    if app._konami_char_pos >= len(app._konami_current_text):
        app._konami_overlay.itemconfigure(app._konami_text_id, text=app._konami_current_text)
        app._konami_step += 1
        app.root.after(60, lambda: _konami_next_line(app))
    else:
        app.root.after(15, lambda: _konami_type_char(app))


def _konami_fade_out(app):
    """Destroy overlay and reset state."""
    try:
        app._konami_overlay.destroy()
    except (tk.TclError, AttributeError):
        pass
    app._konami_active = False


# -- CRT shutdown animation ------------------------------------------------

def play_crt_shutdown(app):
    """Start CRT power-off animation: overlay black canvas, begin phase chain."""
    try:
        w = app.root.winfo_width()
        h = app.root.winfo_height()
    except tk.TclError:
        _crt_shutdown_finish(app)
        return

    app._shutdown_canvas = tk.Canvas(app.root, bg="#000000", highlightthickness=0)
    app._shutdown_canvas.place(x=0, y=0, width=w, height=h)
    tk.Misc.lift(app._shutdown_canvas)
    app._shutdown_w = w
    app._shutdown_h = h
    app._shutdown_phase = 1
    app._shutdown_frame = 0

    app.root.after(16, lambda: _crt_shutdown_tick(app))


def _crt_shutdown_tick(app):
    """Per-frame CRT shutdown rendering. Phases: vertical compress, horizontal compress, dot fade."""
    try:
        canvas = app._shutdown_canvas
        if not canvas or not canvas.winfo_exists():
            _crt_shutdown_finish(app)
            return

        w = app._shutdown_w
        h = app._shutdown_h
        cx = w // 2
        cy = h // 2

        canvas.delete("all")
        # Black background fill
        canvas.create_rectangle(0, 0, w, h, fill="#000000", outline="")

        phase = app._shutdown_phase
        frame = app._shutdown_frame

        if phase == 1:
            # Vertical compress: bright bar shrinks to 2px horizontal line
            total_frames = 8
            t = min(frame / total_frames, 1.0)
            ease = t * t  # ease-in
            bar_h = max(2, int(h * (1.0 - ease)))
            y1 = cy - bar_h // 2
            y2 = cy + bar_h // 2

            # Cyan glow behind
            glow_expand = 4
            glow_color = lerp_color("#003344", "#000000", ease)
            canvas.create_rectangle(0, y1 - glow_expand, w, y2 + glow_expand,
                                    fill=glow_color, outline="")
            # Chromatic aberration: red channel offset above
            red_color = lerp_color("#ff4444", "#000000", ease)
            canvas.create_rectangle(0, y1 - 3, w, y2 - 3, fill=red_color, outline="")
            # Chromatic aberration: blue channel offset below
            blue_color = lerp_color("#4444ff", "#000000", ease)
            canvas.create_rectangle(0, y1 + 3, w, y2 + 3, fill=blue_color, outline="")
            # Bright bar (main white/cyan channel on top)
            bar_color = lerp_color("#ffffff", "#88ffff", ease)
            canvas.create_rectangle(0, y1, w, y2, fill=bar_color, outline="")

            app._shutdown_frame += 1
            if frame >= total_frames:
                app._shutdown_phase = 2
                app._shutdown_frame = 0

        elif phase == 2:
            # Horizontal compress: line shrinks to dot at center
            total_frames = 7
            t = min(frame / total_frames, 1.0)
            ease = t * t
            line_w = max(4, int(w * (1.0 - ease)))
            x1 = cx - line_w // 2
            x2 = cx + line_w // 2

            # Glow
            glow_color = lerp_color("#003344", "#000000", ease)
            canvas.create_rectangle(x1 - 3, cy - 3, x2 + 3, cy + 3,
                                    fill=glow_color, outline="")
            # Chromatic aberration: red channel offset above
            red_color = lerp_color("#ff4444", "#000000", ease)
            canvas.create_rectangle(x1, cy - 3, x2, cy - 1, fill=red_color, outline="")
            # Chromatic aberration: blue channel offset below
            blue_color = lerp_color("#4444ff", "#000000", ease)
            canvas.create_rectangle(x1, cy + 1, x2, cy + 3, fill=blue_color, outline="")
            # Line/dot (main white channel on top)
            bar_color = lerp_color("#88ffff", "#ffffff", ease)
            canvas.create_rectangle(x1, cy - 1, x2, cy + 1, fill=bar_color, outline="")

            app._shutdown_frame += 1
            if frame >= total_frames:
                app._shutdown_phase = 3
                app._shutdown_frame = 0

        elif phase == 3:
            # Dot fade: small dot fades from white to black
            total_frames = 5
            t = min(frame / total_frames, 1.0)
            dot_size = max(1, int(3 * (1.0 - t)))
            # Chromatic aberration: red dot offset up-left
            red_color = lerp_color("#ff4444", "#000000", t)
            canvas.create_rectangle(cx - dot_size - 2, cy - dot_size - 2,
                                    cx + dot_size - 2, cy + dot_size - 2,
                                    fill=red_color, outline="")
            # Chromatic aberration: blue dot offset down-right
            blue_color = lerp_color("#4444ff", "#000000", t)
            canvas.create_rectangle(cx - dot_size + 2, cy - dot_size + 2,
                                    cx + dot_size + 2, cy + dot_size + 2,
                                    fill=blue_color, outline="")
            # Main white dot on top
            dot_color = lerp_color("#ffffff", "#000000", t)
            canvas.create_rectangle(cx - dot_size, cy - dot_size,
                                    cx + dot_size, cy + dot_size,
                                    fill=dot_color, outline="")

            app._shutdown_frame += 1
            if frame >= total_frames:
                _crt_shutdown_finish(app)
                return

        app.root.after(16, lambda: _crt_shutdown_tick(app))

    except Exception:
        _crt_shutdown_finish(app)


def _crt_shutdown_finish(app):
    """Final cleanup: close storage, destroy windows."""
    try:
        app.storage.close()
    except Exception:
        pass
    try:
        app.root.destroy()
    except Exception:
        pass
    try:
        app._owner.destroy()
    except Exception:
        pass
