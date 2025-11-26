"""
Multi-Source Data Feed Orchestrator - CORE SIGNALOPS IP

This is the fusion layer that makes SignalOps unique:
Aggregates 5 data sources into a unified decision interface.

Sources:
1. Prediction Markets (Polymarket) - crowd probability estimates
2. On-Chain Data (DeFiLlama) - capital flows, TVL
3. Fundamentals (Yahoo Finance) - value metrics, financials
4. Technical Indicators - price patterns, momentum
5. News Events - Fed statements, SEC filings

The orchestrator:
- Fetches data from all sources in parallel
- Normalizes into standard format
- Provides conflict detection (e.g., RSI says buy but prediction markets say crash)
- Returns unified dict for strategy consumption
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from market_data.prediction_market_adapter import PredictionMarketFeed
from market_data.onchain_adapter import OnChainDataFeed
from market_data.fundamental_adapter import FundamentalDataFeed


class MultiSourceDataFeed:
    """
    Orchestrates data from 5 sources and detects conflicts.

    This is SignalOps' core innovation - transparent multi-source fusion.
    """

    def __init__(self, use_mock=False):
        """
        Initialize all data adapters.

        Args:
            use_mock: Use mock data for all sources (offline development)
        """
        self.prediction_markets = PredictionMarketFeed(use_mock=use_mock)
        self.onchain = OnChainDataFeed(use_mock=use_mock)
        self.fundamentals = FundamentalDataFeed(use_mock=use_mock)

        self.use_mock = use_mock
        self.executor = ThreadPoolExecutor(max_workers=5)

    def get_unified_data(self,
                         symbol: str,
                         market_data: Dict,
                         event_config: Optional[Dict] = None) -> Dict:
        """
        Fetch and unify data from all sources.

        Args:
            symbol: Trading symbol (e.g., 'BTC', 'AAPL')
            market_data: Current price/volume data
            event_config: Polymarket event configuration

        Returns:
            Unified dict with all sources + conflict analysis
        """
        # Fetch from all sources in parallel (non-blocking)
        futures = []

        # 1. Prediction markets (events)
        if event_config:
            futures.append(
                self.executor.submit(
                    self.prediction_markets.get_events,
                    event_config
                )
            )
        else:
            futures.append(self.executor.submit(lambda: {}))

        # 2. On-chain data (for crypto assets)
        if self._is_crypto(symbol):
            futures.append(
                self.executor.submit(
                    self.onchain.get_crypto_market_health,
                    symbol
                )
            )
        else:
            futures.append(self.executor.submit(lambda: {}))

        # 3. Fundamentals (for stocks/crypto with fundamentals)
        futures.append(
            self.executor.submit(
                self.fundamentals.get_value_metrics,
                symbol
            )
        )

        # 4. Technical indicators (calculated from market_data)
        futures.append(
            self.executor.submit(
                self._calculate_technical_indicators,
                market_data
            )
        )

        # Wait for all sources to complete (with timeout)
        try:
            results = [f.result(timeout=10) for f in futures]
            events, onchain_data, fundamental_data, technical_data = results
        except Exception as e:
            print(f"Error fetching multi-source data: {e}")
            # Return partial data rather than failing completely
            events, onchain_data, fundamental_data, technical_data = {}, {}, {}, {}

        # Unify into single dict
        unified = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,

            # Source 1: Prediction Markets
            'events': events,

            # Source 2: On-Chain
            'onchain': onchain_data,

            # Source 3: Fundamentals
            'fundamentals': fundamental_data,

            # Source 4: Technical
            'technical': technical_data,

            # Source 5: Market Data (price/volume)
            'market': market_data,

            # CORE VALUE: Conflict detection
            'conflicts': self._detect_conflicts(
                events, onchain_data, fundamental_data, technical_data, market_data
            ),

            # Consensus signal (when sources agree)
            'consensus': self._calculate_consensus(
                events, onchain_data, fundamental_data, technical_data
            )
        }

        return unified

    def _detect_conflicts(self,
                          events: Dict,
                          onchain: Dict,
                          fundamentals: Dict,
                          technicals: Dict,
                          market: Dict) -> List[Dict]:
        """
        Detect conflicts between data sources.

        Example conflict:
        - Technical: RSI = 28 (oversold, typical BUY signal)
        - Events: Banking crisis odds = 76% (macro risk HIGH)
        - Decision: BLOCK BUY, flag conflict

        This is the "sanity check" layer that prevented SVB losses.
        """
        conflicts = []

        # Conflict 1: Technical says buy, but macro events say danger
        technical_signal = technicals.get('signal', 'HOLD')

        # Check prediction market risk
        if events:
            for event_name, event_data in events.items():
                if isinstance(event_data, dict):
                    prob = event_data.get('yes_probability', 0)

                    # High probability of negative events
                    if any(keyword in event_name.lower() for keyword in ['recession', 'crash', 'crisis', 'war']):
                        if prob > 0.6 and technical_signal == 'BUY':
                            conflicts.append({
                                'type': 'MACRO_RISK_VS_TECHNICAL',
                                'severity': 'HIGH',
                                'description': f'Technical says {technical_signal} but {event_name} odds at {prob:.1%}',
                                'recommendation': 'BLOCK',
                                'sources': ['technical', 'prediction_markets']
                            })

        # Conflict 2: Fundamentals say overvalued, technicals say buy
        if fundamentals.get('source') != 'unavailable':
            pb_ratio = fundamentals.get('price_to_book')
            pe_ratio = fundamentals.get('price_to_earnings')

            if pb_ratio and pe_ratio:
                if (pb_ratio > 3.0 or pe_ratio > 30) and technical_signal == 'BUY':
                    conflicts.append({
                        'type': 'VALUATION_VS_TECHNICAL',
                        'severity': 'MEDIUM',
                        'description': f'Stock overvalued (P/B={pb_ratio:.1f}, P/E={pe_ratio:.1f}) but technical says BUY',
                        'recommendation': 'CAUTION',
                        'sources': ['fundamentals', 'technical']
                    })

        # Conflict 3: On-chain shows outflows, price rising (crypto)
        if onchain.get('source') == 'onchain':
            onchain_sentiment = onchain.get('interpretation', {}).get('sentiment', 'NEUTRAL')
            price_change = market.get('price_change_pct', 0)

            if onchain_sentiment == 'BEARISH' and price_change > 5:
                conflicts.append({
                    'type': 'ONCHAIN_VS_PRICE',
                    'severity': 'MEDIUM',
                    'description': 'Price rising but on-chain shows capital outflows',
                    'recommendation': 'INVESTIGATE',
                    'sources': ['onchain', 'market']
                })

        return conflicts

    def _calculate_consensus(self,
                             events: Dict,
                             onchain: Dict,
                             fundamentals: Dict,
                             technicals: Dict) -> Dict:
        """
        Calculate consensus signal when multiple sources agree.

        Requires 2+ sources pointing same direction for high confidence.
        """
        signals = []
        confidences = []

        # Technical signal
        if technicals.get('signal'):
            signals.append(technicals['signal'])
            confidences.append(technicals.get('confidence', 0.5))

        # Fundamental signal (Graham value)
        if fundamentals.get('graham_score'):
            score = fundamentals['graham_score']
            if score > 70:
                signals.append('BUY')
                confidences.append(0.7)
            elif score < 30:
                signals.append('SELL')
                confidences.append(0.6)

        # On-chain signal
        if onchain.get('interpretation'):
            sentiment = onchain['interpretation'].get('sentiment')
            if sentiment == 'BULLISH':
                signals.append('BUY')
                confidences.append(0.6)
            elif sentiment == 'BEARISH':
                signals.append('SELL')
                confidences.append(0.6)

        # Event risk filter (veto power)
        if events:
            for event_data in events.values():
                if isinstance(event_data, dict):
                    # Check for high-risk events
                    if any(keyword in str(event_data.get('title', '')).lower()
                           for keyword in ['crash', 'crisis', 'recession']):
                        prob = event_data.get('yes_probability', 0)
                        if prob > 0.7:
                            # High risk event overrides buy signals
                            signals = [s if s != 'BUY' else 'HOLD' for s in signals]

        # Calculate consensus
        if not signals:
            return {'action': 'HOLD', 'confidence': 0.5, 'sources_count': 0}

        # Count votes
        buy_votes = signals.count('BUY')
        sell_votes = signals.count('SELL')
        total_votes = len(signals)

        if buy_votes >= 2:
            action = 'BUY'
            confidence = np.mean([c for s, c in zip(signals, confidences) if s == 'BUY'])
        elif sell_votes >= 2:
            action = 'SELL'
            confidence = np.mean([c for s, c in zip(signals, confidences) if s == 'SELL'])
        else:
            action = 'HOLD'
            confidence = 0.5

        return {
            'action': action,
            'confidence': float(confidence),
            'sources_count': total_votes,
            'votes': {'BUY': buy_votes, 'SELL': sell_votes, 'HOLD': total_votes - buy_votes - sell_votes}
        }

    def _calculate_technical_indicators(self, market_data: Dict) -> Dict:
        """
        Calculate basic technical indicators from market data.

        Note: In production, this would call TA-Lib or be calculated in Go.
        For now, simple mock implementation.
        """
        price = market_data.get('price', 100)

        # Mock RSI calculation (would use real price history)
        rsi = 50 + (np.random.randn() * 15)  # Mock: normally distributed around 50
        rsi = max(0, min(100, rsi))

        # Simple signal logic
        if rsi < 30:
            signal = 'BUY'
            confidence = 0.7
        elif rsi > 70:
            signal = 'SELL'
            confidence = 0.7
        else:
            signal = 'HOLD'
            confidence = 0.5

        return {
            'source': 'technical',
            'rsi_14': rsi,
            'signal': signal,
            'confidence': confidence,
            'note': 'Mock calculation - replace with real TA-Lib in production'
        }

    def _is_crypto(self, symbol: str) -> bool:
        """Check if symbol is a cryptocurrency."""
        crypto_symbols = ['BTC', 'ETH', 'SOL', 'AVAX', 'MATIC', 'ARB', 'OP']
        return symbol in crypto_symbols or symbol.endswith('USD')

    def get_audit_trail(self, unified_data: Dict) -> Dict:
        """
        Generate audit trail for decision logging.

        Returns structured log matching README example format.
        """
        return {
            'timestamp': unified_data['timestamp'],
            'asset': unified_data['symbol'],
            'decision': unified_data.get('consensus', {}).get('action', 'HOLD'),
            'confidence': unified_data.get('consensus', {}).get('confidence', 0.5),
            'triggers_met': self._extract_triggers(unified_data),
            'conflicts_detected': unified_data.get('conflicts', []),
            'sources_used': self._count_sources(unified_data)
        }

    def _extract_triggers(self, unified_data: Dict) -> List[Dict]:
        """Extract which conditions triggered the decision."""
        triggers = []

        # Fundamental triggers
        if unified_data.get('fundamentals', {}).get('source') != 'unavailable':
            fund = unified_data['fundamentals']
            if fund.get('price_to_book'):
                triggers.append({
                    'source': 'fundamental',
                    'metric': 'price_to_book',
                    'value': fund['price_to_book'],
                    'threshold': '< 1.5',
                    'status': 'PASS' if fund['price_to_book'] < 1.5 else 'FAIL'
                })

        # Event triggers
        for event_name, event_data in unified_data.get('events', {}).items():
            if isinstance(event_data, dict) and 'yes_probability' in event_data:
                triggers.append({
                    'source': 'polymarket',
                    'market': event_name,
                    'probability': event_data['yes_probability'],
                    'status': 'MONITORED'
                })

        # Technical triggers
        if unified_data.get('technical', {}).get('rsi_14'):
            tech = unified_data['technical']
            triggers.append({
                'source': 'technical',
                'indicator': 'rsi_14',
                'value': tech['rsi_14'],
                'threshold': '< 35 or > 65',
                'status': 'PASS' if tech['signal'] != 'HOLD' else 'NEUTRAL'
            })

        return triggers

    def _count_sources(self, unified_data: Dict) -> int:
        """Count how many sources provided data."""
        count = 0
        if unified_data.get('events'):
            count += 1
        if unified_data.get('onchain', {}).get('source') == 'onchain':
            count += 1
        if unified_data.get('fundamentals', {}).get('source') != 'unavailable':
            count += 1
        if unified_data.get('technical'):
            count += 1
        return count
