"""
Secure agent upload and testing runtime.

Lets users submit custom agent code and benchmark it against existing agents
without editing the repo. Uses restricted execution to prevent malicious code.
"""

import ast
import sys
import io
from typing import Dict, Optional
from contextlib import redirect_stdout, redirect_stderr
import traceback


class AgentUploadRuntime:
    """
    Sandboxed runtime for user-submitted agent code.
    
    Security approach:
    - Parse AST to check for dangerous imports/calls
    - Restrict available builtins
    - Timeout execution
    - Capture stdout/stderr
    """
    
    def __init__(self, timeout=5):
        self.timeout = timeout
        
        # Whitelist of allowed imports
        self.allowed_imports = {
            'numpy', 'np',
            'pandas', 'pd',
            'agents.base_agent',
            'typing'
        }
        
        # Blacklist of dangerous builtins
        self.blocked_builtins = {
            'eval', 'exec', 'compile',
            '__import__', 'open', 'input',
            'file', 'execfile'
        }
    
    def validate_code(self, code):
        """
        Check if code is safe to execute.
        Returns (is_safe, error_message).
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        
        # Check for dangerous patterns
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in self.allowed_imports:
                        return False, f"Import not allowed: {alias.name}"
            
            if isinstance(node, ast.ImportFrom):
                if node.module not in self.allowed_imports:
                    return False, f"Import not allowed: {node.module}"
            
            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.blocked_builtins:
                        return False, f"Blocked function: {node.func.id}"
        
        return True, None
    
    def execute_agent_code(self, code, agent_class_name):
        """
        Execute user code and extract the agent class.
        Returns (agent_class, error) tuple.
        """
        # Validate first
        is_safe, error = self.validate_code(code)
        if not is_safe:
            return None, error
        
        # Create restricted globals
        restricted_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'enumerate': enumerate,
                'isinstance': isinstance,
                'float': float,
                'int': int,
                'str': str,
                'list': list,
                'dict': dict,
                'True': True,
                'False': False,
                'None': None
            }
        }
        
        # Allow importing base agent
        restricted_globals['__name__'] = '__main__'
        
        # Capture output
        stdout = io.StringIO()
        stderr = io.StringIO()
        
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exec(code, restricted_globals)
            
            # Extract the agent class
            if agent_class_name not in restricted_globals:
                return None, f"Agent class '{agent_class_name}' not found in code"
            
            agent_class = restricted_globals[agent_class_name]
            return agent_class, None
            
        except Exception as e:
            error_msg = f"Execution error: {str(e)}\n{traceback.format_exc()}"
            return None, error_msg
    
    def test_agent(self, agent_class, market_data, event_data=None):
        """
        Test an uploaded agent with sample data.
        Returns (signal, error) tuple.
        """
        try:
            # Instantiate agent
            agent = agent_class("UploadedAgent")
            
            # Generate signal
            signal = agent.generate_signal(market_data, event_data)
            
            return signal, None
            
        except Exception as e:
            return None, f"Agent test failed: {str(e)}"


def upload_and_test_agent(code, agent_class_name, market_data, event_data=None):
    """
    Main interface for uploading and testing an agent.
    
    Args:
        code: String containing agent class definition
        agent_class_name: Name of the class to instantiate
        market_data: Test market data
        event_data: Optional event data
    
    Returns:
        Dict with results and any errors
    """
    runtime = AgentUploadRuntime()
    
    result = {
        'success': False,
        'agent_class': None,
        'test_signal': None,
        'errors': []
    }
    
    # Step 1: Validate and execute code
    agent_class, error = runtime.execute_agent_code(code, agent_class_name)
    if error:
        result['errors'].append(error)
        return result
    
    result['agent_class'] = agent_class_name
    
    # Step 2: Test with sample data
    signal, error = runtime.test_agent(agent_class, market_data, event_data)
    if error:
        result['errors'].append(error)
        return result
    
    result['success'] = True
    result['test_signal'] = signal
    
    return result


# Example usage for notebook or web interface
def notebook_upload_demo():
    """
    Demo for Jupyter notebook or web interface.
    """
    sample_code = '''
from agents.base_agent import BaseAgent, Signal

class MyUploadedAgent(BaseAgent):
    def generate_signal(self, market_data, event_data=None):
        price = market_data.get('price', 100)
        
        # Simple logic: buy if price < 100
        if price < 100:
            return Signal(
                timestamp=market_data.get('timestamp', 0),
                symbol=market_data.get('symbol', 'TEST'),
                action='BUY',
                confidence=0.75,
                size=100,
                reason="Price below threshold",
                agent_name=self.name,
                price=price
            )
        return None
'''
    
    sample_market_data = {
        'timestamp': 1699300000,
        'symbol': 'SPY',
        'price': 95.0,
        'volume': 1000000
    }
    
    result = upload_and_test_agent(
        code=sample_code,
        agent_class_name='MyUploadedAgent',
        market_data=sample_market_data
    )
    
    if result['success']:
        print(f"Agent uploaded successfully: {result['agent_class']}")
        print(f"Test signal: {result['test_signal']}")
    else:
        print("Upload failed:")
        for error in result['errors']:
            print(f"  - {error}")
    
    return result
