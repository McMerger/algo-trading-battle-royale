# Quick Start Guide

## Multi-Source Prediction Market Trading System

Get up and running in 5 minutes.

---

## Installation

```bash
# Clone and setup
git clone https://github.com/McMerger/algo-trading-battle-royale.git
cd algo-trading-battle-royale
pip install -r requirements.txt
cd python-strategy-engine
```

**Dependencies installed:**
- numpy, pandas (data handling)
- requests (API calls)
- feedparser (RSS feeds)
- google-genai (optional, for explanations)

---

## 1. Test Data Sources

Verify all three data sources are working:

```bash
python test_multisource.py
```

**Expected output:**
```
TESTING MULTI-SOURCE DATA FEEDS
1. Testing Polymarket (Prediction Markets)...
   Found 2 Polymarket markets
   - btc_100k: 68% probability (polymarket)

2. Testing DeFiLlama (On-Chain Data)...
   Total exchange inflows: $450.0M
   Total DeFi TVL: $85.00B

3. Testing RSS News Feeds...
   Found 2 high-impact events
   - [coindesk] Bitcoin ETF approval imminent...

✓ All data sources tested
```

This verifies:
- ✅ Polymarket API connection
- ✅ DeFiLlama on-chain data
- ✅ RSS news feeds

---

## 2. Run Multi-Source Demo

See all three sources working together:

```bash
python strategy-engine.py --mode multisource --epochs 10
```

**What this does:**
- Creates 5 agents (3 single-source + 2 hybrid)
- Fetches live data from Polymarket, DeFiLlama, and news feeds
- Generates trading signals when sources align
- Shows performance comparison

**Expected output:**
```
MULTI-SOURCE SIGNAL FUSION DEMO
Three Independent Sources: Polymarket + On-Chain + News

Agents:
  - Polymarket-Only
  - OnChain-Only
  - News-Only
  - Hybrid-2of3      ← Requires 2/3 sources to confirm
  - Hybrid-3of3      ← Requires all 3 sources to confirm

Epoch  1: 3 signals generated
  - Polymarket-Only : BUY  @ 68% | 68% BTC $100k odds
  - OnChain-Only    : BUY  @ 75% | $450M inflows
  - Hybrid-2of3     : BUY  @ 77% | 2/3 sources confirm BUY

KEY INSIGHT: Multi-Source Confirmation
Single-source agents show higher noise and false positives.
Multi-source agents trade less frequently but with higher conviction.
Expected improvement: ~23% fewer false positives with 2/3 confirmation
```

---

## 3. Explore Usage Patterns

See all README code examples in action:

```bash
python example_multisource_usage.py
```

**What you'll see:**
1. **Individual adapters** (Polymarket, DeFiLlama, News)
2. **Building custom agents** (exact README pattern)
3. **Full integration** (all three feeds combined)
4. **Hybrid confirmation** (aligned vs conflicting scenarios)

---

## 4. Build Your Own Agent

Copy this template:

```python
# my_agent.py
from agents.base_agent import BaseAgent, Signal

class MyAgent(BaseAgent):
    def generate_signal(self, market_data, event_data):
        # Access Polymarket
        polymarket = event_data.get('polymarket', {})
        btc_odds = polymarket.get('btc_100k', {}).get('yes_probability', 0.5)

        # Access on-chain
        onchain = event_data.get('onchain', {})
        inflows = onchain.get('total_exchange_inflows', 0)

        # Access news
        news = event_data.get('news_events', {})
        event_count = news.get('count', 0)

        # Your logic here
        if btc_odds > 0.65 and inflows > 400e6 and event_count > 0:
            return Signal(
                timestamp=market_data['timestamp'],
                symbol=market_data['symbol'],
                action='BUY',
                confidence=btc_odds,
                size=100,
                reason=f"3/3 sources confirm: {btc_odds:.0%} odds + ${inflows/1e6:.0f}M inflows + {event_count} events",
                agent_name=self.name,
                price=market_data['price']
            )

        return None
```

---

## 5. Offline Testing (Mock Data)

Test without API calls using mock data:

```bash
python strategy-engine.py --mode multisource --mock --epochs 5
```

**Use this for:**
- ✅ Development without rate limits
- ✅ CI/CD testing
- ✅ Learning the system offline

---

## Other Modes

### Discover Polymarket Markets

```bash
python strategy-engine.py --mode discover
```

Find current market slugs for:
- Bitcoin/crypto predictions
- Federal Reserve decisions
- US elections
- Economic indicators

### Test API Connection

```bash
python strategy-engine.py --mode test
```

Quick connectivity check for Polymarket.

### Stress Testing

```bash
python strategy-engine.py --mode stress
```

See how agents behave under:
- 20% volatility spikes
- Flash crashes (-15%)
- Sudden probability reversals

### Meta-Agent Demo

```bash
python strategy-engine.py --mode meta --epochs 30
```

Thompson Sampling learns which agent to trust in real-time.

---

## Understanding the Output

### Signal Format

```python
Signal(
    timestamp=1699488000,
    symbol='BTC',
    action='BUY',           # BUY, SELL, or HOLD
    confidence=0.82,        # 0-1 (higher = more confident)
    size=100,
    reason="2/3 sources confirm BUY | Polymarket: BUY + On-chain: BUY",
    agent_name='Hybrid-2of3',
    price=95000
)
```

### Key Metrics

- **Win Rate:** % of profitable trades
- **Sharpe Ratio:** Risk-adjusted returns (>1.0 is good)
- **PnL:** Total profit/loss
- **Confidence:** Agent's conviction (0-100%)

---

## Common Patterns

### Pattern 1: All Sources Align → Trade

```python
Polymarket: 68% BTC $100k (bullish)
On-chain: $450M inflows (bullish)
News: Fed dovish (bullish)

Result: BUY @ 84% confidence (3/3 sources)
```

### Pattern 2: Sources Conflict → Avoid

```python
Polymarket: 78% Fed hike (bearish)
On-chain: $600M inflows (bullish)
News: No events (neutral)

Result: NO TRADE (conflict detected)
```

### Pattern 3: Insufficient Data → Wait

```python
Polymarket: No relevant markets
On-chain: Below threshold
News: No events

Result: NO TRADE (insufficient signals)
```

---

## Next Steps

1. **Run the tests:**
   ```bash
   python test_multisource.py
   ```

2. **Try the demo:**
   ```bash
   python strategy-engine.py --mode multisource --epochs 10
   ```

3. **Study the examples:**
   ```bash
   python example_multisource_usage.py
   ```

4. **Build your agent:**
   - Copy template above
   - Add to `agents/` directory
   - Import in `strategy-engine.py`
   - Test with `--mock` first

5. **Read the docs:**
   - `README.md` - Full system overview
   - `IMPLEMENTATION_STATUS.md` - Technical verification
   - Code comments in each file

---

## Troubleshooting

### "Connection failed" errors

```bash
# Use mock data
python strategy-engine.py --mode multisource --mock
```

### Rate limits (DeFiLlama: 300 req/5min)

```bash
# Reduce epochs or increase sleep time
python strategy-engine.py --mode multisource --epochs 5
```

### Import errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## Key Files

| File | Purpose |
|------|---------|
| `strategy-engine.py` | Main entry point, all demos |
| `test_multisource.py` | Comprehensive test suite |
| `example_multisource_usage.py` | README code examples |
| `agents/hybrid_agent.py` | Multi-source confirmation logic |
| `market_data/onchain.py` | DeFiLlama adapter |
| `market_data/events.py` | News/RSS adapter |
| `market_data/prediction_market_adapter.py` | Polymarket adapter |

---

## Support

- **Issues:** Open a GitHub issue
- **Examples:** Check `example_multisource_usage.py`
- **Tests:** Run `test_multisource.py`
- **Docs:** See `README.md`

---

**Ready to trade on prediction market signals!** 🚀

*Remember: This is a research platform. Not financial advice. Test thoroughly before risking real capital.*
