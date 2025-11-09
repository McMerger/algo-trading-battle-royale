"""
News and event adapter using RSS feeds.

Monitors Fed, SEC, Treasury announcements and breaking news
for event-driven trading signals.
"""

import requests
import feedparser
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re


class NewsAdapter:
    """
    RSS feed adapter for financial news and announcements.

    Monitors:
    - Federal Reserve press releases
    - SEC announcements
    - US Treasury statements
    - Major financial news outlets
    """

    def __init__(self):
        # RSS feed URLs for major sources
        self.feeds = {
            'fed': 'https://www.federalreserve.gov/feeds/press_all.xml',
            'sec': 'https://www.sec.gov/news/pressreleases.rss',
            'treasury': 'https://home.treasury.gov/rss/press-releases',
            'reuters': 'https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best',
            'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/'
        }

        # Keywords that matter for trading
        self.high_impact_keywords = {
            'fed': ['rate decision', 'hike', 'cut', 'inflation', 'employment', 'fomc'],
            'sec': ['bitcoin', 'crypto', 'etf', 'enforcement', 'fraud'],
            'treasury': ['sanctions', 'debt', 'yields', 'bonds'],
            'crypto': ['bitcoin', 'ethereum', 'regulation', 'sec', 'etf']
        }

        self.cache = {}
        self.cache_ttl = 60  # 1 minute cache

    def fetch_feed(self, source: str) -> List[Dict]:
        """
        Fetch and parse RSS feed from a source.

        Args:
            source: One of 'fed', 'sec', 'treasury', 'reuters', 'coindesk'

        Returns:
            List of parsed entries
        """
        if source not in self.feeds:
            print(f"Unknown news source: {source}")
            return []

        # Check cache
        cache_key = f"feed_{source}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            age = (datetime.now() - cached_time).seconds
            if age < self.cache_ttl:
                return cached_data

        try:
            feed_url = self.feeds[source]
            feed = feedparser.parse(feed_url)

            entries = []
            for entry in feed.entries[:20]:  # Limit to 20 most recent
                entries.append({
                    'source': source,
                    'title': entry.get('title', ''),
                    'summary': entry.get('summary', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'published_parsed': entry.get('published_parsed'),
                    'fetched_at': datetime.now().isoformat()
                })

            self.cache[cache_key] = (datetime.now(), entries)
            return entries

        except Exception as e:
            print(f"Failed to fetch {source} feed: {e}")
            return []

    def get_recent(self, sources: List[str], minutes: int = 5) -> List[Dict]:
        """
        Get news from the last N minutes.

        Args:
            sources: List of sources to check
            minutes: How far back to look (default 5 minutes)

        Returns:
            List of recent events matching criteria
        """
        cutoff = datetime.now() - timedelta(minutes=minutes)
        recent_events = []

        for source in sources:
            entries = self.fetch_feed(source)

            for entry in entries:
                # Parse published time
                pub_time = None
                if entry.get('published_parsed'):
                    pub_time = datetime(*entry['published_parsed'][:6])

                # If within time window, add to results
                if pub_time and pub_time > cutoff:
                    recent_events.append(entry)

        return recent_events

    def detect_high_impact(self, sources: List[str], minutes: int = 5) -> List[Dict]:
        """
        Detect high-impact events based on keywords.

        Args:
            sources: Sources to monitor
            minutes: Lookback period

        Returns:
            List of high-impact events with impact score
        """
        recent = self.get_recent(sources, minutes)
        high_impact = []

        for event in recent:
            source = event['source']
            title = event['title'].lower()
            summary = event.get('summary', '').lower()
            text = f"{title} {summary}"

            # Calculate impact score based on keyword matches
            impact_score = 0
            matched_keywords = []

            # Check source-specific keywords
            if source in self.high_impact_keywords:
                for keyword in self.high_impact_keywords[source]:
                    if keyword.lower() in text:
                        impact_score += 1
                        matched_keywords.append(keyword)

            # Check crypto keywords for all sources
            for keyword in self.high_impact_keywords['crypto']:
                if keyword.lower() in text:
                    impact_score += 0.5
                    matched_keywords.append(keyword)

            if impact_score > 0:
                event['impact_score'] = impact_score
                event['matched_keywords'] = list(set(matched_keywords))
                high_impact.append(event)

        # Sort by impact score
        high_impact.sort(key=lambda x: x['impact_score'], reverse=True)
        return high_impact

    def extract_sentiment(self, text: str) -> str:
        """
        Simple sentiment extraction based on keyword patterns.

        Returns: 'bullish', 'bearish', or 'neutral'
        """
        text = text.lower()

        bullish_words = ['approve', 'growth', 'positive', 'gains', 'rally', 'surge', 'dovish']
        bearish_words = ['reject', 'decline', 'negative', 'falls', 'crash', 'hawkish', 'hike']

        bullish_count = sum(1 for word in bullish_words if word in text)
        bearish_count = sum(1 for word in bearish_words if word in text)

        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        else:
            return 'neutral'


class EventDataFeed:
    """
    Main interface for event/news data.
    Provides agent-friendly event stream.
    """

    def __init__(self, use_mock=False):
        self.news = NewsAdapter()
        self.use_mock = use_mock

        # Mock events for testing
        self.mock_events = [
            {
                'source': 'fed',
                'title': 'Fed signals dovish stance in surprise statement',
                'summary': 'Federal Reserve indicates potential rate pause due to cooling inflation',
                'impact_score': 3.0,
                'sentiment': 'bullish',
                'matched_keywords': ['rate decision', 'inflation'],
                'detected_at': datetime.now().isoformat()
            },
            {
                'source': 'sec',
                'title': 'SEC approves spot Bitcoin ETF applications',
                'summary': 'Securities and Exchange Commission greenlights major crypto ETF products',
                'impact_score': 4.0,
                'sentiment': 'bullish',
                'matched_keywords': ['bitcoin', 'etf'],
                'detected_at': datetime.now().isoformat()
            }
        ]

    def get_events(self, sources: List[str] = None, minutes: int = 5) -> Dict:
        """
        Get recent high-impact events.

        Args:
            sources: List of sources to monitor (default: all)
            minutes: Lookback period

        Returns:
            Dict of event data for agent consumption
        """
        if self.use_mock:
            return {
                'events': self.mock_events,
                'count': len(self.mock_events),
                'highest_impact': max([e['impact_score'] for e in self.mock_events]),
                'updated_at': datetime.now().isoformat()
            }

        sources = sources or ['fed', 'sec', 'treasury', 'coindesk']
        events = self.news.detect_high_impact(sources, minutes)

        # Add sentiment to each event
        for event in events:
            text = f"{event['title']} {event.get('summary', '')}"
            event['sentiment'] = self.news.extract_sentiment(text)

        return {
            'events': events,
            'count': len(events),
            'highest_impact': max([e['impact_score'] for e in events]) if events else 0,
            'sources': sources,
            'updated_at': datetime.now().isoformat()
        }

    def add_events_to_market_data(self, market_data: Dict, sources: List[str] = None) -> Dict:
        """
        Enrich market data with event stream.
        This is the key integration point for agents.
        """
        enriched = market_data.copy()
        enriched['news_events'] = self.get_events(sources)
        return enriched

    def get_latest_by_source(self, source: str) -> Optional[Dict]:
        """Get the most recent event from a specific source."""
        events = self.get_events([source], minutes=60)  # Look back 1 hour
        if events['events']:
            return events['events'][0]
        return None
