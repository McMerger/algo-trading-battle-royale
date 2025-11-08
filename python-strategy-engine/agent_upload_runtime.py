"""
Secure agent upload and testing runtime.

Allows users to submit custom agent code and benchmark it against existing strategies
without modifying the repo. Uses restricted execution for safety.
"""

import ast
import sys
import io
from typing import Dict, Optional
from contextlib import redirect_stdout, redirect_stderr
import traceback

from agents.base_agent import BaseAgent, Signal


class AgentUploadRuntime:
    """
    Sandboxed runtime for user-submitted agents.
    
    Security approach: AST validation + restricted globals.
    Not production-grade isolation (use containers for that), but good for demos.
    """
    
    def __init__(self):
        self.uploaded_agents = {}
        self.forbidden_imports = [
            'os', 'sys', 'subprocess', 'eval', 'exec',
            'open', 'file', '__import__', 'compile'
        ]
    
    def validate_agent_code(self, code):
        """
        Basic validation of submitted agent code.
        Checks for dangerous operations via AST parsing.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        
        # Check for forbidden operations
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name in self.forbidden_imports:
                        return False, f"Forbidden import: {name.name}"
            
            if isinstance(node, ast.ImportFrom):
                if node.module in self.forbidden_imports:
                    return False, f"Forbidden import: {node.module}"
            
            # Check for dangerous builtins
            if isinstance(node, ast.Name):
                if node.id in ['eval', 'exec', 'compile', '__import__']:
                    return False, f"Forbidden operation: {node.id}"
        
        return True, "Code validated"
    
    def load_agent_from_code(self, code, agent_name="UploadedAgent"):
        """
        Load agent class from user-submitted code string.
        
        Returns agent instance or None if validation fails.
        """
        # Validate code
        is_valid, msg = self.validate_agent_code(code)
        if not is_valid:
            print(f"Validation failed: {msg}")
            return None
        
        # Restricted globals for execution
        restricted_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'max': max,
                'min': min,
                'sum': sum,
                'abs': abs,
                'float': float,
                'int': int,
                'str': str,
                'dict': dict,
                'list': list,
            },
            'BaseAgent': BaseAgent,
            'Signal': Signal,
            'Optional': Optional,
            'Dict': Dict
        }
        
        # Safe imports allowed
        try:
            import numpy as np
            restricted_globals['np'] = np
        except ImportError:
            pass
        
        # Execute in restricted environment
        local_namespace = {}
        
        try:
            exec(code, restricted_globals, local_namespace)
        except Exception as e:
            print(f"Execution error: {e}")
            traceback.print_exc()
            return None
        
        # Find the agent class
        agent_class = None
        for name, obj in local_namespace.items():
            if isinstance(obj, type) and issubclass(obj, BaseAgent) and obj != BaseAgent:
                agent_class = obj
                break
        
        if not agent_class:
            print("No valid agent class found in submitted code")
            return None
        
        # Instantiate
        try:
            agent = agent_class(name=agent_name)
            self.uploaded_agents[agent_name] = agent
            print(f"Successfully loaded agent: {agent_name}")
            return agent
        except Exception as e:
            print(f"Failed to instantiate agent: {e}")
            return None
    
    def test_agent(self, agent, test_data):
        """
        Test an uploaded agent with sample data.
        Captures output and errors safely.
        """
        print(f"\nTesting agent: {agent.name}")
        print("-" * 50)
        
        results = []
        
        for i, data in enumerate(test_data):
            market_data = data.get('market_data', {})
            event_data = data.get('event_data')
            
            # Capture stdout/stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    signal = agent.generate_signal(market_data, event_data)
                
                result = {
                    'test_case': i,
                    'signal': signal,
                    'stdout': stdout_capture.getvalue(),
                    'stderr': stderr_capture.getvalue(),
                    'success': True
                }
                
                if signal:
                    print(f"Test {i}: {signal.action} @ {signal.confidence:.1%}")
                else:
                    print(f"Test {i}: HOLD")
                
            except Exception as e:
                result = {
                    'test_case': i,
                    'error': str(e),
                    'traceback': traceback.format_exc(),
                    'success': False
                }
                print(f"Test {i}: ERROR - {e}")
            
            results.append(result)
        
        return results


def example_uploaded_agent_code():
    """
    Example agent code that a user might submit.
    This is what the format should look like.
    """
    return """
from agents.base_agent import BaseAgent, Signal

class MyCustomAgent(BaseAgent):
    '''
    User-submitted agent that trades on simple momentum.
    '''
    
    def __init__(self, name="MyCustomAgent"):
        super().__init__(name)
        self.prev_price = None
    
    def generate_signal(self, market_data, event_data=None):
        price = market_data.get('price', 0)
        
        # Simple momentum strategy
        if self.prev_price is None:
            self.prev_price = price
            return None
        
        momentum = (price - self.prev_price) / self.prev_price
        self.prev_price = price
        
        if abs(momentum) < 0.002:  # Less than 0.2% move
            return None
        
        action = 'BUY' if momentum > 0 else 'SELL'
        confidence = min(abs(momentum) * 100, 0.9)
        
        return Signal(
            timestamp=market_data.get('timestamp', 0),
            symbol=market_data.get('symbol', 'UNKNOWN'),
            action=action,
            confidence=confidence,
            size=100,
            reason=f"Momentum {momentum:.2%}",
            agent_name=self.name,
            price=price
        )
"""


# Demo usage
if __name__ == "__main__":
    runtime = AgentUploadRuntime()
    
    # Load example agent
    code = example_uploaded_agent_code()
    agent = runtime.load_agent_from_code(code, "UserMomentum")
    
    if agent:
        # Test with sample data
        test_data = [
            {
                'market_data': {'price': 100, 'volume': 1000, 'timestamp': 1},
                'event_data': None
            },
            {
                'market_data': {'price': 101, 'volume': 1000, 'timestamp': 2},
                'event_data': None
            },
            {
                'market_data': {'price': 102, 'volume': 1000, 'timestamp': 3},
                'event_data': None
            }
        ]
        
        results = runtime.test_agent(agent, test_data)
        
        print("\nTest Summary:")
        successes = sum(1 for r in results if r.get('success'))
        print(f"Passed: {successes}/{len(results)}")
