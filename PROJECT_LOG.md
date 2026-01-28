# Personal News Aggregator - Project Log

## Project Goal
Create a desktop news aggregator that delivers factual news via RSS feeds while filtering out sensationalism, opinion pieces, and propaganda.

**Last Updated:** 2026-01-27
**Status:** v1.8 - Dark Cyberpunk Theme Applied

---

## Technology Stack
| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python 3 | Simple, readable, good RSS libraries |
| GUI | Tkinter | Built into Python, no installation |
| RSS Parsing | feedparser | Industry standard, handles edge cases |
| HTTP | requests | Simple and reliable |
| Storage | sqlite3 | Built into Python, no installation |

**Packages to install:** `pip install feedparser requests`

---

## Project Structure

```
News Aggregate/
├── News Aggregator.bat      # Windows launcher (double-click to run)
├── PROJECT_LOG.md           # This file
└── news_aggregator/
    ├── main.py              # Entry point
    ├── app.py               # Tkinter GUI (~2500 lines)
    ├── feeds.py             # RSS feed fetching/parsing
    ├── storage.py           # SQLite database operations
    ├── filters.py           # Content filtering logic
    ├── config.py            # Default settings, feeds, and bias colors
    └── data/
        └── news.db          # SQLite database (auto-created on first run)
```

---

## How to Run

```bash
# Option 1: Double-click the batch file
News Aggregator.bat

# Option 2: Command line
cd news_aggregator
python main.py
```

---

## Features Implemented

### Core Features
- [x] RSS feed fetching and parsing with error handling
- [x] SQLite storage for feeds, articles, settings, and custom keywords
- [x] Sensationalism/noise detection scoring (0-100)
- [x] Opinion content detection (URL patterns, title patterns)
- [x] Clickbait pattern detection
- [x] Custom filter keywords with configurable weights

### GUI Features
- [x] Three-panel layout (feeds tree, article list, preview)
- [x] Feed management (add, remove, validate, organize by category)
- [x] Article list columns: Title, Source, Bias, Date, Noise Level
- [x] Article preview with summary text
- [x] "Open in Browser" button
- [x] "Author Bio" button (links to author profile when available)
- [x] Mark read/unread (automatic on selection)
- [x] Noise filter slider (hide articles above threshold)
- [x] Search functionality
- [x] Auto-refresh (30 minutes default, configurable)
- [x] Right-click context menus on feeds and articles

### Bias Transparency
- [x] Source bias ratings displayed in article list column
- [x] Color-coded bias labels in preview panel:
  - Green = Center
  - Blue = Left-Center
  - Purple = Right-Center
- [x] Color-coded factual ratings:
  - Green = Very High / High
  - Orange = Mostly Factual
  - Red = Mixed
- [x] Author Bio button with auto-generated profile URLs

### Volume Reduction (v1.3)
- [x] **Recency Window** - Dropdown to filter articles by age (6h/12h/24h/48h/Week/All)
- [x] **Smart Daily Cap per Source** - Limit N articles per feed, ranked by quality score
- [x] **Topic Clustering** - Group related articles with [+N] indicator, expandable in preview

### UI Polish (v1.8)
- [x] **Dark Cyberpunk Theme** - Full dark theme with neon cyan/magenta accents (Session 12)
- [ ] **Cyberpunk Animations** - Pulsing neon borders, color cycling (NOT YET REBUILT)
- [x] **Summary Highlighting** - Comprehensive entity-based highlighting with Wikipedia links:
  - People (Cyan), Titles (Purple), Government (Slate Blue), Military (Steel Blue)
  - Organizations (Green), Countries (Orange), Places (Sienna), Events (Goldenrod)
  - Money (Magenta), Statistics (Hot Pink), Dates (Rose), Numbers (Yellow), Verbs (Coral)
- [x] **Bold Lede** - First sentence bolded for quick scanning
- [x] **Keyboard Navigation** - ↑/↓ navigate, Enter open, M read, H hide, F5 refresh
- [x] **Wikipedia Links** - Clickable entities open Wikipedia search
- [x] **Feed Favicons** - 16x16 icons next to feed names

---

## Default Feeds (with Integrity Ratings)

| Source | Category | Bias | Factual | Author Bio |
|--------|----------|------|---------|------------|
| Associated Press | Wire Services | Center | Very High | Yes |
| Reuters World | Wire Services | Center | Very High | Yes |
| NPR News | Public Broadcasting | Left-Center | Very High | Yes |
| BBC World | International | Left-Center | High | No |
| The Guardian World | International | Left-Center | Mixed | Yes |
| PBS NewsHour | Public Broadcasting | Center | High | Yes |
| Wall Street Journal | Business | Right-Center | High | Yes |
| The Economist | International | Center | High | No |

*Ratings source: [Media Bias/Fact Check](https://mediabiasfactcheck.com/)*

---

## Database Schema

### feeds
```sql
id, name, url, category, bias, factual, author_url_pattern,
enabled, last_fetched, created_at
```

### articles
```sql
id, feed_id, title, link, summary, published, author,
noise_score, is_read, is_hidden, created_at
```

### filter_keywords
```sql
id, keyword, weight, is_active, created_at
```

### settings
```sql
key, value
```

---

## Article Grading System

Articles receive an objectivity score (0-100) where **higher = better**.

**Grades:**
| Score | Grade | Label | Color |
|-------|-------|-------|-------|
| 85-100 | A | Straight News | Dark green |
| 65-84 | B | Light Commentary | Green |
| 45-64 | C | Editorialized | Yellow |
| 25-44 | D | Heavy Spin | Orange |
| 0-24 | F | Opinion/Hype | Red |

**Deductions (subtracted from 100):**
| Factor | Deduction | Examples |
|--------|-----------|----------|
| Opinion URL patterns | -40 | /opinion/, /editorial/, /blog/ |
| Opinion title indicators | -35 | "Opinion:", "Editorial:" |
| Sensational keywords | -5 to -15 each | "BREAKING", "slams", "destroys" |
| Clickbait patterns | -20 | "10 reasons...", "You won't believe" |
| Excessive punctuation | -5 to -15 | Multiple !!!, ??? |
| ALL CAPS words | -5 to -15 | Non-abbreviation capitals |

**What Gets Analyzed:**
| Input | Checks |
|-------|--------|
| URL | Opinion path patterns |
| Headline | All checks except URL patterns |
| Summary | Sensational keywords, custom keywords |

---

## Implementation Status

### Phase 1: Foundation - COMPLETE
- [x] Set up project structure
- [x] Create SQLite database schema
- [x] Implement storage.py (CRUD operations)

### Phase 2: Data Ingestion - COMPLETE
- [x] Implement feeds.py (RSS fetching/parsing)
- [x] Create config.py with default sources
- [x] Test feed fetching with sample sources

### Phase 3: Filtering - COMPLETE
- [x] Implement filters.py
- [x] Source-based filtering
- [x] URL path filtering (opinion detection)
- [x] Sensationalism keyword scoring

### Phase 4: User Interface - COMPLETE
- [x] Create basic Tkinter window layout
- [x] Feed list panel (left)
- [x] Article list panel (center)
- [x] Article preview panel (bottom)
- [x] Open in browser functionality

### Phase 5: User Controls - COMPLETE
- [x] Add/remove feed sources
- [x] Noise threshold slider
- [x] Mark articles read/unread
- [x] Manual refresh button

### Phase 6: Polish - COMPLETE
- [x] Auto-refresh on interval
- [x] Search/filter articles
- [x] Settings persistence
- [~] Keyboard shortcuts (implemented, needs refinement)

### Phase 7: Bias Transparency - COMPLETE
- [x] Add bias/factual ratings to feeds
- [x] Display bias column in article list
- [x] Color-coded labels in preview
- [x] Author bio URL generation

---

## Progress Log

### Session 1 - 2026-01-17: Planning
- Defined project requirements
- Chose technology stack
- Designed architecture
- Planned filtering strategy
- Created implementation roadmap

### Session 2 - 2026-01-17: Full Implementation
- Created all core modules: config.py, storage.py, feeds.py, filters.py, app.py, main.py
- Implemented complete GUI with three-panel layout
- Added all filtering logic (opinion detection, sensationalism scoring)
- Created Windows batch launcher
- Initial default feeds: AP, Reuters, NPR, BBC, Guardian, PBS, Al Jazeera, CSM

### Session 3 - 2026-01-17: Bias Transparency Update
- Researched journalistic integrity ratings for all sources
- Removed Al Jazeera (Qatar state-owned, mixed factual rating)
- Removed Christian Science Monitor (user request)
- Added Wall Street Journal (Right-Center, High factual)
- Added The Economist (Center, High factual)
- Added bias/factual fields to database with migration support
- Added Bias column to article list
- Added color-coded bias/factual labels in preview panel
- Implemented Author Bio button with auto-generated URLs
- Updated PROJECT_LOG.md

### Session 4 - 2026-01-18: Grading System Overhaul
- Changed auto-refresh interval from 30 minutes to 3 hours
- Replaced "Noise Score" with letter grade system (A-F)
- Inverted scoring: higher = better (0-100 objectivity scale)
- Added grade labels: A (Straight News), B (Light Commentary), C (Editorialized), D (Heavy Spin), F (Opinion/Hype)
- Color scale: dark green → green → yellow → orange → red
- Renamed UI: "Noise Filter" → "Min Grade" slider
- Updated storage queries to filter by minimum score
- Initialized git repository (pending: configure user identity)

### Session 5 - 2026-01-18: Cyberpunk UI Overhaul
- Implemented dark mode with cyberpunk aesthetic
- Color palette: neon cyan (#00ffff) + neon magenta (#ff00ff) accents
- Deep black backgrounds with layered depth
- Cyan borders for Feeds/Articles panels, magenta for Preview panel
- Buttons: cyan border, magenta on hover
- Selected rows: magenta with white text
- Menu highlights: magenta
- Added compact-but-comfortable padding throughout
- Increased row height to 30px for easier clicking
- Added alternating row striping (subtle background variation)

### Session 6 - 2026-01-22: Volume Reduction & Summary Highlighting
- Implemented all three volume reduction features:
  - Recency Window dropdown (6h/12h/24h/48h/Week/All)
  - Smart Daily Cap per Source dropdown (5/10/15/20/No Limit)
  - Topic Clustering with [+N] indicators and RELATED ARTICLES section
- Added cyberpunk animations: pulsing borders, color cycling, status bar typing
- Implemented summary highlighting with semantic colors:
  - Names/proper nouns (cyan), Organizations (green), Locations (lime)
  - Numbers (magenta), Percentages/Quotes (yellow), Actions (hot pink)
- Bold lede (first sentence) for quick scanning
- Typewriter effect for summary text
- Keyboard navigation (Tab, arrows, Enter, M, H, Escape, F5)
- Controls button showing keyboard reference
- **Note:** Keyboard navigation simplified in Session 7

### Session 7 - 2026-01-23: Bug Fixes & Scoring Enhancements
- **Fixed AP & Reuters feeds**: Original URLs were dead (403/404 errors)
  - Updated to use Google News RSS proxy: `news.google.com/rss/search?q=when:24h+allinurl:{domain}`
  - Updated both config.py (for new installs) and existing database records
- **Fixed Bias/Factual ratings**: Database had "Unknown" values
  - Populated all feeds with correct bias/factual ratings from Media Bias/Fact Check
  - Updated migration to auto-populate ratings for feeds with "Unknown" values
- **Fixed Author Info button**: Renamed from "Author Bio", now uses Google search
  - Changed from unreliable URL slug generation to Google search: `"Author Name" author site:domain`
  - Cleans author names (removes "By", locations, titles)
  - Skips agency bylines (AFP, Reuters, AP, etc.)
  - Added visible disabled state (muted colors) to TButton style
- **Simplified keyboard navigation**: Removed Tab/panel cycling
  - Just ↑/↓ to navigate articles, Enter to open, M to toggle read, H to hide
- **Expanded summary analysis**: Added positive/negative factor scoring
  - Positive: attribution (+5), quotes (+5), numbers (+3), dates (+3), hedging (+2)
  - Negative: opinion phrases (-10), imperatives (-8), vague sources (-5), emotional words (-5)
- **Source factual rating modifier**: Feeds' factual ratings now affect scores
  - Very High: +5 bonus, High: neutral, Mostly Factual: -5, Mixed: -10
- **Cross-source corroboration**: Clustered articles get bonus
  - 2 sources: +2, 3 sources: +5, 4+ sources: +8
- **New grade labels**: Cyberpunk-themed, harsher descriptors
  - A: Solid, B: Passable, C: Weak, D: Noise, F: Slop
- **Numerical scoring**: Changed from letter grades to "85 - Solid" format
- **Published column**: Renamed from "Date", now shows relative time
  - Format: "<3 Hours" or ">5 Hours" (rounded to nearest hour)
- **Added WRFDR logo**: Displays at bottom of Feeds panel with version number
- **Relocated status bar**: Moved from bottom of window to Preview panel header
  - "Preview" label on left, animated status text on right
  - Fixed cursor blink to use color toggle (prevents text jumping)
- **UI adjustments**: Increased default window size to 1200x750

### Session 8 - 2026-01-24: UI Tweaks, Wikipedia Hyperlinks, Author Search & Favicons
- **Removed Min Grade slider** from toolbar (all articles now shown regardless of score)
- **Number highlighting expanded** - All numbers now highlighted in magenta, not just those with qualifiers
- **Wikipedia hyperlinks on proper nouns** - Names, organizations, and locations are now clickable
  - Underlined styling with hand cursor on hover
  - Uses Google site:wikipedia.org search, resolves redirect programmatically to bypass notice
  - Extensive exclusion list for common words (days, months, verbs, adjectives, etc.)
  - Multi-word names like "President Kennedy" work correctly
  - **Status:** Functional but disambiguation still inconsistent; tabled for future refinement
- **Search Author dropdown** - Replaced "Author Info" button with dropdown menu
  - Options: Google, LinkedIn, Wikipedia, Twitter
  - Extracts and cleans author name from article metadata
  - Styled with cyan border to match other buttons
- **Feed favicons** - Small icons now display next to feed names in sidebar
  - Uses Google's favicon service for reliability
  - Handles Google News RSS proxy URLs (extracts real domain)
  - Handles feed subdomains (feeds.npr.org → npr.org, bbci.co.uk → bbc.com)
  - Cached in database as BLOB, loaded async in background

### Session 9 - 2026-01-25: WIREFEEDR Rebrand & Borderless UI Overhaul (LOST - NEEDS REBUILD)
- **App renamed to WIREFEEDR** - New name displayed in custom title bar and taskbar
- **Fixed ticker tape click-to-select bug** - Clicking articles in ticker now works with clustering
  - Root cause: Only representative article IDs were in treeview, not clustered articles
  - Solution: Added `article_to_rep` reverse lookup map to resolve any article ID to its cluster representative
- **Fixed borderless window issues**:
  - **Taskbar visibility**: Used Windows ctypes API (`WS_EX_APPWINDOW`) to force app onto taskbar
  - **Resize handles**: Implemented custom edge detection with 8-direction resize cursors
- **Removed native Windows menu bar** - Eliminated white "File/Articles" menu bar
- **Custom title bar menus** - Moved all menu functionality into draggable title bar:
  - **REFRESH** button (first position) with spinning animation on click
  - **FEEDS** dropdown (includes Feed Diag)
  - **CONTROLS** dropdown with styled popup matching app aesthetic
  - **PURGE** button (aligned right near minimize) with custom confirmation dialog
- **Custom PURGE confirmation dialog** - Styled borderless popup:
  - Magenta border, dark background, "WARNING" in large text
  - Centered over main window, matches cyberpunk aesthetic
  - Added `delete_all_articles()` method to storage.py
- **Relocated toolbar controls** - Moved filters inline with panel headers to save vertical space:
  - Feeds header row: "Feeds" label left, "Show Read" + "Cluster" checkboxes right
  - Articles header row: "Articles" label left, Recency/Per Source/Search controls right
- **Fixed panel border animations** - Refactored `BorderAnimator` class:
  - Switched from ttk.LabelFrame to tk.Frame for panels
  - Changed from ttk.Style updates to direct widget `configure()` calls
  - Added `set_targets()` method to accept frame/label references
- **Code cleanup** - Removed ~40 lines of unused code:
  - Removed obsolete LabelFrame styles
  - Removed `_build_toolbar` method
  - Removed `_build_status_bar` method
  - Removed `show_delete_old_dialog` method
  - Kept `analyze_article` debug method per user request

### Session 10 - 2026-01-25: Accidental Revert
- Attempted font consistency changes (Segoe UI sans-serif)
- User requested revert, but `git checkout` reverted to staged Session 8 version
- **ALL Session 5-9 work lost** (dark theme, animations, borderless window, ticker, etc.)
- Current state: Basic unstyled app from Session 4

### Session 11 - 2026-01-25: Core Functionality Rebuild & Entity Highlighting System
Prioritized functionality over aesthetics. Rebuilt core features and implemented comprehensive entity recognition.

**Volume Reduction Controls Restored:**
- Recency dropdown (6h/12h/24h/48h/Week/All)
- Per Source cap dropdown (5/10/15/20/No Limit)
- Topic Clustering toggle with [+N] indicators
- Related articles shown in preview when cluster selected

**Scoring System Improvements:**
- Score column displays "85 - Solid" format
- Date column shows relative time ("< 3 Hours", "2 Days")
- Factual rating now factors into objectivity scoring
- Top 10 articles per feed at fetch time (ranked by quality)

**AP/Reuters Feed Fix:**
- Database migration auto-fixes old broken URLs to Google News RSS proxy

**Search Author Dropdown:**
- Replaced "Author Bio" button with dropdown menu
- Options: Google, LinkedIn, Wikipedia, Twitter/X
- Cleans author names, skips agency bylines

**Feed Favicons:**
- 16x16 icons next to feed names in sidebar
- Google favicon service, cached in database
- Handles Google News proxy URLs (extracts real domain)

**Keyboard Navigation:**
- ↑/↓ navigate articles, Enter opens in browser
- M toggles read/unread, H hides article, F5 refreshes

**Comprehensive Entity Highlighting System (Wikipedia Links):**
New category-based highlighting with clickable Wikipedia links. Entity databases massively expanded.

| Category | Color | Entries | Examples |
|----------|-------|---------|----------|
| People | Cyan `#008b8b` | Pattern-based | Names detected mid-sentence |
| Titles | Purple `#8b008b` | ~150 | President, General, Dr. |
| Government | Slate Blue `#6a5acd` | ~200 | FBI, Congress, Kremlin |
| Military | Steel Blue `#4682b4` | ~180 | NATO, IDF, Navy SEALs |
| Organizations | Green `#228b22` | ~350 | UN, Apple, Harvard |
| Countries | Orange `#cc7000` | ~200 | All 195 UN nations + aliases |
| Places | Sienna `#a0522d` | ~450 | Major cities worldwide, landmarks |
| Events | Goldenrod `#b8860b` | ~250 | Wars, treaties, disasters |

**Number Highlighting (non-clickable):**
| Category | Color | Examples |
|----------|-------|----------|
| Money | Magenta `#c71585` | $5 billion, €200 million |
| Statistics | Hot Pink `#ff69b4` | 45%, 1,000 troops |
| Dates | Rose `#e75480` | January 6, Tuesday |
| Numbers | Yellow `#e6c300` | All other numbers |
| Verbs | Muted Coral `#d2956b` | said, announced, killed |

**Entity Detection Features:**
- Title + Name linked as one unit ("President Xi Jinping" → Wikipedia)
- Multi-word pattern matching ("Bureau of Meteorology", "Gulf of Mexico")
- Trigger word whitelist prevents over-matching
- Blacklist for common phrase endings
- Possessives handled ("China's" highlights but searches "China")
- Names at sentence start now detected
- Bold lede (first sentence)
- ~1,780 total entity entries across all categories

**Remaining for Future Sessions:**
- Borderless window with custom title bar
- Pulsing border animations
- WIREFEEDR branding
- **Back up to GitHub** (priority)

### Session 12 - 2026-01-27: Dark Cyberpunk Theme & Ticker Tape
Restored the dark cyberpunk aesthetic lost in Session 10, plus the ticker tape from Session 9.

**Dark Theme Applied to All Widgets:**
- Switched ttk theme from Windows default to `clam` for full color control
- Configured all ttk styles: TFrame, TLabel, TButton, TCheckbutton, TCombobox, Treeview, Treeview.Heading, TLabelframe, TPanedwindow, TSeparator, TScrollbar, TMenubutton, TEntry, TSpinbox
- `style.map()` calls for interactive states: magenta hover, magenta selection, cyan active indicators
- Root window background set to deepest black (`#05050a`)

**Color Palette (from config.py DARK_THEME):**
- Backgrounds: `#05050a` (deepest), `#0a0a12` (panels), `#10101a` (lists/inputs)
- Text: `#e8e8e8` (primary), `#6a7080` (muted), `#ffffff` (highlight)
- Accents: `#00ffff` (cyan), `#ff00ff` (magenta), `#ff1493` (hot pink)
- Selection: magenta background with white text

**Specific Widget Fixes:**
- All 7 `tk.Menu` constructors (menubar, submenus, context menus, author menu) dark-themed
- Combobox popdown listbox styled via `option_add` (dark bg, magenta selection)
- Checkbutton indicators: dark background, cyan when selected
- Treeview tags: unread = bold bright white, read = muted `#6a7080`
- Preview text widget: dark bg with light text and cyan cursor
- Bias/factual `tk.Label` widgets: dark background to blend when empty
- All three dialog classes (AddFeed, ManageFeeds, FilterKeywords) dark-themed
- Dialog status colors: `#ff4444` (error), `#44ff44` (success), muted gray (info)
- Border colors (`bordercolor`, `lightcolor`, `darkcolor`) set on buttons, entries, treeviews, labelframes to eliminate white edges

**Ticker Tape Restored:**
- Scrolling cyan headlines from unread articles
- Magenta highlight on hover, click to select, double-click to open
- Seamless looping with dual-copy technique
- Pause on mouse enter, resume on leave

---

## Potential Future Enhancements

### High Priority - Volume Reduction ✓ COMPLETE
These features reduce daily article count to a manageable ~20-30 articles.

- [x] **Topic Clustering** - Groups related articles with [+N] indicator, shows related in preview
- [x] **Recency Window** - Dropdown: 6h/12h/24h/48h/Week/All
- [x] **Smart Daily Cap per Source** - Dropdown: 5/10/15/20/No Limit per feed, ranked by quality

### Medium Priority
- [x] **Keyboard shortcuts** - Simplified: ↑/↓ navigate, Enter open, M read, H hide
- [x] **Wikipedia hyperlinks** - Comprehensive entity highlighting with ~1,780 entries (Session 11)
- [x] **Ticker tape** - Scrolling unread headlines with click/hover interaction (Session 12)
- [ ] **GitHub backup** - Push to repository for version control
- [ ] OPML import/export for feed lists
- [ ] Feed folders/grouping
- [ ] Article tagging/bookmarking
- [ ] Notification for new articles

### Low Priority
- [ ] Offline reading mode (cache full article text)
- [ ] Feed health monitoring dashboard
- [ ] Readability mode (strip ads, extract content)
- [ ] Integration with read-it-later services (Pocket, Instapaper)

### Technical Debt
- [ ] Async feed fetching (currently sequential in background thread)
- [x] ~~Feed favicon fetching~~ - Done (Session 8)
- [ ] Database backup/restore
- [x] ~~Revisit Author Info search~~ - Now "Search Author" dropdown (Session 8)

---

## Known Limitations

1. **WSJ Feed**: Dow Jones RSS may require authentication for full article content
2. **RSS Compatibility**: Some non-standard feeds may not parse correctly
3. **Windows Only**: Batch launcher is Windows-specific (Python command works cross-platform)
4. **Author Bio URLs**: Best-effort generation; some may 404 if slug format differs from expected

---

## Notes & Decisions

- **Why not AI-based filtering?** Keyword/rule-based filtering keeps the app simple, fast, and fully offline. Can add AI later if needed.
- **Why hide vs delete?** Hiding allows users to tune sensitivity without losing articles. Transparency over black-box filtering.
- **Why these default sources?** Selected for factual reporting track record per Media Bias/Fact Check. Balanced across political spectrum (Left-Center to Right-Center).
- **Why color-coded bias?** Quick visual indication helps users contextualize information before reading.
