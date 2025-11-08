"""
Explainability module for feature attribution.

Shows which factors (price, volume, event probabilities) drove each decision.
Lightweight implementation - can be extended with SHAP/LIME for ML models.
"""

from typing import Dict, List
from collections import defaultdict


class SimpleExplainer:
    """
    Simple rule-based explainer for agent decisions.
    Attributes decisions to price, volume, events, and technical factors.
    """
    
    def __init__(self):
        self.explanations = []
        self.feature_impacts = defaultdict(list)
    
    def explain_signal(self, signal, market_data, event_data=None):
        """
        Generate explanation for a trading signal.
        
        Returns dict with feature attributions.
        """
        explanation = {
            'agent': signal.agent_name,
            'action': signal.action,
            'confidence': signal.confidence,
            'reason': signal.reason,
            'attributions': {}
        }
        
        # Parse reason string to identify key factors
        reason_lower = signal.reason.lower()
        
        # Check for price-related factors
        if any(word in reason_lower for word in ['price', 'momentum', 'trend', 'moving average']):
            explanation['attributions']['price'] = 0.4
        
        # Check for volume
        if 'volume' in reason_lower:
            explanation['attributions']['volume'] = 0.2
        
        # Check for event-driven factors
        if event_data and any(word in reason_lower for word in ['fed', 'election', 'hike', 'odds', 'probability']):
            explanation['attributions']['events'] = 0.5
            
            # Identify specific events
            explanation['event_details'] = {}
            for event_name, event_info in event_data.items():
                if event_name in reason_lower or event_name.replace('_', ' ') in reason_lower:
                    explanation['event_details'][event_name] = event_info.get('yes_probability', 0)
        
        # Check for technical indicators
        if any(word in reason_lower for word in ['bollinger', 'rsi', 'macd', 'crossover']):
            explanation['attributions']['technical'] = 0.3
        
        # Normalize attributions if they exist
        if explanation['attributions']:
            total = sum(explanation['attributions'].values())
            if total > 0:
                explanation['attributions'] = {
                    k: v / total for k, v in explanation['attributions'].items()
                }
        
        # Store for later analysis
        self.explanations.append(explanation)
        
        for feature, impact in explanation['attributions'].items():
            self.feature_impacts[feature].append(impact)
        
        return explanation
    
    def print_explanation(self, explanation):
        """Print human-readable explanation."""
        print(f"\nAgent: {explanation['agent']}")
        print(f"Action: {explanation['action']} (confidence: {explanation['confidence']:.1%})")
        print(f"Reason: {explanation['reason']}")
        
        if explanation['attributions']:
            print("\nFeature Attribution:")
            for feature, impact in sorted(explanation['attributions'].items(), 
                                        key=lambda x: x[1], reverse=True):
                bar_len = int(impact * 40)
                bar = '█' * bar_len + '░' * (40 - bar_len)
                print(f"  {feature:12} [{bar}] {impact:.1%}")
        
        if 'event_details' in explanation:
            print("\nEvent Probabilities:")
            for event, prob in explanation['event_details'].items():
                print(f"  {event}: {prob:.1%}")
    
    def print_summary(self):
        """Print summary of all explanations."""
        if not self.explanations:
            print("No explanations generated yet")
            return
        
        print("\n" + "="*70)
        print("EXPLAINABILITY SUMMARY")
        print("="*70)
        
        print(f"\nTotal decisions analyzed: {len(self.explanations)}")
        
        # Action distribution
        actions = defaultdict(int)
        for exp in self.explanations:
            actions[exp['action']] += 1
        
        print("\nAction Distribution:")
        for action, count in actions.items():
            pct = count / len(self.explanations)
            print(f"  {action}: {count} ({pct:.1%})")
        
        # Average feature importance
        if self.feature_impacts:
            print("\nAverage Feature Importance:")
            for feature, impacts in sorted(self.feature_impacts.items(), 
                                          key=lambda x: sum(x[1])/len(x[1]), 
                                          reverse=True):
                avg_impact = sum(impacts) / len(impacts)
                bar_len = int(avg_impact * 40)
                bar = '█' * bar_len + '░' * (40 - bar_len)
                print(f"  {feature:12} [{bar}] {avg_impact:.1%}")
        
        print("="*70 + "\n")


class SHAPExplainer:
    """
    Placeholder for SHAP-based explainability.
    Requires sklearn/shap libraries and trained models.
    """
    
    def __init__(self):
        self.model = None
        print("SHAP explainer not yet implemented. Use SimpleExplainer for now.")
    
    def explain(self, model, features):
        """
        Would use SHAP to explain model predictions.
        Implementation left for future enhancement.
        """
        raise NotImplementedError("SHAP integration coming soon")
