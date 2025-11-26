"""
Fundamental data adapter using Yahoo Finance and financial statement analysis.

Provides Graham value investing metrics:
- Price-to-Book (P/B) ratio
- Net Current Asset Value (NCAV)
- Price-to-Earnings (P/E) ratio
- Debt-to-Equity
- Free Cash Flow

These metrics identify undervalued assets for value-based strategies.
"""

import requests
from typing import Dict, Optional
from datetime import datetime
import json


class YahooFinanceAdapter:
    """
    Yahoo Finance data adapter for fundamental metrics.

    Uses Yahoo Finance v8 API (unofficial but widely used).
    No API key required for basic quotes and statistics.
    """

    def __init__(self):
        self.base_url = "https://query2.finance.yahoo.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour (fundamentals don't change frequently)

    def get_fundamentals(self, symbol: str) -> Optional[Dict]:
        """
        Get comprehensive fundamental data for a symbol.

        Args:
            symbol: Stock ticker (e.g., 'AAPL', 'MSFT')

        Returns:
            Dict with P/B, P/E, NCAV, debt ratios, etc.
        """
        cache_key = f"fundamentals_{symbol}"
        if self._check_cache(cache_key):
            return self.cache[cache_key]

        try:
            # Get quote summary with key statistics
            url = f"{self.base_url}/v10/finance/quoteSummary/{symbol}"
            params = {
                'modules': 'defaultKeyStatistics,financialData,balanceSheetHistory,incomeStatementHistory'
            }

            resp = self.session.get(url, params=params, timeout=10)

            if not resp.ok:
                print(f"Yahoo Finance error {resp.status_code} for {symbol}")
                return None

            data = resp.json()
            result = data.get('quoteSummary', {}).get('result', [])

            if not result:
                return None

            stats = result[0]

            # Extract key metrics
            key_stats = stats.get('defaultKeyStatistics', {})
            financial_data = stats.get('financialData', {})
            balance_sheet = stats.get('balanceSheetHistory', {}).get('balanceSheetStatements', [{}])[0]

            # Get current price from financial data
            current_price = self._extract_value(financial_data.get('currentPrice'))

            # Calculate NCAV (Net Current Asset Value)
            ncav_data = self._calculate_ncav(balance_sheet, key_stats)

            fundamentals = {
                'source': 'yahoo_finance',
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),

                # Valuation ratios
                'price': current_price,
                'market_cap': self._extract_value(key_stats.get('marketCap')),
                'enterprise_value': self._extract_value(key_stats.get('enterpriseValue')),

                # Graham metrics
                'price_to_book': self._extract_value(key_stats.get('priceToBook')),
                'price_to_earnings': self._extract_value(key_stats.get('trailingPE')),
                'forward_pe': self._extract_value(key_stats.get('forwardPE')),

                # NCAV (Graham's Net-Net strategy)
                'ncav_per_share': ncav_data.get('ncav_per_share'),
                'ncav_ratio': ncav_data.get('ncav_ratio'),  # Price / NCAV

                # Profitability
                'profit_margin': self._extract_value(financial_data.get('profitMargins')),
                'operating_margin': self._extract_value(financial_data.get('operatingMargins')),
                'return_on_equity': self._extract_value(financial_data.get('returnOnEquity')),

                # Financial health
                'debt_to_equity': self._extract_value(financial_data.get('debtToEquity')),
                'current_ratio': self._extract_value(financial_data.get('currentRatio')),
                'quick_ratio': self._extract_value(financial_data.get('quickRatio')),

                # Cash flow
                'free_cash_flow': self._extract_value(financial_data.get('freeCashflow')),
                'operating_cash_flow': self._extract_value(financial_data.get('operatingCashflow')),

                # Growth
                'revenue_growth': self._extract_value(financial_data.get('revenueGrowth')),
                'earnings_growth': self._extract_value(financial_data.get('earningsGrowth')),

                # Dividend
                'dividend_yield': self._extract_value(key_stats.get('dividendYield')),

                # Graham value score (custom calculation)
                'graham_score': self._calculate_graham_score(
                    self._extract_value(key_stats.get('priceToBook')),
                    self._extract_value(key_stats.get('trailingPE')),
                    ncav_data.get('ncav_ratio'),
                    self._extract_value(financial_data.get('debtToEquity'))
                )
            }

            self.cache[cache_key] = fundamentals
            return fundamentals

        except Exception as e:
            print(f"Failed to fetch fundamentals for {symbol}: {e}")
            return None

    def _calculate_ncav(self, balance_sheet: Dict, key_stats: Dict) -> Dict:
        """
        Calculate Net Current Asset Value (Graham's Net-Net).

        NCAV = Current Assets - Total Liabilities
        NCAV per share = NCAV / Shares Outstanding

        Graham's rule: Buy when Price < (2/3 * NCAV per share)
        """
        try:
            current_assets = self._extract_value(balance_sheet.get('totalCurrentAssets'))
            total_liabilities = self._extract_value(balance_sheet.get('totalLiab'))
            shares_outstanding = self._extract_value(key_stats.get('sharesOutstanding'))

            if current_assets and total_liabilities and shares_outstanding:
                ncav = current_assets - total_liabilities
                ncav_per_share = ncav / shares_outstanding

                # Get current price for ratio calculation
                current_price = self._extract_value(key_stats.get('currentPrice'))
                ncav_ratio = (current_price / ncav_per_share) if ncav_per_share > 0 else None

                return {
                    'ncav': ncav,
                    'ncav_per_share': ncav_per_share,
                    'ncav_ratio': ncav_ratio,
                    'graham_threshold': ncav_per_share * 0.67  # 2/3 of NCAV
                }

        except Exception:
            pass

        return {'ncav_per_share': None, 'ncav_ratio': None}

    def _calculate_graham_score(self, pb: Optional[float], pe: Optional[float],
                                  ncav_ratio: Optional[float], debt_equity: Optional[float]) -> float:
        """
        Custom Graham value score (0-100).

        Higher score = more attractive for value investing.
        Based on Graham's criteria.
        """
        score = 50.0  # Start neutral

        # P/B ratio (prefer < 1.5)
        if pb is not None:
            if pb < 1.0:
                score += 20
            elif pb < 1.5:
                score += 10
            elif pb > 3.0:
                score -= 10

        # P/E ratio (prefer < 15)
        if pe is not None and pe > 0:
            if pe < 10:
                score += 15
            elif pe < 15:
                score += 10
            elif pe > 25:
                score -= 10

        # NCAV ratio (prefer < 0.67)
        if ncav_ratio is not None:
            if ncav_ratio < 0.67:
                score += 25  # Strong Graham signal
            elif ncav_ratio < 1.0:
                score += 10

        # Debt-to-Equity (prefer < 0.5)
        if debt_equity is not None:
            if debt_equity < 0.3:
                score += 10
            elif debt_equity < 0.5:
                score += 5
            elif debt_equity > 1.0:
                score -= 15

        return max(0, min(100, score))

    def _extract_value(self, data: Optional[Dict]) -> Optional[float]:
        """Extract numerical value from Yahoo Finance's nested structure."""
        if data is None:
            return None

        if isinstance(data, dict):
            raw = data.get('raw')
            if raw is not None:
                return float(raw)

        try:
            return float(data)
        except (TypeError, ValueError):
            return None

    def _check_cache(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self.cache:
            return False

        entry = self.cache[key]
        if 'timestamp' not in entry:
            return False

        age = (datetime.now() - datetime.fromisoformat(entry['timestamp'])).seconds
        return age < self.cache_ttl


class FundamentalDataFeed:
    """
    Unified interface for fundamental data.
    """

    def __init__(self, use_mock=False):
        self.yahoo = YahooFinanceAdapter()
        self.use_mock = use_mock

        # Mock data for testing
        self.mock_data = {
            'source': 'mock',
            'symbol': 'MOCK',
            'price': 150.0,
            'price_to_book': 1.32,
            'price_to_earnings': 18.5,
            'ncav_ratio': 0.85,
            'debt_to_equity': 0.35,
            'graham_score': 72.0
        }

    def get_value_metrics(self, symbol: str) -> Dict:
        """
        Get value investing metrics for a symbol.

        Returns metrics compatible with Graham value strategies.
        """
        if self.use_mock:
            return self.mock_data

        fundamentals = self.yahoo.get_fundamentals(symbol)

        if not fundamentals:
            print(f"No fundamental data available for {symbol}, using fallback")
            return {'source': 'unavailable', 'symbol': symbol}

        return fundamentals

    def is_graham_value(self, symbol: str, strict: bool = True) -> Dict:
        """
        Check if a stock meets Graham's value criteria.

        Strict mode requires:
        - P/B < 1.5
        - P/E < 15 (and positive)
        - Debt-to-Equity < 0.5
        - Price < (2/3 * NCAV per share) - the "Net-Net" rule

        Returns:
            Dict with boolean 'is_value' and explanation
        """
        metrics = self.get_value_metrics(symbol)

        if metrics.get('source') == 'unavailable':
            return {'is_value': False, 'reason': 'No data available'}

        pb = metrics.get('price_to_book')
        pe = metrics.get('price_to_earnings')
        ncav_ratio = metrics.get('ncav_ratio')
        debt_equity = metrics.get('debt_to_equity')

        criteria_met = []
        criteria_failed = []

        # Check each Graham criterion
        if pb is not None:
            if pb < 1.5:
                criteria_met.append(f'P/B {pb:.2f} < 1.5')
            else:
                criteria_failed.append(f'P/B {pb:.2f} >= 1.5')

        if pe is not None and pe > 0:
            if pe < 15:
                criteria_met.append(f'P/E {pe:.2f} < 15')
            else:
                criteria_failed.append(f'P/E {pe:.2f} >= 15')

        if ncav_ratio is not None:
            if ncav_ratio < 0.67:
                criteria_met.append(f'Price/NCAV {ncav_ratio:.2f} < 0.67 (Net-Net!)')
            elif ncav_ratio < 1.0:
                criteria_met.append(f'Price/NCAV {ncav_ratio:.2f} < 1.0')

        if debt_equity is not None:
            if debt_equity < 0.5:
                criteria_met.append(f'D/E {debt_equity:.2f} < 0.5')
            else:
                criteria_failed.append(f'D/E {debt_equity:.2f} >= 0.5')

        if strict:
            is_value = len(criteria_met) >= 3 and len(criteria_failed) == 0
        else:
            is_value = len(criteria_met) >= 2

        return {
            'is_value': is_value,
            'graham_score': metrics.get('graham_score', 50),
            'criteria_met': criteria_met,
            'criteria_failed': criteria_failed,
            'recommendation': 'BUY' if is_value else 'PASS'
        }
