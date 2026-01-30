# animations.py - Visual effects, animation loop, typewriter, boot sequence, gradient buttons

import tkinter as tk
import math
import random

from PIL import Image, ImageDraw, ImageTk

from config import DARK_THEME
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
    """Subtle color cycle on the WIREFEEDR title."""
    t_val = (math.sin(app._anim_frame * (2 * math.pi / 180)) + 1) / 2
    color = lerp_color(DARK_THEME["cyan"], DARK_THEME["magenta"], t_val)
    app.title_label.configure(fg=color)


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
    """Activate glitch effect on refresh start."""
    app._glitch_active = True
    app._glitch_end_frame = (app._anim_frame + 8) % 3600
    app._glitch_sequence = ["#00ffff", "#ff00ff", "#ffffff", "#00ffff", "#ff00ff", "#ffffff", "#00ffff", "#ff00ff"]
    app._glitch_step = 0


def animate_glitch(app):
    """Flash panel borders through a fixed neon sequence."""
    if not app._glitch_active:
        return
    if app._anim_frame == app._glitch_end_frame:
        app._glitch_active = False
        return
    color = app._glitch_sequence[app._glitch_step % len(app._glitch_sequence)]
    app._glitch_step += 1
    for widget, _, _ in app._neon_panels:
        widget.configure(highlightbackground=color)


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
        "WIREFEEDR v2.0",
        "INITIALIZING NEURAL FEED PARSER",
        "CONNECTING TO NEWS GRID",
        "BIAS DETECTION MATRIX: ONLINE",
        "SIGNAL LOCKED. WELCOME, OPERATOR.",
    ]
    app._boot_step = 0
    app.root.after(200, lambda: boot_next_line(app))


def boot_next_line(app):
    """Display next boot line with typewriter effect."""
    if app._boot_step >= len(app._boot_lines):
        app.root.after(400, lambda: boot_fade_out(app))
        return

    y = 200 + app._boot_step * 28
    text = app._boot_lines[app._boot_step]
    color = DARK_THEME["cyan"] if app._boot_step < len(app._boot_lines) - 1 else DARK_THEME["magenta"]

    app._boot_overlay.create_text(
        60, y, text=text, fill=color, anchor=tk.W,
        font=("Consolas", 11, "bold")
    )
    app._boot_step += 1
    app.root.after(300, lambda: boot_next_line(app))


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
