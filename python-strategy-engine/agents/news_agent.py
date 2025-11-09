"""
News-driven agent that reacts to breaking events.

Strategy:
- Monitor Fed, SEC, Treasury announcements
- React to high-impact news (<60s latency)
- Use sentiment and keyword matching
- Higher impact score = higher confidence
"""

from typing import Dict, Optional
from agents.base_agent import BaseAgent, Signal


class NewsAgent(BaseAgent):
    """
    Trades on breaking news and announcements.

    Logic:
    - High-impact bullish news = BUY
    - High-impact bearish news = SELL
    - Confidence scales with impact score
    - Fed news weighted higher than general news
    """

    def __init__(self, name="NewsAgent",
                 impact_threshold=2.0,
                 fed_multiplier=1.5):
        super().__init__(name)

        self.impact_threshold = impact_threshold
        self.fed_multiplier = fed_multiplier

        # Track seen events to avoid duplicate trading
        self.seen_events = set()

    def generate_signal(self, market_data, event_data=None):
        """
        Generate signal based on recent news events.

        Expected event_data format:
        {
            'news_events': {
                'events': [
                    {
                        'source': 'fed',
                        'title': 'Fed signals dovish stance',
                        'impact_score': 3.0,
                        'sentiment': 'bullish',
                        'matched_keywords': ['rate decision', 'inflation']
                    }
                ],
                'count': 1,
                'highest_impact': 3.0
            }
        }
        """
        if not event_data or 'news_events' not in event_data:
            return None

        news = event_data['news_events']
        events = news.get('events', [])

        if not events:
            return None

        # Find the highest impact event we haven't seen
        best_event = None
        best_score = 0

        for event in events:
            # Create unique identifier
            event_id = f"{event['source']}_{event['title'][:50]}"

            if event_id in self.seen_events:
                continue

            impact = event.get('impact_score', 0)

            # Boost Fed events
            if event.get('source') == 'fed':
                impact *= self.fed_multiplier

            if impact > best_score and impact >= self.impact_threshold:
                best_score = impact
                best_event = event
                self.seen_events.add(event_id)

        if not best_event:
            return None

        # Determine action based on sentiment
        sentiment = best_event.get('sentiment', 'neutral')
        source = best_event.get('source', 'unknown')
        title = best_event.get('title', '')
        keywords = ', '.join(best_event.get('matched_keywords', []))

        if sentiment == 'bullish':
            action = 'BUY'
            confidence = min(0.88, 0.6 + (best_score / 10))
        elif sentiment == 'bearish':
            action = 'SELL'
            confidence = min(0.88, 0.6 + (best_score / 10))
        else:
            # Neutral sentiment - use source-specific logic
            if source == 'fed':
                # Fed news is typically risk-off
                action = 'SELL'
                confidence = 0.65
            elif source == 'sec' and 'etf' in title.lower():
                # ETF news usually bullish
                action = 'BUY'
                confidence = 0.7
            else:
                return None

        reason = (f"{source.upper()} event (impact: {best_event['impact_score']:.1f}): "
                 f"\"{title[:80]}...\" | "
                 f"Sentiment: {sentiment} | Keywords: {keywords}")

        return Signal(
            timestamp=market_data.get('timestamp', 0),
            symbol=market_data.get('symbol', 'BTC'),
            action=action,
            confidence=confidence,
            size=100,
            reason=reason,
            agent_name=self.name,
            price=market_data.get('price', 0)
        )


class FedNewsAgent(BaseAgent):
    """
    Specialized agent focused purely on Federal Reserve announcements.
    More aggressive than general news agent.
    """

    def __init__(self, name="FedNewsAgent"):
        super().__init__(name)
        self.seen_fed_events = set()

    def generate_signal(self, market_data, event_data=None):
        """
        React immediately to any Fed announcement.
        """
        if not event_data or 'news_events' not in event_data:
            return None

        news = event_data['news_events']
        events = news.get('events', [])

        # Find Fed events only
        for event in events:
            if event.get('source') != 'fed':
                continue

            event_id = f"fed_{event['title'][:50]}"
            if event_id in self.seen_fed_events:
                continue

            self.seen_fed_events.add(event_id)

            title = event.get('title', '').lower()
            sentiment = event.get('sentiment', 'neutral')

            # Fed-specific keyword logic
            if 'hike' in title or 'hawkish' in title:
                action = 'SELL'
                confidence = 0.82
                reason = f"Fed hawkish signal: \"{event['title']}\""
            elif 'cut' in title or 'dovish' in title:
                action = 'BUY'
                confidence = 0.82
                reason = f"Fed dovish signal: \"{event['title']}\""
            elif 'pause' in title:
                action = 'BUY'
                confidence = 0.72
                reason = f"Fed pause signal: \"{event['title']}\""
            elif sentiment == 'bullish':
                action = 'BUY'
                confidence = 0.75
                reason = f"Fed bullish announcement: \"{event['title']}\""
            elif sentiment == 'bearish':
                action = 'SELL'
                confidence = 0.75
                reason = f"Fed bearish announcement: \"{event['title']}\""
            else:
                continue

            return Signal(
                timestamp=market_data.get('timestamp', 0),
                symbol=market_data.get('symbol', 'BTC'),
                action=action,
                confidence=confidence,
                size=100,
                reason=reason,
                agent_name=self.name,
                price=market_data.get('price', 0)
            )

        return None


class SECAgent(BaseAgent):
    """
    Specialized agent for SEC announcements (crypto-focused).
    """

    def __init__(self, name="SECAgent"):
        super().__init__(name)
        self.seen_sec_events = set()

    def generate_signal(self, market_data, event_data=None):
        """
        React to SEC crypto announcements.
        """
        if not event_data or 'news_events' not in event_data:
            return None

        news = event_data['news_events']
        events = news.get('events', [])

        for event in events:
            if event.get('source') != 'sec':
                continue

            event_id = f"sec_{event['title'][:50]}"
            if event_id in self.seen_sec_events:
                continue

            self.seen_sec_events.add(event_id)

            title = event.get('title', '').lower()
            keywords = event.get('matched_keywords', [])

            # ETF approval = mega bullish
            if 'etf' in keywords and ('approve' in title or 'approval' in title):
                return Signal(
                    timestamp=market_data.get('timestamp', 0),
                    symbol=market_data.get('symbol', 'BTC'),
                    action='BUY',
                    confidence=0.92,
                    size=100,
                    reason=f"SEC ETF APPROVAL: \"{event['title']}\"",
                    agent_name=self.name,
                    price=market_data.get('price', 0)
                )

            # ETF rejection = bearish
            elif 'etf' in keywords and ('reject' in title or 'denial' in title):
                return Signal(
                    timestamp=market_data.get('timestamp', 0),
                    symbol=market_data.get('symbol', 'BTC'),
                    action='SELL',
                    confidence=0.85,
                    size=100,
                    reason=f"SEC ETF REJECTION: \"{event['title']}\"",
                    agent_name=self.name,
                    price=market_data.get('price', 0)
                )

            # Enforcement action = bearish
            elif 'enforcement' in keywords or 'fraud' in keywords:
                return Signal(
                    timestamp=market_data.get('timestamp', 0),
                    symbol=market_data.get('symbol', 'BTC'),
                    action='SELL',
                    confidence=0.73,
                    size=100,
                    reason=f"SEC enforcement action: \"{event['title']}\"",
                    agent_name=self.name,
                    price=market_data.get('price', 0)
                )

        return None
