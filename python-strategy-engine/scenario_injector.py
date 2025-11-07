"""
Scenario injection for stress testing agents.

Lets you inject volatility spikes, rate hikes, flash crashes, and other
regime changes to see which agents break and which adapt.

This is where you prove your agents aren't overfit to one market condition.
"""

from typing import Dict, List, Callable
import numpy as np
from datetime import datetime


class ScenarioInjector:
    """
    Injects synthetic market shocks and event probability shifts.
    Use this to test agent robustness across different regimes.
    """
    
    def __init__(self):
        self.scenarios = {}
        self.active = []
    
    def inject_volatility_spike(self, market_data, multiplier=3.0):
        """Sudden volatility increase."""
        modified = market_data.copy()
        modified['volatility'] = modified.get('volatility', 0.01) * multiplier
        modified['scenario'] = f'VOL_SPIKE_{multiplier}x'
        return modified
    
    def inject_rate_hike_shock(self, market_data, basis_points=50):
        """
        Simulate Fed rate hike announcement.
        Price drops, vol spikes, event odds shift.
        """
        modified = market_data.copy()
        
        # Price impact: roughly -2% per 25bps
        impact = -0.02 * (basis_points / 25)
        modified['price'] = modified.get('price', 100) * (1 + impact)
        modified['volatility'] = modified.get('volatility', 0.01) * 2.5
        modified['scenario'] = f'RATE_HIKE_{basis_points}BPS'
        
        # Update event data if present
        if 'events' in modified and 'fed_hike' in modified['events']:
            # Spike Fed hike probability to near certainty
            modified['events']['fed_hike']['yes_probability'] = 0.95
        
        return modified
    
    def inject_flash_crash(self, market_data, drop_pct=0.10):
        """Sudden price drop with volume spike."""
        modified = market_data.copy()
        modified['price'] = modified.get('price', 100) * (1 - drop_pct)
        modified['volume'] = modified.get('volume', 1000) * 5.0
        modified['volatility'] = modified.get('volatility', 0.01) * 10.0
        modified['scenario'] = f'FLASH_CRASH_{drop_pct:.0%}'
        return modified
    
    def inject_event_shift(self, market_data, event_name, new_prob):
        """
        Inject a sudden event probability shift.
        Example: Election odds swing from 40% to 70% overnight.
        """
        modified = market_data.copy()
        
        if 'events' not in modified:
            modified['events'] = {}
        
        if event_name not in modified['events']:
            modified['events'][event_name] = {
                'source': 'injected',
                'yes_probability': new_prob,
                'title': f'Injected {event_name}'
            }
        else:
            old_prob = modified['events'][event_name]['yes_probability']
            modified['events'][event_name]['yes_probability'] = new_prob
            shift = abs(new_prob - old_prob)
            modified['scenario'] = f'EVENT_SHIFT_{event_name}_{shift:.0%}'
        
        return modified
    
    def inject_regime_shift(self, market_data, regime):
        """
        Mark explicit regime change.
        Regimes: 'BULL', 'BEAR', 'SIDEWAYS', 'HIGH_VOL', 'LOW_VOL'
        """
        modified = market_data.copy()
        modified['regime'] = regime
        modified['scenario'] = f'REGIME_{regime}'
        
        # Adjust params by regime
        params = {
            'BULL': {'trend': 0.001, 'vol_mult': 0.8},
            'BEAR': {'trend': -0.002, 'vol_mult': 1.5},
            'SIDEWAYS': {'trend': 0.0, 'vol_mult': 0.5},
            'HIGH_VOL': {'trend': 0.0, 'vol_mult': 3.0},
            'LOW_VOL': {'trend': 0.0, 'vol_mult': 0.3}
        }
        
        p = params.get(regime, {'trend': 0, 'vol_mult': 1.0})
        
        base_price = modified.get('price', 100)
        modified['price'] = base_price * (1 + p['trend'])
        modified['volatility'] = modified.get('volatility', 0.01) * p['vol_mult']
        
        return modified
    
    def run_stress_test(self, agents, market_data):
        """
        Run all agents through adversarial scenarios.
        Reports which agents fail under stress.
        """
        results = {
            'scenarios': {},
            'agent_robustness': {a.name: {'failures': 0, 'total': 0} for a in agents}
        }
        
        scenarios = [
            ('vol_spike', lambda d: self.inject_volatility_spike(d, 5.0)),
            ('rate_shock', lambda d: self.inject_rate_hike_shock(d, 75)),
            ('flash_crash', lambda d: self.inject_flash_crash(d, 0.15)),
            ('fed_shift', lambda d: self.inject_event_shift(d, 'fed_hike', 0.90))
        ]
        
        for scenario_name, scenario_fn in scenarios:
            modified = scenario_fn(market_data)
            scenario_results = []
            
            for agent in agents:
                # Get event_data if present in modified market_data
                event_data = modified.get('events')
                signal = agent.generate_signal(modified, event_data)
                
                results['agent_robustness'][agent.name]['total'] += 1
                
                # Failure = no signal or very low confidence under stress
                if signal is None or signal.confidence < 0.3:
                    results['agent_robustness'][agent.name]['failures'] += 1
                    scenario_results.append({
                        'agent': agent.name,
                        'status': 'FAILED',
                        'signal': None
                    })
                else:
                    scenario_results.append({
                        'agent': agent.name,
                        'status': 'PASS',
                        'action': signal.action,
                        'confidence': signal.confidence
                    })
            
            results['scenarios'][scenario_name] = scenario_results
        
        # Calculate robustness scores
        for agent_name, stats in results['agent_robustness'].items():
            if stats['total'] > 0:
                stats['score'] = 1 - (stats['failures'] / stats['total'])
        
        return results
    
    def print_stress_report(self, results):
        """Human-readable stress test report."""
        print("\n" + "="*70)
        print("ADVERSARIAL STRESS TEST REPORT")
        print("="*70)
        
        for scenario, scenario_results in results['scenarios'].items():
            print(f"\n{scenario.upper()}")
            print("-" * 70)
            for r in scenario_results:
                symbol = "✓" if r['status'] == 'PASS' else "✗"
                print(f"  {symbol} {r['agent']:25} {r['status']}")
        
        print("\n" + "="*70)
        print("AGENT ROBUSTNESS SCORES")
        print("="*70)
        
        for agent_name, stats in results['agent_robustness'].items():
            score = stats.get('score', 0)
            bar_len = int(score * 40)
            bar = '█' * bar_len + '░' * (40 - bar_len)
            print(f"{agent_name:25} [{bar}] {score:.1%}")
        
        print("="*70 + "\n")
