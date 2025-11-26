#!/usr/bin/env python3
"""
End-to-End Integration Test for SignalOps

Tests the complete flow:
1. Python multi-source data fusion
2. Strategy decision making
3. Go execution engine
4. Binance API (test mode)
5. PostgreSQL logging

Run this to verify the system is working.
"""

import sys
import os
import time
from datetime import datetime

# Add python-strategy-engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python-strategy-engine'))

from market_data.multi_source_feed import MultiSourceDataFeed
from market_data.prediction_market_adapter import PredictionMarketFeed
from execution_client import ExecutionClient
from agents.graham_defensive import GrahamDefensiveStrategy


def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_multi_source_data():
    """Test 1: Multi-Source Data Fusion"""
    print_section("TEST 1: Multi-Source Data Fusion")

    feed = MultiSourceDataFeed(use_mock=False)

    # Mock market data
    market_data = {
        'symbol': 'AAPL',
        'price': 150.0,
        'volume': 1000000,
        'timestamp': datetime.now().timestamp()
    }

    # Event configuration for Polymarket
    event_config = {
        'btc_100k': 'will-bitcoin-be-above-100000-on-january-1-2025',
        'recession': 'will-the-us-enter-a-recession-in-2025'
    }

    print("Fetching data from all sources...")
    unified = feed.get_unified_data('AAPL', market_data, event_config)

    print(f"✓ Sources contacted: {feed._count_sources(unified)}")
    print(f"✓ Events data: {len(unified.get('events', {}))} markets")
    print(f"✓ Fundamentals: {unified.get('fundamentals', {}).get('source', 'N/A')}")
    print(f"✓ On-chain: {unified.get('onchain', {}).get('source', 'N/A')}")
    print(f"✓ Technical: {unified.get('technical', {}).get('source', 'N/A')}")

    # Check for conflicts
    conflicts = unified.get('conflicts', [])
    print(f"✓ Conflicts detected: {len(conflicts)}")
    for conflict in conflicts:
        print(f"  - {conflict['type']}: {conflict['description']}")

    # Check consensus
    consensus = unified.get('consensus', {})
    print(f"✓ Consensus: {consensus.get('action')} (confidence: {consensus.get('confidence', 0):.2f})")

    return unified


def test_strategy_decision(unified_data):
    """Test 2: Strategy Decision Making"""
    print_section("TEST 2: Strategy Decision Making")

    strategy = GrahamDefensiveStrategy()

    print(f"Running {strategy.name} strategy...")

    # Add unified data to market_data
    market_data = {
        'symbol': 'AAPL',
        'price': 150.0,
        'timestamp': datetime.now().timestamp(),
        'unified': unified_data
    }

    signal = strategy.generate_signal(market_data)

    if signal:
        print(f"✓ Signal generated: {signal.action}")
        print(f"  Confidence: {signal.confidence:.2f}")
        print(f"  Size: ${signal.size:,.2f}")
        print(f"  Reason: {signal.reason}")
        return signal
    else:
        print("✗ No signal generated")
        return None


def test_go_execution_engine():
    """Test 3: Go Execution Engine Connection"""
    print_section("TEST 3: Go Execution Engine")

    print("Connecting to Go execution engine...")
    client = ExecutionClient()

    # Test health check first
    import requests
    try:
        resp = requests.get('http://localhost:8080/health', timeout=5)
        if resp.ok:
            print("✓ Go execution engine is healthy")
        else:
            print("✗ Go execution engine returned error")
            return None
    except Exception as e:
        print(f"✗ Cannot connect to Go engine: {e}")
        print("  Make sure to run: docker-compose up")
        return None

    # Test market data retrieval
    print("\nTesting market data retrieval...")
    try:
        market_data = client.get_market_data('BTCUSDT', 'binance')
        if 'error' in market_data:
            print(f"✗ Market data error: {market_data['error']}")
        else:
            print(f"✓ BTC Price: ${market_data.get('price', 'N/A'):,.2f}")
            print(f"  Bid: ${market_data.get('bid', 'N/A'):,.2f}")
            print(f"  Ask: ${market_data.get('ask', 'N/A'):,.2f}")
            print(f"  24h Volume: {market_data.get('volume_24h', 'N/A')}")
    except Exception as e:
        print(f"✗ Market data failed: {e}")

    return client


def test_order_submission(client, signal):
    """Test 4: Order Submission"""
    print_section("TEST 4: Order Submission (Paper Trading)")

    if not client:
        print("✗ Skipping - Go engine not available")
        return

    if not signal:
        print("✗ Skipping - No signal to execute")
        return

    print("Submitting test order...")

    order_id = f"test_{int(time.time())}"

    result = client.submit_order(
        order_id=order_id,
        strategy_name="GrahamDefensive",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.001,  # Small test order
        price=0.0,  # Market order
        order_type="MARKET",
        exchange="binance"
    )

    if result.get('success'):
        print(f"✓ Order submitted successfully")
        print(f"  Order ID: {result.get('order_id')}")
        print(f"  Exchange Order ID: {result.get('exchange_order_id', 'N/A')}")
        print(f"  Status: {result.get('status')}")
        print(f"  Executed Price: ${result.get('executed_price', 0):,.2f}")
        print(f"  Fees: ${result.get('fees', 0):.8f}")
    else:
        print(f"✗ Order failed: {result.get('error', 'Unknown error')}")

    return result


def test_database_logging():
    """Test 5: Database Logging"""
    print_section("TEST 5: Database Logging")

    try:
        import psycopg2
        conn = psycopg2.connect(
            "postgresql://signalops:signalops_dev_password@localhost:5432/signalops"
        )
        cursor = conn.cursor()

        # Check recent trades
        cursor.execute("SELECT COUNT(*) FROM trades")
        count = cursor.fetchone()[0]
        print(f"✓ Connected to PostgreSQL")
        print(f"  Total trades in database: {count}")

        # Get recent trade
        cursor.execute("""
            SELECT order_id, strategy_name, symbol, side, status, timestamp
            FROM trades
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            print(f"\n  Latest trade:")
            print(f"    Order ID: {row[0]}")
            print(f"    Strategy: {row[1]}")
            print(f"    Symbol: {row[2]}")
            print(f"    Side: {row[3]}")
            print(f"    Status: {row[4]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("  Make sure PostgreSQL is running: docker-compose up")


def main():
    print("\n" + "="*70)
    print("  SignalOps End-to-End Integration Test")
    print("  Testing: Python → Multi-Source Data → Strategy → Go → Binance")
    print("="*70)

    # Test 1: Multi-source data
    unified_data = test_multi_source_data()

    # Test 2: Strategy decision
    signal = test_strategy_decision(unified_data)

    # Test 3: Go execution engine
    client = test_go_execution_engine()

    # Test 4: Order submission
    test_order_submission(client, signal)

    # Test 5: Database logging
    test_database_logging()

    # Summary
    print_section("INTEGRATION TEST COMPLETE")
    print("\nNext steps:")
    print("  1. Review logs for any errors")
    print("  2. Check dashboard: http://localhost:8501")
    print("  3. Query database for trade history")
    print("  4. Run with live API keys for real trading")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    main()
