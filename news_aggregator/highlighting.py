# highlighting.py - Semantic text highlighting and entity detection

import re
import webbrowser

from config import DARK_THEME
from entities import TITLES, KNOWN_PEOPLE, ORGANIZATIONS, COUNTRIES, PLACES, EVENTS, GOVERNMENT_TERMS, MILITARY_TERMS


def setup_highlight_tags(app):
    """Configure text tags for semantic highlighting."""
    # Bold for first sentence (lede)
    # lede tag removed --- no special formatting for first sentence

    # Entity categories (clickable Wikipedia links) --- bright for dark bg
    app.highlight_categories = {
        "people": "#00e5e5",      # Bright Cyan
        "titles": "#da70d6",      # Orchid
        "government": "#9d8bff",  # Bright Lavender
        "military": "#6cb4e6",    # Light Steel Blue
        "organizations": "#50e650", # Bright Green
        "countries": "#ff9d3a",   # Bright Orange
        "places": "#e08850",      # Light Sienna
        "events": "#f0c050",      # Bright Goldenrod
        "proper_nouns": "#00ffa0", # Electric Mint --- unknown proper nouns
    }

    # Number categories (not clickable) --- bright for dark bg
    app.number_categories = {
        "money": "#ff50a0",       # Bright Pink
        "statistics": "#ff88cc",  # Bright Hot Pink
        "dates": "#ff7098",       # Bright Rose
        "numbers": "#ffe040",     # Bright Yellow
    }

    # Verb categories (not clickable) --- colors chosen for thematic meaning
    app.verb_categories = {
        "verb_communication": "#87ceeb",  # Sky Blue --- clear as open air, neutral transmission
        "verb_accusation": "#dc143c",     # Crimson --- blood, anger, pointed finger
        "verb_support": "#90ee90",        # Light Green --- growth, thumbs up, go signal
        "verb_agreement": "#40e0d0",      # Turquoise --- harmony, meeting of waters
        "verb_decision": "#9370db",       # Medium Purple --- royal decree, judge's robe
        "verb_political": "#8b008b",      # Dark Magenta --- imperial purple, power
        "verb_military": "#8b0000",       # Dark Red --- blood of battle, Mars
        "verb_legal": "#ffd700",          # Gold --- scales of justice, law's weight
        "verb_economic": "#228b22",       # Forest Green --- money, wealth, growth
        "verb_discovery": "#00bfff",      # Deep Sky Blue --- eureka, illumination, insight
        "verb_change": "#ff8c00",         # Dark Orange --- autumn leaves, transformation
        "verb_creation": "#00fa9a",       # Medium Spring Green --- new life, genesis
        "verb_movement": "#b0c4de",       # Light Steel Blue --- wind, motion, travel
        "verb_emotion": "#ff69b4",        # Hot Pink --- the heart, passion, feeling
        "verb_prevention": "#4682b4",     # Steel Blue --- shield, barrier, protection
        "verb_competition": "#ffa500",    # Orange --- trophy, medal, fire of competition
        "verb_medical": "#20b2aa",        # Light Sea Green --- clinical, healing, triage
    }

    # Configure tags for entities (clickable)
    for tag, color in app.highlight_categories.items():
        app.preview_text.tag_configure(tag, foreground=color, underline=True)
        app.preview_text.tag_bind(tag, "<Enter>",
                                   lambda e: app.preview_text.configure(cursor="hand2"))
        app.preview_text.tag_bind(tag, "<Leave>",
                                   lambda e: app.preview_text.configure(cursor=""))
        app.preview_text.tag_bind(tag, "<Button-1>", lambda event: on_wiki_link_click(app, event))

    # Configure tags for numbers (not clickable)
    for tag, color in app.number_categories.items():
        app.preview_text.tag_configure(tag, foreground=color)

    # Configure tags for verbs (not clickable)
    for tag, color in app.verb_categories.items():
        app.preview_text.tag_configure(tag, foreground=color)

    # Related articles section (yellow)
    app.preview_text.tag_configure("related_header", foreground=DARK_THEME["neon_yellow"], font=("Consolas", 9, "bold"))

    # Store related article targets (populated in _finish_typewriter)
    app._related_article_targets = {}

    # Store wiki link targets: {(start, end): (search_term, category)}
    app.wiki_link_targets = {}

    # Initialize entity databases
    init_entity_databases(app)


def init_entity_databases(app):
    """Initialize databases of known entities for categorization."""
    app.titles = TITLES
    app.leaders = KNOWN_PEOPLE
    app.countries = COUNTRIES
    app.government = GOVERNMENT_TERMS
    app.military = MILITARY_TERMS
    app.organizations = ORGANIZATIONS
    app.places = PLACES
    app.events = EVENTS


def apply_highlighting(app, text_widget, text):
    """Apply semantic highlighting to text in the widget."""

    # Clear previous wiki link targets
    app.wiki_link_targets = {}

    # Insert text first
    text_widget.insert("1.0", text)

    # Bold the first sentence (lede)
    first_sentence_end = None
    for i, char in enumerate(text):
        if char in ".!?" and i > 20:
            first_sentence_end = i + 1
            break
    # lede highlighting removed

    text_lower = text.lower()

    # Track highlighted ranges to avoid overlaps
    highlighted_ranges = []

    def is_overlapping(start, end):
        for s, e in highlighted_ranges:
            if start < e and end > s:
                return True
        return False

    def add_highlight(start, end, tag, search_term=None):
        if is_overlapping(start, end):
            return False
        highlighted_ranges.append((start, end))
        start_idx = f"1.0+{start}c"
        end_idx = f"1.0+{end}c"
        text_widget.tag_add(tag, start_idx, end_idx)
        if search_term and tag in app.highlight_categories:
            app.wiki_link_targets[(start, end)] = (search_term, tag)
        return True

    # === NUMBERS (non-clickable) ===

    # 1. Money patterns
    money_patterns = [
        r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion))?',
        r'\u20ac[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion))?',
        r'\u00a3[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion))?',
        r'\b\d+(?:\.\d+)?\s*(?:dollars|euros|pounds|yen|yuan)',
    ]
    for pattern in money_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            add_highlight(match.start(), match.end(), "money")

    # 2. Statistics patterns
    stats_patterns = [
        r'\b\d+(?:\.\d+)?%',
        r'\b\d+(?:\.\d+)?\s*(?:percent|percentage)',
        r'\b\d{1,3}(?:,\d{3})+\b',
        r'\b\d+(?:\.\d+)?\s*(?:million|billion|trillion|thousand)\b',
        r'\b\d+\s*(?:people|troops|soldiers|casualties|deaths|injured|killed|wounded)',
    ]
    for pattern in stats_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            add_highlight(match.start(), match.end(), "statistics")

    # 3. Date patterns
    date_patterns = [
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?',
        r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,?\s+\d{4})?',
        r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
        r'\b(?:last|next|this)\s+(?:week|month|year|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
    ]
    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            add_highlight(match.start(), match.end(), "dates")

    # 4. Catch-all numbers (not already categorized)
    number_patterns = [
        # Ordinals
        r'\b\d+(?:st|nd|rd|th)\b',              # 1st, 2nd, 3rd, 250th
        # Times
        r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm|a\.m\.|p\.m\.)?\b',  # 3:00, 10:30 PM
        # Ranges and scores
        r'\b\d+(?:\.\d+)?[-\u2013\u2014]\d+(?:\.\d+)?\b', # 10-15, 2.5-3.0, 2020-2024
        r'\b\d+/\d+\b',                         # Fractions/scores: 1/2, 3/4
        # Decades
        r"\b\d{2,4}'?s\b",                      # 1990s, 80s, '90s
        # With units
        r'\b\d+(?:\.\d+)?\s*(?:km|mi|m|ft|in|cm|mm|kg|lb|lbs|oz|g|mg|mph|kph|fps|hz|khz|mhz|ghz|kb|mb|gb|tb|kw|mw|gw)\b',
        # With K/M/B abbreviations
        r'\b\d+(?:\.\d+)?\s*[KkMmBb]\b',        # 5K, 10M, 2.5B
        # Version numbers
        r'\bv?\d+(?:\.\d+)+\b',                 # v1.0, 2.5.1, v10.3.2
        # Scientific notation
        r'\b\d+(?:\.\d+)?[eE][+-]?\d+\b',       # 1e10, 2.5e-3
        # Temperatures
        r'[-\u2212]?\d+(?:\.\d+)?\u00b0[FCfc]?\b',        # 72 deg F, -10 deg C, 22 deg
        # Coordinates
        r'\b\d+(?:\.\d+)?\u00b0[NSEW]?\b',           # 40.7128 deg N
        # Stock/number changes
        r'[+\u2212-]\d+(?:\.\d+)?%?\b',              # +5.2, -3.8, +12%
        # Numbered items
        r'(?:No\.|#|\u2116)\s*\d+\b',                # No. 1, #1, No.1
        # Hyphenated number phrases
        r'\b\d+[-\u2013](?:year|day|hour|minute|month|week|meter|mile|foot|pound|dollar|point|game|run|set)\b',
        # Approximate/comparative
        r'[~\u2248<>\u2264\u2265]\s*\d+(?:\.\d+)?',            # ~100, >50, <100
        # Roman numerals (common ones in news)
        r'\b(?:III|II|IV|VI|VII|VIII|IX|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX|XXI)\b',
        # Feet and inches
        r"\b\d+['\u2032]\s*\d*[\"\u2033]?\b",            # 6'2", 5'
        # Plain numbers (catch-all, must be last)
        r'\b\d+(?:\.\d+)?\b',                   # 42, 3.14
    ]
    for pattern in number_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            add_highlight(match.start(), match.end(), "numbers")

    # 5. Verbs (news action words) - categorized with distinct colors
    verb_categories = {
        "verb_communication": [
            "said", "says", "saying", "stated", "states", "stating", "declared", "declares",
            "announced", "announces", "announcing", "told", "tells", "telling", "claimed", "claims", "claiming",
            "asserted", "asserts", "asserting", "remarked", "remarking", "commented", "comments", "commenting",
            "mentioned", "mentioning", "expressed", "expressing", "articulated", "articulating",
            "conveyed", "conveying", "communicated", "communicating", "spoke", "speaks", "speaking",
            "responded", "responds", "responding", "replied", "replies", "replying",
            "answered", "answers", "answering", "questioned", "questions", "questioning",
            "asked", "asks", "asking", "inquired", "inquiring", "queried", "querying",
            "interviewed", "interviewing", "briefed", "briefing", "addressed", "addressing",
            "emphasized", "emphasised", "emphasizing", "emphasising", "stressed", "stressing",
            "highlighted", "highlighting", "underscored", "underscoring", "reiterated", "reiterating",
            "repeated", "repeating", "clarified", "clarifying", "explained", "explains", "explaining",
            "elaborated", "elaborating", "detailed", "detailing", "outlined", "outlining",
            "summarized", "summarised", "summarizing", "summarising", "recapped", "recapping",
            "described", "describes", "describing", "depicted", "depicting",
            "characterized", "characterised", "characterizing", "characterising",
            "portrayed", "portraying", "presented", "presents", "presenting",
            "relayed", "relaying", "transmitted", "transmitting", "broadcast", "broadcasts", "broadcasting",
            "published", "publishes", "publishing", "posted", "posts", "posting",
            "tweeted", "tweets", "tweeting", "shared", "shares", "sharing",
            "reported", "reports", "reporting", "disclosed", "discloses", "disclosing",
            "revealed", "reveals", "revealing", "exposed", "exposes", "exposing",
            "leaked", "leaks", "leaking", "divulged", "divulging", "confirmed", "confirms", "confirming",
            "acknowledged", "acknowledges", "acknowledging", "admitted", "admits", "admitting",
            "conceded", "concedes", "conceding", "noted", "notes", "noting",
            "added", "adds", "adding", "cited", "cites", "citing", "quoted", "quotes", "quoting",
            "referenced", "referencing", "indicated", "indicates", "indicating",
            "signaled", "signalled", "signals", "signaling", "signalling",
            "suggested", "suggests", "suggesting", "implied", "implies", "implying",
            "hinted", "hints", "hinting", "alluded", "alluding", "insinuated", "insinuating",
            "speculated", "speculates", "speculating", "predicted", "predicts", "predicting",
            "forecast", "forecasts", "forecasting", "projected", "projects", "projecting",
            "estimated", "estimates", "estimating", "calculated", "calculating", "assessed", "assessing",
            "wrote", "writes", "writing", "penned", "penning", "authored", "authoring",
        ],
        "verb_accusation": [
            "accused", "accuses", "accusing", "blamed", "blames", "blaming",
            "alleged", "alleges", "alleging", "implicated", "implicating",
            "incriminated", "incriminating", "condemned", "condemns", "condemning",
            "denounced", "denounces", "denouncing",
            "criticized", "criticised", "criticizes", "criticises", "criticizing", "criticising",
            "slammed", "slams", "slamming", "blasted", "blasts", "blasting",
            "lambasted", "lambasting", "castigated", "castigating",
            "rebuked", "rebukes", "rebuking", "reprimanded", "reprimanding",
            "chastised", "chastising", "scolded", "scolding", "admonished", "admonishing",
            "faulted", "faults", "faulting", "singled", "singling",
            "attacked", "attacking", "assailed", "assailing", "vilified", "vilifying",
        ],
        "verb_support": [
            "praised", "praises", "praising", "commended", "commends", "commending",
            "applauded", "applauds", "applauding", "hailed", "hails", "hailing",
            "celebrated", "celebrates", "celebrating", "honored", "honoured", "honors", "honours", "honoring", "honouring",
            "recognized", "recognised", "recognizes", "recognises", "recognizing", "recognising",
            "endorsed", "endorses", "endorsing", "supported", "supports", "supporting",
            "backed", "backs", "backing", "championed", "champions", "championing",
            "advocated", "advocates", "advocating", "promoted", "promotes", "promoting",
            "defended", "defends", "defending", "justified", "justifies", "justifying",
            "validated", "validates", "validating", "upheld", "upholds", "upholding",
            "embraced", "embraces", "embracing", "touted", "touts", "touting",
        ],
        "verb_agreement": [
            "agreed", "agrees", "agreeing", "disagreed", "disagrees", "disagreeing",
            "concurred", "concurs", "concurring", "disputed", "disputes", "disputing",
            "contested", "contests", "contesting", "challenged", "challenges", "challenging",
            "opposed", "opposes", "opposing", "objected", "objects", "objecting",
            "protested", "protests", "protesting", "resisted", "resists", "resisting",
            "rejected", "rejects", "rejecting", "refused", "refuses", "refusing",
            "declined", "declines", "declining", "denied", "denies", "denying",
            "contradicted", "contradicts", "contradicting", "countered", "counters", "countering",
            "rebutted", "rebuts", "rebutting", "refuted", "refutes", "refuting",
            "dismissed", "dismisses", "dismissing", "doubted", "doubts", "doubting",
        ],
        "verb_decision": [
            "decided", "decides", "deciding", "determined", "determines", "determining",
            "concluded", "concludes", "concluding", "resolved", "resolves", "resolving",
            "ruled", "rules", "ruling", "judged", "judges", "judging", "decreed", "decreeing",
            "ordered", "orders", "ordering", "commanded", "commands", "commanding",
            "directed", "directs", "directing", "instructed", "instructs", "instructing",
            "mandated", "mandates", "mandating", "required", "requires", "requiring",
            "demanded", "demands", "demanding", "requested", "requests", "requesting",
            "urged", "urges", "urging", "encouraged", "encourages", "encouraging",
            "pressured", "pressures", "pressuring", "pushed", "pushes", "pushing",
            "lobbied", "lobbies", "lobbying", "petitioned", "petitions", "petitioning",
            "appealed", "appeals", "appealing", "sought", "seeks", "seeking",
            "pursued", "pursues", "pursuing", "aimed", "aims", "aiming",
            "intended", "intends", "intending", "planned", "plans", "planning",
            "proposed", "proposes", "proposing", "recommended", "recommends", "recommending",
            "forced", "forces", "forcing", "compelled", "compels", "compelling",
            "labeled", "labelled", "labels", "labeling", "labelling",
            "designated", "designates", "designating", "classified", "classifies", "classifying",
        ],
        "verb_political": [
            "enacted", "enacts", "enacting", "legislated", "legislates", "legislating",
            "passed", "passes", "passing", "vetoed", "vetoes", "vetoing",
            "signed", "signs", "signing", "ratified", "ratifies", "ratifying",
            "amended", "amends", "amending", "repealed", "repeals", "repealing",
            "overturned", "overturns", "overturning", "enforced", "enforces", "enforcing",
            "implemented", "implements", "implementing", "administered", "administers", "administering",
            "governed", "governs", "governing", "regulated", "regulates", "regulating",
            "deregulated", "deregulates", "deregulating", "sanctioned", "sanctions", "sanctioning",
            "embargoed", "embargoes", "embargoing",
            "authorized", "authorised", "authorizes", "authorises", "authorizing", "authorising",
            "approved", "approves", "approving", "certified", "certifies", "certifying",
            "licensed", "licenced", "licenses", "licences", "licensing", "licencing",
            "permitted", "permits", "permitting", "banned", "bans", "banning",
            "prohibited", "prohibits", "prohibiting", "blocked", "blocks", "blocking",
            "suspended", "suspends", "suspending", "revoked", "revokes", "revoking",
            "rescinded", "rescinds", "rescinding", "appointed", "appoints", "appointing",
            "nominated", "nominates", "nominating", "elected", "elects", "electing",
            "inaugurated", "inaugurates", "inaugurating", "sworn", "swore", "swearing",
            "impeached", "impeaches", "impeaching", "ousted", "ousts", "ousting",
            "toppled", "topples", "toppling", "overthrew", "overthrows", "overthrowing",
            "resigned", "resigns", "resigning", "retired", "retires", "retiring", "quit", "quits", "quitting",
        ],
        "verb_military": [
            "attacked", "attacks", "attacking", "struck", "strikes", "striking",
            "bombed", "bombs", "bombing", "shelled", "shells", "shelling",
            "fired", "fires", "firing", "shot", "shoots", "shooting",
            "targeted", "targets", "targeting", "assaulted", "assaults", "assaulting",
            "invaded", "invades", "invading", "occupied", "occupies", "occupying",
            "seized", "seizes", "seizing", "captured", "captures", "capturing",
            "conquered", "conquers", "conquering", "liberated", "liberates", "liberating",
            "retreated", "retreats", "retreating", "withdrew", "withdraws", "withdrawing",
            "deployed", "deploys", "deploying", "mobilized", "mobilised", "mobilizes", "mobilises", "mobilizing", "mobilising",
            "escalated", "escalates", "escalating", "retaliated", "retaliates", "retaliating",
            "fortified", "fortifies", "fortifying", "besieged", "besieges", "besieging",
            "blockaded", "blockades", "blockading", "ambushed", "ambushes", "ambushing",
            "raided", "raids", "raiding", "stormed", "storms", "storming",
            "clashed", "clashes", "clashing", "fought", "fights", "fighting",
            "battled", "battles", "battling", "killed", "kills", "killing",
            "slew", "slays", "slaying", "murdered", "murders", "murdering",
            "assassinated", "assassinates", "assassinating", "executed", "executes", "executing",
            "massacred", "massacres", "massacring", "slaughtered", "slaughters", "slaughtering",
            "wounded", "wounds", "wounding", "injured", "injures", "injuring",
            "maimed", "maims", "maiming", "hurt", "hurts", "hurting",
            "died", "dies", "dying", "perished", "perishes", "perishing",
            "surrendered", "surrenders", "surrendering", "capitulated", "capitulates", "capitulating",
            "ceased", "ceases", "ceasing",
        ],
        "verb_legal": [
            "arrested", "arrests", "arresting", "detained", "detains", "detaining",
            "jailed", "jails", "jailing", "imprisoned", "imprisons", "imprisoning",
            "incarcerated", "incarcerates", "incarcerating", "released", "releases", "releasing",
            "freed", "frees", "freeing", "charged", "charges", "charging",
            "indicted", "indicts", "indicting", "prosecuted", "prosecutes", "prosecuting",
            "tried", "tries", "trying", "convicted", "convicts", "convicting",
            "acquitted", "acquits", "acquitting", "sentenced", "sentences", "sentencing",
            "fined", "fines", "fining", "pardoned", "pardons", "pardoning",
            "exonerated", "exonerates", "exonerating", "testified", "testifies", "testifying",
            "sued", "sues", "suing", "settled", "settles", "settling",
            "litigated", "litigates", "litigating", "extradited", "extradites", "extraditing",
            "deported", "deports", "deporting", "subpoenaed", "subpoenas", "subpoenaing",
        ],
        "verb_economic": [
            "invested", "invests", "investing", "divested", "divests", "divesting",
            "acquired", "acquires", "acquiring", "merged", "merges", "merging",
            "bought", "buys", "buying", "sold", "sells", "selling",
            "traded", "trades", "trading", "profited", "profits", "profiting",
            "earned", "earns", "earning", "spent", "spends", "spending",
            "paid", "pays", "paying", "funded", "funds", "funding",
            "financed", "finances", "financing", "borrowed", "borrows", "borrowing",
            "lent", "lends", "lending", "defaulted", "defaults", "defaulting",
            "restructured", "restructures", "restructuring", "downsized", "downsizes", "downsizing",
            "expanded", "expands", "expanding", "grew", "grows", "growing",
            "shrank", "shrinks", "shrinking", "surged", "surges", "surging",
            "plunged", "plunges", "plunging", "soared", "soars", "soaring",
            "plummeted", "plummets", "plummeting", "rallied", "rallies", "rallying",
            "rose", "rises", "rising", "fell", "falls", "falling",
            "increased", "increases", "increasing", "decreased", "decreases", "decreasing",
            "doubled", "doubles", "doubling", "tripled", "triples", "tripling",
            "halved", "halves", "halving", "slashed", "slashes", "slashing",
            "cut", "cuts", "cutting", "raised", "raises", "raising",
            "boosted", "boosts", "boosting", "lifted", "lifts", "lifting",
            "lowered", "lowers", "lowering", "hired", "hires", "hiring",
            "billed", "bills", "billing", "cost", "costs", "costing",
        ],
        "verb_discovery": [
            "discovered", "discovers", "discovering", "found", "finds", "finding",
            "uncovered", "uncovers", "uncovering", "unearthed", "unearths", "unearthing",
            "detected", "detects", "detecting", "identified", "identifies", "identifying",
            "located", "locates", "locating", "traced", "traces", "tracing",
            "tracked", "tracks", "tracking", "monitored", "monitors", "monitoring",
            "surveyed", "surveys", "surveying", "examined", "examines", "examining",
            "analyzed", "analysed", "analyzes", "analyses", "analyzing", "analysing",
            "investigated", "investigates", "investigating", "probed", "probes", "probing",
            "scrutinized", "scrutinised", "scrutinizes", "scrutinises", "scrutinizing", "scrutinising",
            "reviewed", "reviews", "reviewing", "audited", "audits", "auditing",
            "inspected", "inspects", "inspecting", "verified", "verifies", "verifying",
            "tested", "tests", "testing", "searched", "searches", "searching",
            "recovered", "recovers", "recovering", "encountered", "encounters", "encountering",
            "proved", "proves", "proving", "proven", "conducted", "conducts", "conducting",
        ],
        "verb_change": [
            "changed", "changes", "changing", "altered", "alters", "altering",
            "modified", "modifies", "modifying", "revised", "revises", "revising",
            "updated", "updates", "updating", "upgraded", "upgrades", "upgrading",
            "improved", "improves", "improving", "enhanced", "enhances", "enhancing",
            "transformed", "transforms", "transforming", "converted", "converts", "converting",
            "shifted", "shifts", "shifting", "transitioned", "transitions", "transitioning",
            "evolved", "evolves", "evolving", "adapted", "adapts", "adapting",
            "adjusted", "adjusts", "adjusting", "reformed", "reforms", "reforming",
            "restructured", "restructures", "restructuring",
            "reorganized", "reorganised", "reorganizes", "reorganises", "reorganizing", "reorganising",
            "overhauled", "overhauls", "overhauling", "replaced", "replaces", "replacing",
            "substituted", "substitutes", "substituting", "swapped", "swaps", "swapping",
            "switched", "switches", "switching", "reversed", "reverses", "reversing",
        ],
        "verb_creation": [
            "created", "creates", "creating", "built", "builds", "building",
            "constructed", "constructs", "constructing", "developed", "develops", "developing",
            "designed", "designs", "designing", "invented", "invents", "inventing",
            "launched", "launches", "launching", "introduced", "introduces", "introducing",
            "unveiled", "unveils", "unveiling", "opened", "opens", "opening",
            "established", "establishes", "establishing", "founded", "founds", "founding",
            "started", "starts", "starting", "began", "begins", "beginning",
            "initiated", "initiates", "initiating", "closed", "closes", "closing",
            "shut", "shuts", "shutting", "ended", "ends", "ending",
            "terminated", "terminates", "terminating", "demolished", "demolishes", "demolishing",
            "destroyed", "destroys", "destroying", "ruined", "ruins", "ruining",
            "damaged", "damages", "damaging", "wrecked", "wrecks", "wrecking",
            "devastated", "devastates", "devastating", "razed", "razes", "razing",
            "leveled", "levelled", "levels", "leveling", "levelling",
            "collapsed", "collapses", "collapsing", "imploded", "implodes", "imploding",
            "exploded", "explodes", "exploding", "detonated", "detonates", "detonating",
            "burned", "burnt", "burns", "burning", "flooded", "floods", "flooding",
            "sank", "sinks", "sinking",
        ],
        "verb_movement": [
            "moved", "moves", "moving", "traveled", "travelled", "travels", "traveling", "travelling",
            "went", "goes", "going", "came", "comes", "coming",
            "arrived", "arrives", "arriving", "departed", "departs", "departing",
            "left", "leaves", "leaving", "returned", "returns", "returning",
            "visited", "visits", "visiting", "toured", "tours", "touring",
            "fled", "flees", "fleeing", "escaped", "escapes", "escaping",
            "evacuated", "evacuates", "evacuating", "migrated", "migrates", "migrating",
            "immigrated", "immigrates", "immigrating", "emigrated", "emigrates", "emigrating",
            "expelled", "expels", "expelling", "exiled", "exiles", "exiling",
            "banished", "banishes", "banishing", "crossed", "crosses", "crossing",
            "entered", "enters", "entering", "exited", "exits", "exiting",
            "landed", "lands", "landing", "crashed", "crashes", "crashing",
            "collided", "collides", "colliding", "derailed", "derails", "derailing",
            "capsized", "capsizes", "capsizing", "embarked", "embarks", "embarking",
        ],
        "verb_emotion": [
            "feared", "fears", "fearing", "worried", "worries", "worrying",
            "concerned", "concerns", "concerning", "alarmed", "alarms", "alarming",
            "shocked", "shocks", "shocking", "surprised", "surprises", "surprising",
            "stunned", "stuns", "stunning", "outraged", "outrages", "outraging",
            "angered", "angers", "angering", "infuriated", "infuriates", "infuriating",
            "pleased", "pleases", "pleasing", "delighted", "delights", "delighting",
            "thrilled", "thrills", "thrilling", "excited", "excites", "exciting",
            "relieved", "relieves", "relieving", "disappointed", "disappoints", "disappointing",
            "frustrated", "frustrates", "frustrating", "dismayed", "dismays", "dismaying",
            "mourned", "mourns", "mourning", "grieved", "grieves", "grieving",
            "lamented", "laments", "lamenting", "cheered", "cheers", "cheering",
            "welcomed", "welcomes", "welcoming",
        ],
        "verb_prevention": [
            "prevented", "prevents", "preventing", "stopped", "stops", "stopping",
            "halted", "halts", "halting", "barred", "bars", "barring",
            "thwarted", "thwarts", "thwarting", "foiled", "foils", "foiling",
            "averted", "averts", "averting", "avoided", "avoids", "avoiding",
            "protected", "protects", "protecting", "shielded", "shields", "shielding",
            "guarded", "guards", "guarding", "secured", "secures", "securing",
            "safeguarded", "safeguards", "safeguarding", "preserved", "preserves", "preserving",
            "saved", "saves", "saving", "rescued", "rescues", "rescuing",
        ],
        "verb_competition": [
            "won", "wins", "winning", "lost", "loses", "losing",
            "defeated", "defeats", "defeating", "beat", "beats", "beating",
            "prevailed", "prevails", "prevailing", "triumphed", "triumphs", "triumphing",
            "succeeded", "succeeds", "succeeding", "failed", "fails", "failing",
            "achieved", "achieves", "achieving", "accomplished", "accomplishes", "accomplishing",
            "completed", "completes", "completing", "finished", "finishes", "finishing",
            "led", "leads", "leading", "trailed", "trails", "trailing",
            "tied", "ties", "tying", "drew", "draws", "drawing",
            "qualified", "qualifies", "qualifying", "eliminated", "eliminates", "eliminating",
            "advanced", "advances", "advancing", "competed", "competes", "competing",
        ],
        "verb_medical": [
            "diagnosed", "diagnoses", "diagnosing", "treated", "treats", "treating",
            "cured", "cures", "curing", "healed", "heals", "healing",
            "hospitalized", "hospitalised", "hospitalizes", "hospitalises", "hospitalizing", "hospitalising",
            "operated", "operates", "operating", "vaccinated", "vaccinates", "vaccinating",
            "infected", "infects", "infecting", "contracted", "contracts", "contracting",
            "spread", "spreads", "spreading", "transmitted", "transmits", "transmitting",
            "quarantined", "quarantines", "quarantining", "isolated", "isolates", "isolating",
            "sickened", "sickens", "sickening", "suffered", "suffers", "suffering",
        ],
    }
    for category, verbs in verb_categories.items():
        pattern = r'\b(?:' + '|'.join(verbs) + r')\b'
        for match in re.finditer(pattern, text, re.IGNORECASE):
            add_highlight(match.start(), match.end(), category)

    # === ENTITIES (clickable) ===

    # 4. Titles followed by names - match FIRST as one unit (e.g., "president Xi Jinping")
    for title in app.titles:
        pattern = r'\b(' + re.escape(title) + r'\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        for match in re.finditer(pattern, text, re.IGNORECASE):
            full_phrase = match.group(1)
            add_highlight(match.start(), match.end(), "people", full_phrase)

    # 5. Find ALL capitalized word sequences, then classify them
    # This matches: "Zhang Youxia", "President Xi Jinping", "Central Military Commission"
    # Also handles possessives: "China's" -> "China"
    cap_sequence_pattern = r"([A-Z][a-z]+(?:[-'][a-z]+)?(?:\s+(?:of|the|and|for|de|von|van)?\s*[A-Z][a-z]+(?:[-'][a-z]+)?)*)"

    # Collect all sequences first
    sequences = []
    for match in re.finditer(cap_sequence_pattern, text):
        phrase = match.group(1)
        start = match.start()
        end = match.end()

        # Handle possessive 's at the end - include it in highlight but not search
        if end < len(text) and text[end:end+2] == "'s":
            display_end = end + 2
        else:
            display_end = end

        sequences.append((start, end, display_end, phrase))

    # Words to skip (sentence starters, common words)
    skip_words = {
        "the", "a", "an", "this", "that", "these", "those", "it", "its",
        "has", "have", "had", "been", "was", "were", "are", "is", "be",
        "said", "says", "told", "added", "noted", "asked", "called",
        "new", "many", "more", "most", "some", "all", "other", "such",
        "also", "just", "even", "still", "well", "back", "now", "then",
        "but", "and", "for", "not", "you", "his", "her", "their", "our",
        "first", "last", "next", "high", "low", "long", "short", "big",
        "according", "including", "during", "after", "before", "since",
        "while", "where", "when", "which", "what", "who", "how", "why",
        "continue", "reading", "here", "there", "very", "much", "far",
        "however", "although", "though", "because", "therefore", "thus",
    }

    # Classify and highlight each sequence
    for start, end, display_end, phrase in sequences:
        phrase_lower = phrase.lower()
        words = phrase.split()

        # Skip single common words
        if len(words) == 1 and words[0].lower() in skip_words:
            continue

        # Check if this is at sentence start (position 0 or after ". ")
        at_sentence_start = False
        if start == 0:
            at_sentence_start = True
        elif start > 1 and text[start-2:start] in (". ", "! ", "? "):
            at_sentence_start = True

        # At sentence start, only skip if it's a single common word
        # Multi-word sequences (names) at sentence start should still be highlighted
        if at_sentence_start and len(words) == 1:
            # Single word at sentence start - only highlight if known entity
            if phrase_lower not in app.countries and phrase_lower not in app.places and phrase_lower not in app.organizations:
                continue

        # Determine category by checking against known entities and patterns
        category = None
        search_term = phrase

        # Check known entity databases (exact match)
        if phrase_lower in app.leaders:
            category = "people"
        elif phrase_lower in app.events:
            category = "events"
        elif phrase_lower in app.military:
            category = "military"
        elif phrase_lower in app.government:
            category = "government"
        elif phrase_lower in app.organizations:
            category = "organizations"
        elif phrase_lower in app.countries:
            category = "countries"
        elif phrase_lower in app.places:
            category = "places"

        # Check for title + name pattern (e.g., "President Xi Jinping")
        elif words[0].lower() in app.titles:
            category = "titles"
            # If more than just title, it's title + name
            if len(words) > 1:
                # Highlight whole thing as title+person combined
                category = "people"
                search_term = " ".join(words[1:])  # Search just the name

        # Check for organizational patterns (X Y Commission/Ministry/etc.)
        elif any(w.lower() in {"commission", "committee", "council", "ministry",
                               "department", "bureau", "agency", "authority",
                               "administration", "board", "corps", "command"}
                for w in words):
            category = "government"

        # Check for military patterns
        elif any(w.lower() in {"army", "navy", "force", "forces", "guard", "corps",
                               "fleet", "brigade", "division", "regiment"}
                for w in words):
            category = "military"

        # Check for organization patterns
        elif any(w.lower() in {"university", "college", "institute", "corporation",
                               "company", "inc", "corp", "foundation", "association",
                               "bank", "group", "trust"}
                for w in words):
            category = "organizations"

        # Default: if 2-3 capitalized words, likely a person's name
        elif len(words) >= 2 and len(words) <= 3:
            # Check if all words look like name parts (not org keywords)
            looks_like_name = all(
                w[0].isupper() and w.lower() not in skip_words
                for w in words
            )
            if looks_like_name:
                category = "people"

        # Single capitalized word in middle of sentence - check databases
        elif len(words) == 1:
            word = words[0]
            word_lower = word.lower()
            if word_lower in app.countries:
                category = "countries"
            elif word_lower in app.places:
                category = "places"
            elif word_lower in app.organizations:
                category = "organizations"
            elif not at_sentence_start:
                # Mid-sentence capitalization = proper noun
                category = "proper_nouns"

        # Fallback: mid-sentence capitalized phrase not matching any category
        if not category and not at_sentence_start and len(words) >= 1:
            category = "proper_nouns"

        # Apply highlight if category was determined
        if category:
            add_highlight(start, display_end, category, search_term)


def on_wiki_link_click(app, event):
    """Handle click on wiki link - open Wikipedia search."""
    index = app.preview_text.index(f"@{event.x},{event.y}")
    line, char = index.split(".")
    char_offset = int(char)

    for (start, end), (search_term, category) in app.wiki_link_targets.items():
        if start <= char_offset < end:
            import urllib.parse
            query = urllib.parse.quote(search_term)
            url = f"https://en.wikipedia.org/wiki/Special:Search?search={query}&go=Go"
            webbrowser.open(url)
            return
