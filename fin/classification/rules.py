"""Rule-based classification engine."""

import yaml
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class RuleEngine:
    """Engine for classifying transactions based on deterministic rules."""
    
    def __init__(self, rules_file: str = "fin/config/rules.yaml"):
        """
        Initialize the rule engine.
        
        Args:
            rules_file: Path to the YAML rules file
        """
        self.rules_file = rules_file
        self.rules = self._load_rules()
        self._compile_patterns()
    
    def _load_rules(self) -> List[Dict]:
        """Load rules from YAML file."""
        try:
            # Try absolute path first
            path = Path(self.rules_file)
            if not path.is_absolute():
                # Try relative to project root (assuming we run from root)
                path = Path.cwd() / self.rules_file
            
            if not path.exists():
                print(f"Warning: Rules file not found at {path}")
                return []
                
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('rules', [])
        except Exception as e:
            print(f"Error loading rules: {e}")
            return []
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        for rule in self.rules:
            try:
                rule['compiled_pattern'] = re.compile(rule['pattern'], re.IGNORECASE)
            except re.error as e:
                print(f"Invalid regex pattern '{rule['pattern']}': {e}")
                rule['compiled_pattern'] = None
    
    def classify(self, description: str) -> Tuple[Optional[str], Optional[str], float]:
        """
        Classify a transaction description using defined rules.
        
        Args:
            description: Transaction description (normalized)
            
        Returns:
            Tuple containing:
            - category: Detected category or None
            - subcategory: Detected subcategory or None
            - confidence: Confidence score (1.0 for rule match)
        """
        if not description:
            return None, None, 0.0
        
        # Sort rules by priority (descending)
        sorted_rules = sorted(self.rules, key=lambda x: x.get('priority', 0), reverse=True)
        
        best_match = None
        
        for rule in sorted_rules:
            pattern = rule.get('compiled_pattern')
            if not pattern:
                continue
                
            if pattern.search(description):
                return rule['category'], rule['subcategory'], 1.0
        
        return None, None, 0.0
