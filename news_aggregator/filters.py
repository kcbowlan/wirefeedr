# filters.py - Content filtering logic

import re
from typing import Optional, List
from collections import defaultdict
from config import (
    OPINION_URL_PATTERNS,
    OPINION_TITLE_PATTERNS,
    SENSATIONAL_KEYWORDS,
    CLICKBAIT_NUMBER_PATTERNS,
    ARTICLE_GRADES
)

# Common stop words to exclude from clustering
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "must", "shall", "can", "need", "dare", "ought", "used",
    "it", "its", "this", "that", "these", "those", "i", "you", "he", "she", "we",
    "they", "what", "which", "who", "whom", "how", "when", "where", "why",
    "all", "each", "every", "both", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "also", "now", "new", "says", "said", "after", "before", "over", "into",
    "about", "up", "out", "off", "down", "here", "there", "then", "once", "again",
    "news", "report", "reports", "update", "latest", "breaking"
}


class FilterEngine:
    def __init__(self, custom_keywords: list = None):
        """
        Initialize the filter engine.

        Args:
            custom_keywords: List of dicts with 'keyword' and 'weight' keys
        """
        self.custom_keywords = custom_keywords or []
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for performance."""
        self.clickbait_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in CLICKBAIT_NUMBER_PATTERNS
        ]

    def update_custom_keywords(self, custom_keywords: list):
        """Update the list of custom filter keywords."""
        self.custom_keywords = custom_keywords

    def calculate_objectivity_score(self, title: str, link: str, summary: str = "",
                                     factual_rating: str = "") -> int:
        """
        Calculate an objectivity score for an article (0-100).

        Higher score = more likely to be factual/objective content.

        Args:
            title: Article headline
            link: Article URL
            summary: Article summary/description
            factual_rating: Source's factual rating (Very High, High, Mostly Factual, Mixed)

        Returns:
            int: Objectivity score from 0 (sensational) to 100 (factual)
        """
        deductions = 0

        # Check for opinion URL patterns (high weight - likely opinion content)
        deductions += self._check_opinion_url(link)

        # Check for opinion indicators in title
        deductions += self._check_opinion_title(title)

        # Check for sensational keywords in title and summary
        deductions += self._check_sensational_keywords(title, summary)

        # Check for clickbait patterns
        deductions += self._check_clickbait_patterns(title)

        # Check for excessive punctuation
        deductions += self._check_excessive_punctuation(title)

        # Check for ALL CAPS words
        deductions += self._check_all_caps(title)

        # Check custom keywords
        deductions += self._check_custom_keywords(title, summary)

        # Summary-specific analysis (if summary available)
        if summary:
            # Negative factors in summary (capped at 25)
            deductions += self._check_summary_negative(summary)

            # Positive factors in summary (reduce deductions, capped at 15)
            bonus = self._check_summary_positive(summary)
            deductions = max(0, deductions - bonus)

        # Apply source factual rating modifier
        deductions -= self._get_factual_modifier(factual_rating)

        # Invert: 100 = perfectly objective, 0 = highly sensational
        return max(min(100 - deductions, 100), 0)

    def _get_factual_modifier(self, factual_rating: str) -> int:
        """Get score modifier based on source's factual rating."""
        modifiers = {
            "Very High": 5,    # Bonus for highly factual sources
            "High": 0,         # Neutral
            "Mostly Factual": -5,  # Small penalty
            "Mixed": -10,      # Larger penalty for unreliable sources
        }
        return modifiers.get(factual_rating, 0)

    def get_corroboration_bonus(self, cluster_size: int) -> int:
        """Get score bonus based on how many sources reported the same story."""
        if cluster_size >= 4:
            return 8   # Widely reported
        elif cluster_size >= 3:
            return 5   # Well corroborated
        elif cluster_size >= 2:
            return 2   # Some corroboration
        else:
            return 0   # Single source (no bonus, no penalty)

    def _check_opinion_url(self, link: str) -> int:
        """Check if URL contains opinion/editorial patterns."""
        link_lower = link.lower()
        for pattern in OPINION_URL_PATTERNS:
            if pattern in link_lower:
                return 40  # Strong indicator of opinion content
        return 0

    def _check_opinion_title(self, title: str) -> int:
        """Check if title indicates opinion content."""
        title_lower = title.lower()
        for pattern in OPINION_TITLE_PATTERNS:
            if pattern in title_lower:
                return 35  # Strong indicator of opinion content
        return 0

    def _check_sensational_keywords(self, title: str, summary: str) -> int:
        """Check for sensational keywords in title and summary."""
        combined = f"{title} {summary}".lower()
        score = 0

        for keyword in SENSATIONAL_KEYWORDS:
            if keyword in combined:
                # Title matches are weighted more heavily
                if keyword in title.lower():
                    score += 15
                else:
                    score += 5

        return min(score, 40)  # Cap keyword contribution

    def _check_clickbait_patterns(self, title: str) -> int:
        """Check for clickbait number patterns."""
        for pattern in self.clickbait_patterns:
            if pattern.search(title):
                return 20
        return 0

    def _check_excessive_punctuation(self, title: str) -> int:
        """Check for excessive punctuation marks."""
        score = 0

        # Multiple exclamation marks
        if "!!" in title:
            score += 10
        elif title.count("!") > 1:
            score += 5

        # Multiple question marks
        if "??" in title:
            score += 10
        elif title.count("?") > 2:
            score += 5

        # Ellipsis abuse
        if "..." in title and title.count("...") > 1:
            score += 5

        return min(score, 15)

    def _check_all_caps(self, title: str) -> int:
        """Check for ALL CAPS words (excluding common abbreviations)."""
        # Common abbreviations to ignore
        common_abbrevs = {
            "US", "USA", "UK", "EU", "UN", "NATO", "FBI", "CIA", "NASA",
            "CEO", "CFO", "CTO", "GDP", "IPO", "AI", "NFL", "NBA", "MLB",
            "COVID", "WHO", "CDC", "FDA", "EPA", "IRS", "DOJ", "DOD"
        }

        words = title.split()
        caps_words = 0

        for word in words:
            # Remove punctuation for checking
            clean_word = re.sub(r"[^\w]", "", word)
            if len(clean_word) >= 3 and clean_word.isupper():
                if clean_word not in common_abbrevs:
                    caps_words += 1

        if caps_words >= 3:
            return 15
        elif caps_words >= 2:
            return 10
        elif caps_words >= 1:
            return 5

        return 0

    def _check_custom_keywords(self, title: str, summary: str) -> int:
        """Check for user-defined custom keywords."""
        combined = f"{title} {summary}".lower()
        score = 0

        for kw in self.custom_keywords:
            keyword = kw.get("keyword", "").lower()
            weight = kw.get("weight", 10)
            if keyword and keyword in combined:
                score += weight

        return min(score, 30)  # Cap custom keyword contribution

    def _check_summary_positive(self, summary: str) -> int:
        """Check for positive journalistic signals in summary. Returns bonus points."""
        bonus = 0
        summary_lower = summary.lower()

        # Direct attribution (+5)
        attribution_patterns = [
            r'\bsaid\s+[A-Z]',  # "said John"
            r'\baccording to\b',
            r'\b(confirmed|announced|stated|reported)\s+by\b',
            r'\bofficials\s+(said|confirmed|announced)\b',
            r'\bspokesperson\s+said\b',
        ]
        for pattern in attribution_patterns:
            if re.search(pattern, summary, re.IGNORECASE):
                bonus += 5
                break  # Only count once

        # Quoted speech (+5) - text in quotation marks
        quotes = re.findall(r'["\u201c][^"\u201d]{10,}["\u201d]', summary)
        if quotes:
            bonus += 5

        # Specific numbers (+3) - percentages, dollar amounts, counts
        number_patterns = [
            r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion))?',  # Money
            r'\b\d+(?:\.\d+)?%',  # Percentages
            r'\b\d{1,3}(?:,\d{3})+\b',  # Large numbers with commas
        ]
        for pattern in number_patterns:
            if re.search(pattern, summary):
                bonus += 3
                break

        # Dates/timeframes (+3)
        date_patterns = [
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d',
            r'\blast\s+(week|month|year)\b',
            r'\b(yesterday|today|tomorrow)\b',
            r'\bsince\s+\d{4}\b',
        ]
        for pattern in date_patterns:
            if re.search(pattern, summary_lower):
                bonus += 3
                break

        # Hedging language (+2) - shows journalistic caution
        hedging = ['allegedly', 'reportedly', 'unconfirmed', 'suspected', 'appears to']
        if any(h in summary_lower for h in hedging):
            bonus += 2

        return min(bonus, 15)  # Cap at 15

    def _check_summary_negative(self, summary: str) -> int:
        """Check for negative editorial signals in summary. Returns deduction points."""
        deductions = 0
        summary_lower = summary.lower()

        # First-person opinion (-10)
        opinion_phrases = [
            r'\bi think\b', r'\bi believe\b', r'\bin my view\b', r'\bin my opinion\b',
            r'\bwe must\b', r'\bwe should\b', r'\bwe need to\b',
            r'\bit\'s clear that\b', r'\bobviously\b',
        ]
        for pattern in opinion_phrases:
            if re.search(pattern, summary_lower):
                deductions += 10
                break

        # Imperative/prescriptive language (-8)
        imperatives = [
            r'\b(should|must|need to|have to|ought to)\s+\w+',
        ]
        for pattern in imperatives:
            if re.search(pattern, summary_lower):
                deductions += 8
                break

        # Vague attribution (-5)
        vague_sources = [
            r'\bcritics\s+(say|argue|claim|believe)\b',
            r'\bsome\s+(say|argue|claim|believe)\b',
            r'\bmany\s+(say|argue|claim|believe)\b',
            r'\bexperts\s+(say|argue|claim|believe)\b',
            r'\bsources\s+say\b',
        ]
        vague_count = sum(1 for p in vague_sources if re.search(p, summary_lower))
        deductions += min(vague_count * 5, 10)  # Cap at 10 for vagueness

        # Emotional adjectives (-5)
        emotional_words = [
            'horrific', 'horrifying', 'disgusting', 'outrageous', 'shocking',
            'amazing', 'incredible', 'unbelievable', 'terrifying', 'devastating',
            'shameful', 'despicable', 'appalling', 'hideous', 'atrocious',
            'wonderful', 'fantastic', 'brilliant', 'genius',
        ]
        if any(word in summary_lower for word in emotional_words):
            deductions += 5

        # Rhetorical questions (-5)
        if re.search(r'\?\s*$', summary) or re.search(r'but (is|are|was|were|will|can|should)\s+\w+.*\?', summary_lower):
            deductions += 5

        # Absolutist language (-5)
        absolutist = [
            r'\balways\b', r'\bnever\b', r'\beveryone\b', r'\bnobody\b',
            r'\bproves\b', r'\bundeniable\b', r'\bunquestionable\b',
        ]
        if any(re.search(p, summary_lower) for p in absolutist):
            deductions += 5

        return min(deductions, 25)  # Cap at 25

    def get_article_grade(self, score: int) -> tuple:
        """Get the grade tuple (letter, label, color) for a score."""
        for max_score, letter, label, color in ARTICLE_GRADES:
            if score <= max_score:
                return (letter, label, color)
        # Fallback to F grade
        return ("F", "Opinion/Hype", "#c0392b")

    def get_noise_level(self, score: int) -> str:
        """Get a human-readable score label (e.g., '85 - Solid')."""
        _, label, _ = self.get_article_grade(score)
        return f"{score} - {label}"

    def get_noise_color(self, score: int) -> str:
        """Get a color code for the article grade."""
        _, _, color = self.get_article_grade(score)
        return color

    def analyze_article(self, title: str, link: str, summary: str = "") -> dict:
        """
        Analyze an article and return detailed scoring breakdown.

        Useful for debugging and understanding why an article was scored.
        """
        breakdown = {
            "opinion_url": self._check_opinion_url(link),
            "opinion_title": self._check_opinion_title(title),
            "sensational_keywords": self._check_sensational_keywords(title, summary),
            "clickbait_patterns": self._check_clickbait_patterns(title),
            "excessive_punctuation": self._check_excessive_punctuation(title),
            "all_caps": self._check_all_caps(title),
            "custom_keywords": self._check_custom_keywords(title, summary),
            "summary_negative": self._check_summary_negative(summary) if summary else 0,
            "summary_positive_bonus": -(self._check_summary_positive(summary)) if summary else 0,
        }

        total_deductions = sum(v for v in breakdown.values() if v > 0)
        total_bonus = abs(sum(v for v in breakdown.values() if v < 0))
        net_deductions = max(0, total_deductions - total_bonus)
        final_score = max(0, min(100, 100 - net_deductions))

        return {
            "final_score": final_score,
            "total_deductions": total_deductions,
            "total_bonus": total_bonus,
            "noise_level": self.get_noise_level(final_score),
            "breakdown": breakdown
        }

    # Topic Clustering Methods

    def _extract_keywords(self, text: str) -> set:
        """Extract significant keywords from text, removing stop words."""
        # Lowercase and extract words
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        # Remove stop words and return as set
        return {w for w in words if w not in STOP_WORDS}

    def _calculate_similarity(self, keywords1: set, keywords2: set) -> float:
        """Calculate Jaccard similarity between two keyword sets."""
        if not keywords1 or not keywords2:
            return 0.0
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        return intersection / union if union > 0 else 0.0

    def cluster_articles(self, articles: List[dict], similarity_threshold: float = 0.3) -> List[dict]:
        """
        Cluster similar articles together.

        Args:
            articles: List of article dicts with 'title' and 'id' keys
            similarity_threshold: Minimum similarity (0-1) to group articles

        Returns:
            List of cluster dicts, each containing:
            - 'articles': list of articles in cluster
            - 'representative': the best article (highest score) to show
            - 'keywords': common keywords describing the topic
            - 'count': number of articles in cluster
        """
        if not articles:
            return []

        # Extract keywords for each article
        article_keywords = []
        for article in articles:
            keywords = self._extract_keywords(article.get("title", ""))
            article_keywords.append({
                "article": article,
                "keywords": keywords,
                "cluster_id": None
            })

        # Greedy clustering: assign each article to existing cluster or create new one
        clusters = []

        for item in article_keywords:
            best_cluster = None
            best_similarity = 0

            # Find best matching existing cluster
            for cluster in clusters:
                # Compare against cluster's combined keywords
                similarity = self._calculate_similarity(item["keywords"], cluster["keywords"])
                if similarity > best_similarity and similarity >= similarity_threshold:
                    best_similarity = similarity
                    best_cluster = cluster

            if best_cluster:
                # Add to existing cluster
                best_cluster["articles"].append(item["article"])
                best_cluster["keywords"] |= item["keywords"]  # Expand cluster keywords
            else:
                # Create new cluster
                clusters.append({
                    "articles": [item["article"]],
                    "keywords": item["keywords"].copy()
                })

        # Finalize clusters: pick representative, generate label
        result = []
        for cluster in clusters:
            # Sort by quality score (highest first) and pick best as representative
            sorted_articles = sorted(
                cluster["articles"],
                key=lambda a: a.get("noise_score", 0),
                reverse=True
            )

            # Get top 3 most common keywords for label
            all_keywords = []
            for article in cluster["articles"]:
                all_keywords.extend(self._extract_keywords(article.get("title", "")))

            # Count keyword frequency
            keyword_counts = defaultdict(int)
            for kw in all_keywords:
                keyword_counts[kw] += 1

            # Top keywords (appear in multiple articles)
            top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            topic_label = ", ".join(kw for kw, count in top_keywords if count > 1) or \
                         ", ".join(kw for kw, count in top_keywords[:2])

            result.append({
                "representative": sorted_articles[0],
                "articles": sorted_articles,
                "count": len(sorted_articles),
                "topic": topic_label.title() if topic_label else "General",
                "is_cluster": len(sorted_articles) > 1
            })

        # Sort clusters by representative's published date
        result.sort(key=lambda c: c["representative"].get("published", "") or "", reverse=True)

        return result
