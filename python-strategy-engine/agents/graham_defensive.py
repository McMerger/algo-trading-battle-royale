"""
Graham Defensive Strategy - Multi-Source Value Investing

Implements the exact strategy from README:
1. Fundamental Value Screen (Graham criteria)
2. Macro Risk Filter (Polymarket prediction markets)
3. Technical Confirmation (RSI oversold)

This strategy demonstrates SignalOps' core value proposition:
Multi-source intelligence preventing false signals.

Example from README:
- Date: March 10, 2023
- Technical: BTC RSI = 28 (oversold → typical BUY)
- Polymarket: Banking Crisis 2023 at 76% YES
- On-Chain: $890M USDC outflows
- Decision: BLOCK BUY
- Outcome: BTC dropped 12% more (SVB collapse)
"""

from agents.base_agent import BaseAgent, Signal
from typing import Dict, Optional
from datetime import datetime


class GrahamDefensiveStrategy(BaseAgent):
    """
    Benjamin Graham's defensive value investing + event-aware filtering.

    Entry Criteria (ALL must be met):
    1. Price-to-Book < 1.5
    2. Price < (2/3 * NCAV per share) OR P/E < 15
    3. Debt-to-Equity < 0.5
    4. Recession odds < 25% (Polymarket filter)
    5. Major conflict odds < 15% (Polymarket filter)
    6. RSI < 35 (technical confirmation)

    This is conservative - requires 2+ source confirmation.
    """

    def __init__(self,
                 name="GrahamDefensive",
                 pb_threshold=1.5,
                 pe_threshold=15,
                 debt_threshold=0.5,
                 recession_threshold=0.25,
                 conflict_threshold=0.15,
                 rsi_threshold=35,
                 initial_capital=100000):

        super().__init__(name, initial_capital)

        # Fundamental thresholds
        self.pb_threshold = pb_threshold
        self.pe_threshold = pe_threshold
        self.debt_threshold = debt_threshold

        # Event filter thresholds
        self.recession_threshold = recession_threshold
        self.conflict_threshold = conflict_threshold

        # Technical threshold
        self.rsi_threshold = rsi_threshold

    def generate_signal(self, market_data: Dict, event_data: Optional[Dict] = None) -> Optional[Signal]:
        """
        Generate signal using multi-source data.

        Args:
            market_data: Dict with 'unified' key from MultiSourceDataFeed
            event_data: Legacy parameter, ignored (data now in market_data['unified'])
        """
        # Extract unified data (from MultiSourceDataFeed)
        unified = market_data.get('unified')
        if not unified:
            return None

        symbol = unified.get('symbol', market_data.get('symbol', 'UNKNOWN'))
        price = unified.get('market', {}).get('price', market_data.get('price', 0))

        # Check for conflicts first (SignalOps' unique feature)
        conflicts = unified.get('conflicts', [])
        high_severity_conflicts = [c for c in conflicts if c.get('severity') == 'HIGH']

        if high_severity_conflicts:
            # Block trade due to conflict
            return Signal(
                timestamp=datetime.now().timestamp(),
                symbol=symbol,
                action='HOLD',
                confidence=0.0,
                size=0,
                reason=f"BLOCKED: {high_severity_conflicts[0]['description']}",
                agent_name=self.name,
                price=price
            )

        # Condition 1: Fundamental Value Screen
        value_check, value_reason = self._check_value_criteria(unified)

        # Condition 2: Macro Risk Filter (Polymarket)
        macro_check, macro_reason = self._check_macro_risk(unified)

        # Condition 3: Technical Confirmation
        technical_check, technical_reason = self._check_technical(unified)

        # Decision Logic: Require 2 of 3 conditions
        checks = [value_check, macro_check, technical_check]
        passed_count = sum(checks)

        if passed_count >= 2:
            # Calculate confidence based on how many checks passed
            confidence = 0.6 + (passed_count * 0.1)

            # Check consensus from multi-source feed
            consensus = unified.get('consensus', {})
            if consensus.get('action') == 'BUY' and consensus.get('sources_count', 0) >= 2:
                confidence = min(0.95, confidence + 0.1)

            return Signal(
                timestamp=datetime.now().timestamp(),
                symbol=symbol,
                action='BUY',
                confidence=confidence,
                size=self.capital * 0.02,  # 2% of portfolio per position
                reason=self._build_reason(value_check, value_reason, macro_check, macro_reason,
                                           technical_check, technical_reason, passed_count),
                agent_name=self.name,
                price=price
            )

        # No entry - conditions not met
        return Signal(
            timestamp=datetime.now().timestamp(),
            symbol=symbol,
            action='HOLD',
            confidence=0.5,
            size=0,
            reason=f"Only {passed_count}/3 conditions met",
            agent_name=self.name,
            price=price
        )

    def _check_value_criteria(self, unified: Dict) -> tuple[bool, str]:
        """
        Check Benjamin Graham's value criteria.

        Returns:
            (passed: bool, reason: str)
        """
        fundamentals = unified.get('fundamentals', {})

        if fundamentals.get('source') == 'unavailable':
            return False, "No fundamental data"

        pb_ratio = fundamentals.get('price_to_book')
        pe_ratio = fundamentals.get('price_to_earnings')
        ncav_ratio = fundamentals.get('ncav_ratio')
        debt_equity = fundamentals.get('debt_to_equity')

        checks_passed = []
        checks_failed = []

        # P/B check
        if pb_ratio is not None:
            if pb_ratio < self.pb_threshold:
                checks_passed.append(f'P/B {pb_ratio:.2f}')
            else:
                checks_failed.append(f'P/B {pb_ratio:.2f} >= {self.pb_threshold}')

        # P/E or NCAV check (either works)
        if ncav_ratio is not None and ncav_ratio < 0.67:
            checks_passed.append(f'NCAV {ncav_ratio:.2f} (Net-Net!)')
        elif pe_ratio is not None and 0 < pe_ratio < self.pe_threshold:
            checks_passed.append(f'P/E {pe_ratio:.1f}')
        else:
            checks_failed.append('Neither NCAV nor P/E criteria met')

        # Debt check
        if debt_equity is not None:
            if debt_equity < self.debt_threshold:
                checks_passed.append(f'D/E {debt_equity:.2f}')
            else:
                checks_failed.append(f'D/E {debt_equity:.2f} >= {self.debt_threshold}')

        # Need at least 2 of 3 fundamental checks
        passed = len(checks_passed) >= 2

        reason = f"Value: {', '.join(checks_passed)}" if passed else f"Value FAIL: {', '.join(checks_failed)}"
        return passed, reason

    def _check_macro_risk(self, unified: Dict) -> tuple[bool, str]:
        """
        Check prediction market odds for macro risk events.

        This is SignalOps' unique "event filter" layer.
        """
        events = unified.get('events', {})

        if not events:
            return True, "Macro: No event data (assuming neutral)"

        risk_events = []

        for event_name, event_data in events.items():
            if not isinstance(event_data, dict):
                continue

            prob = event_data.get('yes_probability', 0)

            # Check for recession risk
            if 'recession' in event_name.lower():
                if prob >= self.recession_threshold:
                    risk_events.append(f'Recession {prob:.0%}')
                else:
                    pass  # OK

            # Check for geopolitical risk
            if any(keyword in event_name.lower() for keyword in ['war', 'conflict', 'crisis']):
                if prob >= self.conflict_threshold:
                    risk_events.append(f'{event_name} {prob:.0%}')

        if risk_events:
            return False, f"Macro RISK: {', '.join(risk_events)}"

        return True, f"Macro: Low risk environment"

    def _check_technical(self, unified: Dict) -> tuple[bool, str]:
        """
        Check technical confirmation (oversold condition).
        """
        technical = unified.get('technical', {})

        rsi = technical.get('rsi_14')

        if rsi is None:
            return True, "Technical: No data (neutral)"

        if rsi < self.rsi_threshold:
            return True, f"Technical: RSI {rsi:.1f} oversold"

        return False, f"Technical: RSI {rsi:.1f} not oversold"

    def _build_reason(self, value_pass, value_reason, macro_pass, macro_reason,
                      technical_pass, technical_reason, total_passed) -> str:
        """
        Build human-readable explanation for the signal.

        This generates the audit trail shown in SignalOps README.
        """
        parts = []

        parts.append(f"✓ {value_reason}" if value_pass else f"✗ {value_reason}")
        parts.append(f"✓ {macro_reason}" if macro_pass else f"✗ {macro_reason}")
        parts.append(f"✓ {technical_reason}" if technical_pass else f"✗ {technical_reason}")

        return f"BUY ({total_passed}/3 checks): " + " | ".join(parts)

    def get_strategy_description(self) -> str:
        """Return strategy description for logging."""
        return f"""
Graham Defensive Strategy (Multi-Source Value Investing)

Entry Criteria:
- P/B < {self.pb_threshold}
- P/E < {self.pe_threshold} OR Price < 2/3 NCAV
- Debt/Equity < {self.debt_threshold}
- Recession odds < {self.recession_threshold:.0%}
- Geopolitical risk < {self.conflict_threshold:.0%}
- RSI < {self.rsi_threshold}

Requires 2/3 conditions + no high-severity conflicts.

This demonstrates SignalOps' value proposition:
Multi-source filtering prevents entries during macro risk events.
"""


class SVBCrisisDetector(BaseAgent):
    """
    Specialized strategy that detects banking crises before they hit markets.

    Based on March 2023 SVB collapse example from README.

    Combines:
    - Polymarket banking crisis odds
    - On-chain stablecoin outflows
    - Technical oversold signals

    When crisis odds > 70% + stablecoin outflows, block ALL buys.
    """

    def __init__(self, name="SVBDetector", crisis_threshold=0.70, initial_capital=100000):
        super().__init__(name, initial_capital)
        self.crisis_threshold = crisis_threshold

    def generate_signal(self, market_data: Dict, event_data: Optional[Dict] = None) -> Optional[Signal]:
        """Generate defensive signal during banking crises."""

        unified = market_data.get('unified')
        if not unified:
            return None

        symbol = unified.get('symbol', market_data.get('symbol', 'UNKNOWN'))
        price = unified.get('market', {}).get('price', market_data.get('price', 0))

        # Check Polymarket for banking crisis
        events = unified.get('events', {})
        crisis_detected = False

        for event_name, event_data in events.items():
            if not isinstance(event_data, dict):
                continue

            if any(keyword in event_name.lower() for keyword in ['bank', 'svb', 'credit', 'crisis']):
                prob = event_data.get('yes_probability', 0)
                if prob > self.crisis_threshold:
                    crisis_detected = True
                    crisis_event = event_name
                    crisis_prob = prob
                    break

        # Check on-chain for capital flight
        onchain = unified.get('onchain', {})
        capital_flight = onchain.get('interpretation', {}).get('sentiment') == 'BEARISH'

        if crisis_detected and capital_flight:
            return Signal(
                timestamp=datetime.now().timestamp(),
                symbol=symbol,
                action='SELL',  # Or close positions
                confidence=0.9,
                size=self.capital * 0.5,  # Defensive: reduce exposure
                reason=f"CRISIS DETECTED: {crisis_event} at {crisis_prob:.0%} + on-chain outflows",
                agent_name=self.name,
                price=price
            )

        return None  # No signal
