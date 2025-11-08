"""
Explainability for agent decisions using SHAP/LIME or simple attribution.

Shows which features (price, volume, event probabilities) drove each decision.
"""

import numpy as np
from typing import Dict, List, Optional


class SimpleExplainer:
    """
    Simple feature attribution for agent decisions.
    
    More sophisticated than just logging, less complex than full SHAP.
    Good middle ground for most use cases.
    """
    
    def __init__(self):
        self.feature_history = []
    
    def explain_signal(self, signal, market_data, event_data=None):
        """
        Attribute a signal to its input features.
        
        Returns dict with feature importances.
        """
        if not signal:
            return None
        
        features = {}
        importances = {}
        
        # Extract market features
        features['price'] = market_data.get('price', 0)
        features['volume'] = market_data.get('volume', 0)
        features['volatility'] = market_data.get('volatility', 0)
        
        # Extract event features
        if event_data:
            for event_name, event in event_data.items():
                prob = event.get('yes_probability', 0.5)
                features[f'event_{event_name}'] = prob
        
        # Simple attribution based on signal reasoning
        reason = signal.reason.lower()
        
        # Check which features are mentioned in reason
        total_mentions = 0
        for feature_name in features.keys():
            if feature_name.replace('_', ' ') in reason or feature_name in reason:
                importances[feature_name] = 1.0
                total_mentions += 1
        
        # If event mentioned, give it high weight
        if 'fed' in reason or 'event' in reason or 'probability' in reason:
            for key in features:
                if key.startswith('event_'):
                    importances[key] = importances.get(key, 0) + 2.0
                    total_mentions += 2
        
        # Normalize
        if total_mentions > 0:
            for key in importances:
                importances[key] /= total_mentions
        
        explanation = {
            'signal': signal,
            'features': features,
            'importances': importances,
            'primary_driver': max(importances.items(), key=lambda x: x[1])[0] if importances else None
        }
        
        self.feature_history.append(explanation)
        return explanation
    
    def print_explanation(self, explanation):
        """Human-readable feature attribution."""
        if not explanation:
            return
        
        print("\nFeature Attribution:")
        print("-" * 50)
        
        sorted_features = sorted(
            explanation['importances'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for feature, importance in sorted_features:
            bar_len = int(importance * 30)
            bar = '█' * bar_len + '░' * (30 - bar_len)
            value = explanation['features'].get(feature, 0)
            print(f"{feature:20} [{bar}] {importance:.1%}  (value: {value})")
        
        print(f"\nPrimary driver: {explanation['primary_driver']}")
        print("-" * 50)
    
    def get_feature_summary(self):
        """
        Aggregate feature importance across all decisions.
        Useful for understanding what drives your agents overall.
        """
        if not self.feature_history:
            return {}
        
        all_importances = {}
        counts = {}
        
        for exp in self.feature_history:
            for feature, importance in exp['importances'].items():
                all_importances[feature] = all_importances.get(feature, 0) + importance
                counts[feature] = counts.get(feature, 0) + 1
        
        # Average importance
        summary = {
            feature: all_importances[feature] / counts[feature]
            for feature in all_importances
        }
        
        return dict(sorted(summary.items(), key=lambda x: x[1], reverse=True))
    
    def print_summary(self):
        """Print overall feature importance summary."""
        summary = self.get_feature_summary()
        
        print("\n" + "="*60)
        print("OVERALL FEATURE IMPORTANCE")
        print("="*60)
        
        for feature, avg_importance in summary.items():
            bar_len = int(avg_importance * 40)
            bar = '█' * bar_len + '░' * (40 - bar_len)
            print(f"{feature:25} [{bar}] {avg_importance:.1%}")
        
        print("="*60 + "\n")


# For future: SHAP integration stub
class SHAPExplainer:
    """
    Placeholder for SHAP-based explainability.
    
    SHAP (SHapley Additive exPlanations) provides rigorous feature attribution
    but requires training a model. For now, use SimpleExplainer above.
    
    To implement:
    1. pip install shap
    2. Train surrogate model on (features → agent decisions)
    3. Use SHAP to explain each prediction
    """
    
    def __init__(self):
        self.model = None
        raise NotImplementedError("SHAP integration coming soon. Use SimpleExplainer for now.")
