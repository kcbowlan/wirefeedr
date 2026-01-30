# ticker.py - Ticker tape, trending topics (split-flap), and bias balance bar

import tkinter as tk
import math
import random
import re
import webbrowser
from collections import Counter

from config import DARK_THEME
from constants import BIAS_POSITIONS, TRENDING_STOP_WORDS, FLAP_CHARS


def ticker_set_paused(app, paused):
    """Pause or resume ticker animation."""
    app.ticker_paused = paused
    if not paused:
        # Reset all text colors back to their original colors when leaving
        for item_id in app.ticker_canvas.find_withtag("ticker_text"):
            orig = app._ticker_item_colors.get(item_id)
            if orig:
                app.ticker_canvas.itemconfigure(item_id, fill=orig)


def on_ticker_configure(app, event):
    """Handle ticker canvas resize with debounce."""
    if app._ticker_resize_job:
        app.root.after_cancel(app._ticker_resize_job)
    app._ticker_resize_job = app.root.after(200, lambda: update_ticker(app))


def update_ticker(app):
    """Rebuild ticker content from unread articles in the treeview."""
    app.ticker_canvas.delete("all")
    app.ticker_canvas_to_article = {}
    app.ticker_offset = 0

    # Collect unread articles from treeview
    unread_items = []
    for item_id in app.articles_tree.get_children():
        tags = app.articles_tree.item(item_id, "tags")
        if "unread" in tags:
            values = app.articles_tree.item(item_id, "values")
            # values: (title, source, bias, date, score)
            unread_items.append({
                "article_id": int(item_id),
                "title": values[0],
                "source": values[1],
            })

    if not unread_items:
        # Show placeholder
        app.ticker_canvas.create_text(
            app.ticker_canvas.winfo_width() // 2, 14,
            text="No unread articles",
            fill=DARK_THEME["fg_secondary"],
            font=("TkDefaultFont", 9, "italic"),
            anchor=tk.CENTER,
        )
        stop_ticker_animation(app)
        return

    # Alternating headline colors
    headline_colors = [DARK_THEME["cyan"], DARK_THEME["magenta"]]
    source_color = DARK_THEME["neon_yellow"]
    app._ticker_item_colors = {}  # item_id -> original fill color

    # Build text items — two copies for seamless looping
    x = 0
    font = ("TkDefaultFont", 9)

    for copy in range(2):
        for i, item in enumerate(unread_items):
            h_color = headline_colors[i % 2]

            # Source tag in yellow brackets
            src_text = f"  [{item['source']}]  "
            src_id = app.ticker_canvas.create_text(
                x, 14, text=src_text, fill=source_color,
                font=font, anchor=tk.W, tags="ticker_text",
            )
            app._ticker_item_colors[src_id] = source_color
            app.ticker_canvas_to_article[src_id] = item["article_id"]
            src_bbox = app.ticker_canvas.bbox(src_id)
            x += (src_bbox[2] - src_bbox[0]) if src_bbox else 80

            # Headline text in alternating color
            text_id = app.ticker_canvas.create_text(
                x, 14, text=item["title"], fill=h_color,
                font=font, anchor=tk.W, tags="ticker_text",
            )
            app._ticker_item_colors[text_id] = h_color
            app.ticker_canvas_to_article[text_id] = item["article_id"]
            bbox = app.ticker_canvas.bbox(text_id)
            x += (bbox[2] - bbox[0]) if bbox else 100

        if copy == 0:
            app.ticker_total_width = x

    start_ticker_animation(app)


def ticker_step(app):
    """Move ticker items left by speed pixels. Called by master animation loop."""
    if not app.ticker_paused and app.ticker_total_width > 0:
        app.ticker_canvas.move("ticker_text", -app.ticker_speed, 0)
        app.ticker_offset += app.ticker_speed

        if app.ticker_offset >= app.ticker_total_width:
            app.ticker_canvas.move("ticker_text", app.ticker_total_width, 0)
            app.ticker_offset -= app.ticker_total_width


def start_ticker_animation(app):
    """Flag ticker as running (driven by master animation loop)."""
    app._ticker_running = True


def stop_ticker_animation(app):
    """Flag ticker as stopped."""
    app._ticker_running = False


def on_ticker_click(app, event):
    """Handle single click on ticker — select article in treeview."""
    item_id = app.ticker_canvas.find_closest(event.x, event.y)
    if not item_id:
        return
    item_id = item_id[0]
    article_id = app.ticker_canvas_to_article.get(item_id)
    if article_id is None:
        return

    article_str = str(article_id)
    if app.articles_tree.exists(article_str):
        app.articles_tree.selection_set(article_str)
        app.articles_tree.see(article_str)
        app.articles_tree.event_generate("<<TreeviewSelect>>")


def on_ticker_double_click(app, event):
    """Handle double-click on ticker — open article in browser."""
    item_id = app.ticker_canvas.find_closest(event.x, event.y)
    if not item_id:
        return
    item_id = item_id[0]
    article_id = app.ticker_canvas_to_article.get(item_id)
    if article_id is None:
        return

    article = app.storage.get_article(article_id)
    if article:
        webbrowser.open(article["link"])
        if not article["is_read"]:
            app.storage.mark_article_read(article_id)
            app.refresh_feeds_list()
            app.refresh_articles()


def on_ticker_motion(app, event):
    """Highlight headline under cursor (white), others restore original color."""
    closest = app.ticker_canvas.find_closest(event.x, event.y)
    if not closest:
        return
    closest_id = closest[0]

    for item_id in app.ticker_canvas.find_withtag("ticker_text"):
        if item_id == closest_id and item_id in app.ticker_canvas_to_article:
            app.ticker_canvas.itemconfigure(item_id, fill=DARK_THEME["fg_highlight"])
        else:
            orig = app._ticker_item_colors.get(item_id, DARK_THEME["cyan"])
            app.ticker_canvas.itemconfigure(item_id, fill=orig)


def update_bias_balance(app):
    """Compute bias arrow position and draw the gradient bar with indicator."""
    feeds = app.storage.get_feeds()
    if not feeds:
        app._bias_arrow_pos = 0.5
    else:
        positions = [BIAS_POSITIONS.get(f.get("bias", ""), 0.5) for f in feeds]
        app._bias_arrow_pos = sum(positions) / len(positions)
    draw_bias_bar(app)


def draw_bias_bar(app, pulse_t=0.0):
    """Draw the gradient bias line with a pulsing arrow indicator."""
    canvas = app._bias_canvas
    canvas.delete("all")
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w < 20 or h < 5:
        return

    # 3-stop horizontal gradient: blue -> green -> orange
    bar_y = h // 2
    bar_thickness = 4
    y0 = bar_y - bar_thickness // 2
    y1 = bar_y + bar_thickness // 2
    # Brightness multiplier from pulse (0.5 dim .. 1.0 bright)
    bright = 0.65 + 0.35 * pulse_t
    for x in range(w):
        t = x / max(w - 1, 1)
        if t < 0.5:
            # blue (#4488ff) -> green (#44ff88)
            lt = t * 2.0
            r = int((0x44 + (0x44 - 0x44) * lt) * bright)
            g = int((0x88 + (0xff - 0x88) * lt) * bright)
            b = int((0xff + (0x88 - 0xff) * lt) * bright)
        else:
            # green (#44ff88) -> orange (#ff8844)
            lt = (t - 0.5) * 2.0
            r = int((0x44 + (0xff - 0x44) * lt) * bright)
            g = int((0xff + (0x88 - 0xff) * lt) * bright)
            b = int((0x88 + (0x44 - 0x88) * lt) * bright)
        r, g, b = min(r, 255), min(g, 255), min(b, 255)
        color = f"#{r:02x}{g:02x}{b:02x}"
        canvas.create_line(x, y0, x, y1, fill=color)

    # Glow line (wider, dimmer) behind the bar
    for x in range(0, w, 2):
        t = x / max(w - 1, 1)
        if t < 0.5:
            lt = t * 2.0
            r = int((0x44 + (0x44 - 0x44) * lt) * bright * 0.3)
            g = int((0x88 + (0xff - 0x88) * lt) * bright * 0.3)
            b = int((0xff + (0x88 - 0xff) * lt) * bright * 0.3)
        else:
            lt = (t - 0.5) * 2.0
            r = int((0x44 + (0xff - 0x44) * lt) * bright * 0.3)
            g = int((0xff + (0x88 - 0xff) * lt) * bright * 0.3)
            b = int((0x88 + (0x44 - 0x88) * lt) * bright * 0.3)
        r, g, b = min(r, 255), min(g, 255), min(b, 255)
        glow_color = f"#{r:02x}{g:02x}{b:02x}"
        canvas.create_line(x, y0 - 3, x, y1 + 3, fill=glow_color)

    # Arrow indicator at bias position
    arrow_x = int(app._bias_arrow_pos * (w - 1))
    arrow_size = 5
    # Arrow color pulses between cyan and white
    arrow_bright = 0.7 + 0.3 * pulse_t
    ar = int(0x00 + (0xff - 0x00) * arrow_bright)
    ag = int(0xff * arrow_bright)
    ab = int(0xff * arrow_bright)
    arrow_color = f"#{min(ar,255):02x}{min(ag,255):02x}{min(ab,255):02x}"
    # Downward-pointing triangle above the bar
    canvas.create_polygon(
        arrow_x, y0 - 2,
        arrow_x - arrow_size, y0 - 2 - arrow_size - 2,
        arrow_x + arrow_size, y0 - 2 - arrow_size - 2,
        fill=arrow_color, outline=""
    )
    # Small glow dot on the bar at arrow position
    canvas.create_oval(
        arrow_x - 3, bar_y - 3, arrow_x + 3, bar_y + 3,
        fill=arrow_color, outline=""
    )

    # Endpoint labels
    canvas.create_text(4, h - 3, text="L", anchor=tk.SW,
                       fill="#4488ff", font=("Consolas", 7, "bold"))
    canvas.create_text(w // 2, h - 3, text="C", anchor=tk.S,
                       fill="#44ff88", font=("Consolas", 7, "bold"))
    canvas.create_text(w - 4, h - 3, text="R", anchor=tk.SE,
                       fill="#ff8844", font=("Consolas", 7, "bold"))


def animate_bias_pulse(app):
    """Pulse the bias bar gradient — called from _anim_tick."""
    pulse_t = (math.sin(app._anim_frame * 0.06) + 1.0) / 2.0
    draw_bias_bar(app, pulse_t)


def update_trending(app, articles):
    """Extract trending words and set up the cycling slot display."""
    app._trending_canvas.delete("all")
    app._trending_pool = []
    app._trending_slots = []
    app._trending_pool_idx = 0
    app._trending_initial_done = False

    if not articles:
        return

    # Extract and count words — grab a large pool
    word_counts = Counter()
    for article in articles:
        title = article.get("title", "")
        words = re.findall(r"[a-zA-Z']+", title.lower())
        for word in words:
            if len(word) >= 3 and word not in TRENDING_STOP_WORDS:
                word_counts[word] += 1

    top_words = word_counts.most_common(30)
    if not top_words:
        return

    colors = [DARK_THEME["cyan"], DARK_THEME["magenta"],
              DARK_THEME["fg_secondary"]]
    for i, (word, count) in enumerate(top_words):
        if i < 4:
            color = colors[0]
        elif i < 12:
            color = colors[1]
        else:
            color = colors[2]
        app._trending_pool.append({"word": word, "count": count, "color": color})

    random.shuffle(app._trending_pool)
    layout_trending_slots(app)


def layout_trending_slots(app):
    """Compute compact flowing slot positions and populate initial words."""
    canvas = app._trending_canvas
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w < 30 or h < 10 or not app._trending_pool:
        return

    canvas.delete("all")
    char_w = 8    # per-character cell width
    cell_h = 14   # cell height
    row_gap = 3   # gap between rows
    word_gap = 10 # gap between word slots

    max_word_len = max(len(e["word"]) for e in app._trending_pool)
    slot_w = max_word_len * char_w

    # Calculate grid dimensions for centering
    cols = max(1, (w + word_gap) // (slot_w + word_gap))
    rows = max(1, (h + row_gap) // (cell_h + row_gap))
    total_slots = cols * rows
    grid_w = cols * slot_w + (cols - 1) * word_gap
    grid_h = rows * cell_h + (rows - 1) * row_gap
    origin_x = (w - grid_w) // 2
    origin_y = (h - grid_h) // 2

    # Draw background cells and flow slots
    app._trending_slots = []
    app._flap_char_w = char_w
    app._flap_cell_h = cell_h
    app._flap_max_len = max_word_len
    slot_idx = 0

    for row in range(rows):
        for col in range(cols):
            x = origin_x + col * (slot_w + word_gap)
            y = origin_y + row * (cell_h + row_gap)
            # Draw flap cell backgrounds for this slot
            for ci in range(max_word_len):
                cx = x + ci * char_w
                canvas.create_rectangle(
                    cx, y, cx + char_w - 1, y + cell_h,
                    fill="#0c0c18", outline="#1a1a2e", tags="flap_bg"
                )
            slot = {
                "x": x, "y": y,
                "char_items": [None] * max_word_len,
                "pool_entry": None,
                "prev_word": "",
                "target_word": "",
                "settle_frames": [0] * max_word_len,
                "state": "idle",
                "flip_start": 0,
                "tag": f"ts_{slot_idx}",
            }
            app._trending_slots.append(slot)
            slot_idx += 1

    # Assign initial words and kick off flipping
    app._trending_pool_idx = 0
    for i, slot in enumerate(app._trending_slots):
        if app._trending_pool_idx < len(app._trending_pool):
            entry = app._trending_pool[app._trending_pool_idx]
            app._trending_pool_idx += 1
            slot["pool_entry"] = entry
            slot["target_word"] = entry["word"].upper().ljust(app._flap_max_len)
            # Stagger initial flips so they cascade across the board
            slot["state"] = "flipping"
            slot["flip_start"] = app._anim_frame + i * 2
            # Each char settles with a cascade delay
            for ci in range(app._flap_max_len):
                slot["settle_frames"][ci] = slot["flip_start"] + 4 + ci * 1

    # Schedule first board-wide flip
    interval = app._trending_intervals[app._trending_interval_idx % len(app._trending_intervals)]
    app._trending_next_flip = app._anim_frame + interval


def flip_all_trending(app):
    """Flip the entire board to new words. Called by timer or refresh button."""
    if not app._trending_slots or not app._trending_pool:
        return
    frame = app._anim_frame
    for i, slot in enumerate(app._trending_slots):
        if slot["state"] == "flipping":
            continue  # already mid-flip
        old_word = slot["pool_entry"]["word"] if slot["pool_entry"] else None
        new_entry = next_pool_word(app, exclude_word=old_word)
        if new_entry:
            slot["pool_entry"] = new_entry
            slot["target_word"] = new_entry["word"].upper().ljust(app._flap_max_len)
        slot["state"] = "flipping"
        slot["flip_start"] = frame + i * 2  # cascade stagger across slots
        for ci in range(app._flap_max_len):
            slot["settle_frames"][ci] = slot["flip_start"] + 4 + ci * 1
        # Unbind during flip
        canvas = app._trending_canvas
        canvas.tag_unbind(slot["tag"], "<Button-1>")
        canvas.tag_unbind(slot["tag"], "<Enter>")
        canvas.tag_unbind(slot["tag"], "<Leave>")

    # Cycle to next interval
    app._trending_interval_idx = (app._trending_interval_idx + 1) % len(app._trending_intervals)
    interval = app._trending_intervals[app._trending_interval_idx]
    app._trending_next_flip = frame + interval


def next_pool_word(app, exclude_word=None):
    """Get the next word from the pool, cycling. Skip duplicates of visible words."""
    if not app._trending_pool:
        return None
    visible_words = {s["pool_entry"]["word"] for s in app._trending_slots
                     if s["pool_entry"] and s["state"] != "idle"}
    for _ in range(len(app._trending_pool)):
        entry = app._trending_pool[app._trending_pool_idx % len(app._trending_pool)]
        app._trending_pool_idx = (app._trending_pool_idx + 1) % len(app._trending_pool)
        if exclude_word and entry["word"] == exclude_word:
            continue
        if entry["word"] not in visible_words:
            return entry
    return app._trending_pool[app._trending_pool_idx % len(app._trending_pool)]


def click_trending_word(app, word):
    """Set search filter to the clicked trending word."""
    app.search_var.set(word.strip().lower())
    app.refresh_articles()


def animate_trending(app):
    """Split-flap display animation. Called from _anim_tick."""
    if not app._trending_slots:
        return
    canvas = app._trending_canvas
    frame = app._anim_frame
    char_w = app._flap_char_w
    cell_h = app._flap_cell_h
    max_len = app._flap_max_len
    flap_chars = FLAP_CHARS

    # Check global flip timer
    if (app._trending_next_flip > 0 and frame >= app._trending_next_flip
            and any(s["state"] == "settled" for s in app._trending_slots)):
        flip_all_trending(app)

    for slot in app._trending_slots:
        entry = slot["pool_entry"]
        if not entry:
            continue
        tag = slot["tag"]

        if slot["state"] == "flipping":
            target = slot["target_word"]
            all_settled = True

            for ci in range(max_len):
                settle_at = slot["settle_frames"][ci]
                cx = slot["x"] + ci * char_w
                cy = slot["y"]

                if frame >= settle_at:
                    # This char has settled — show target
                    ch = target[ci] if ci < len(target) else " "
                    color = entry["color"] if ch.strip() else "#0c0c18"
                    if slot["char_items"][ci] is None:
                        item = canvas.create_text(
                            cx + char_w // 2, cy + cell_h // 2,
                            text=ch, font=("Consolas", 9, "bold"),
                            fill=color, anchor=tk.CENTER,
                            tags=(tag, f"{tag}_c{ci}")
                        )
                        slot["char_items"][ci] = item
                    else:
                        canvas.itemconfigure(slot["char_items"][ci],
                                             text=ch, fill=color,
                                             font=("Consolas", 9, "bold"))
                elif frame >= slot["flip_start"]:
                    # Still flipping — show random char
                    all_settled = False
                    ch = random.choice(flap_chars)
                    color = "#667744"
                    if slot["char_items"][ci] is None:
                        item = canvas.create_text(
                            cx + char_w // 2, cy + cell_h // 2,
                            text=ch, font=("Consolas", 9),
                            fill=color, anchor=tk.CENTER,
                            tags=(tag, f"{tag}_c{ci}")
                        )
                        slot["char_items"][ci] = item
                    else:
                        canvas.itemconfigure(slot["char_items"][ci],
                                             text=ch, fill=color,
                                             font=("Consolas", 9))
                else:
                    all_settled = False

            if all_settled:
                slot["state"] = "settled"
                # Bind click/hover on the whole slot tag
                word = entry["word"]
                canvas.tag_bind(tag, "<Button-1>",
                                lambda e, w=word: click_trending_word(app, w))
                canvas.tag_bind(tag, "<Enter>",
                                lambda e, t=tag: (
                                    canvas.itemconfigure(t, fill=DARK_THEME["neon_yellow"]),
                                    canvas.configure(cursor="hand2")))
                canvas.tag_bind(tag, "<Leave>",
                                lambda e, t=tag, s=slot: flap_hover_leave(app, t, s))


def flap_hover_leave(app, tag, slot):
    """Restore settled char colors on hover leave."""
    canvas = app._trending_canvas
    canvas.configure(cursor="")
    entry = slot.get("pool_entry")
    if not entry:
        return
    target = slot["target_word"]
    for ci, item_id in enumerate(slot["char_items"]):
        if item_id:
            ch = target[ci] if ci < len(target) else " "
            color = entry["color"] if ch.strip() else "#0c0c18"
            canvas.itemconfigure(item_id, fill=color)
