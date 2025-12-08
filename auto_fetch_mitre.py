import requests
import re
import json
import yaml
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

class MITREFetcher:
    """Tự động fetch thông tin từ MITRE ATT&CK và Atomic Red Team"""
    
    def __init__(self):
        self.mitre_base_url = "https://attack.mitre.org"
        self.atomic_base_url = "https://raw.githubusercontent.com/redcanaryco/atomic-red-team/master/atomics"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_mitre_technique(self, technique_id: str) -> Dict:
        """
        Lấy thông tin từ MITRE ATT&CK
        
        Args:
            technique_id: Ví dụ "T1036" hoặc "T1548.002"
        
        Returns:
            Dict chứa description, procedure examples, detection methods
        """
        # Format URL
        formatted_id = technique_id.replace('.', '/')
        url = f"{self.mitre_base_url}/techniques/{formatted_id}/"
        
        print(f"[*] Fetching MITRE: {url}")
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract technique name
            name_elem = soup.find('h1')
            name = name_elem.get_text().strip() if name_elem else "Unknown"
            
            # Extract description
            desc_elem = soup.find('div', class_='description-body')
            description = desc_elem.get_text().strip() if desc_elem else ""
            
            # Extract procedure examples (APT usage)
            procedures = []
            procedure_cards = soup.find_all('div', class_='card-data')
            for card in procedure_cards:
                # Find group/software name
                name_tag = card.find('a', class_='card-title')
                if name_tag:
                    actor_name = name_tag.get_text().strip()
                    
                    # Find description
                    desc_tag = card.find('div', class_='description-body')
                    if desc_tag:
                        actor_desc = desc_tag.get_text().strip()
                        procedures.append({
                            'actor': actor_name,
                            'description': actor_desc
                        })
            
            # Extract detection methods
            detection = ""
            detection_section = soup.find('h2', string=re.compile('Detection', re.I))
            if detection_section:
                detection_div = detection_section.find_next('div', class_='description-body')
                if detection_div:
                    detection = detection_div.get_text().strip()
            
            # Extract mitigation
            mitigation = ""
            mitigation_section = soup.find('h2', string=re.compile('Mitigation', re.I))
            if mitigation_section:
                mitigation_div = mitigation_section.find_next('div', class_='description-body')
                if mitigation_div:
                    mitigation = mitigation_div.get_text().strip()
            
            return {
                'technique_id': technique_id,
                'name': name,
                'description': description,
                'procedures': procedures,
                'detection': detection,
                'mitigation': mitigation,
                'url': url
            }
            
        except Exception as e:
            print(f"[!] Error fetching MITRE: {e}")
            return None
    
    def fetch_atomic_tests(self, technique_id: str) -> List[Dict]:
        """
        Lấy test cases từ Atomic Red Team
        
        Args:
            technique_id: Ví dụ "T1036"
        
        Returns:
            List of test cases
        """
        url = f"{self.atomic_base_url}/{technique_id}/{technique_id}.yaml"
        
        print(f"[*] Fetching Atomic Red Team: {url}")
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse YAML
            data = yaml.safe_load(response.text)
            
            tests = []
            if 'atomic_tests' in data:
                for test in data['atomic_tests']:
                    test_info = {
                        'name': test.get('name', ''),
                        'description': test.get('description', ''),
                        'platforms': test.get('supported_platforms', []),
                        'executor': test.get('executor', {}),
                        'input_arguments': test.get('input_arguments', {})
                    }
                    
                    # Extract commands
                    executor = test.get('executor', {})
                    if 'command' in executor:
                        test_info['command'] = executor['command']
                    if 'cleanup_command' in executor:
                        test_info['cleanup'] = executor['cleanup_command']
                    
                    tests.append(test_info)
            
            return tests
            
        except Exception as e:
            print(f"[!] Error fetching Atomic Red Team: {e}")
            return []
    
    def generate_mitre_techniques_section(self, technique_id: str) -> str:
        """
        Tạo phần mitre_techniques tự động
        
        Args:
            technique_id: Ví dụ "T1036" hoặc "T1548.002"
        
        Returns:
            String formatted cho mitre_techniques
        """
        # Fetch data
        mitre_data = self.fetch_mitre_technique(technique_id)
        if not mitre_data:
            return self._generate_fallback_template(technique_id)
        
        atomic_tests = self.fetch_atomic_tests(technique_id.split('.')[0])  # Remove sub-technique
        
        # Build mitre_techniques string
        output = f"""# {mitre_data['technique_id']} - {mitre_data['name']}

## Context:
{mitre_data['description'][:500]}...

## Alternative Methods:
"""
        
        # Add Atomic Red Team test cases
        if atomic_tests:
            output += "\n### From Atomic Red Team:\n\n"
            for i, test in enumerate(atomic_tests[:10], 1):  # Limit to 10 tests
                output += f"#### {i}. {test['name']}\n"
                if 'description' in test and test['description']:
                    output += f"{test['description']}\n\n"
                
                if 'command' in test:
                    # Clean up command
                    cmd = test['command'].strip()
                    # Replace input variables
                    for arg_name, arg_info in test.get('input_arguments', {}).items():
                        default_val = arg_info.get('default', '<value>')
                        cmd = cmd.replace(f"#{{{arg_name}}}", str(default_val))
                    
                    output += f"```\n{cmd}\n```\n\n"
        
        # Add real-world APT usage
        if mitre_data['procedures']:
            output += "\n## Real-world APT Usage:\n\n"
            for proc in mitre_data['procedures'][:5]:  # Limit to 5
                output += f"- **{proc['actor']}**: {proc['description'][:200]}...\n"
        
        # Add detection methods
        if mitre_data['detection']:
            output += f"\n## Detection Methods:\n\n{mitre_data['detection'][:500]}...\n"
        
        # Add reference
        output += f"\n## Reference:\n- {mitre_data['url']}\n"
        
        return output
    
    def _generate_fallback_template(self, technique_id: str) -> str:
        """Template mặc định nếu không fetch được"""
        return f"""# {technique_id} - [Technique Name]

## Context:
[Describe what attackers do with this technique]

## Alternative Methods:

### 1. Standard execution
[command_1]
[command_2]

### 2. Obfuscated execution
[obfuscated_command]
%COMSPEC% /c [command]

### 3. Alternative tools
[alternative_tool_1]
[alternative_tool_2]

### 4. PowerShell equivalent
powershell -c "[command]"

### 5. Combined with payload
[command] && [malicious_action]

## Real-world Usage:
[Search APT reports for examples]

## Detection:
Monitor for:
- Execution of [binary]
- Command-line arguments containing [keywords]
"""


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-fetch MITRE ATT&CK + Atomic Red Team")
    parser.add_argument('-t', '--technique', required=True, help='Technique ID (e.g., T1036, T1548.002)')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    # Fetch data
    fetcher = MITREFetcher()
    mitre_techniques = fetcher.generate_mitre_techniques_section(args.technique)
    
    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(mitre_techniques)
        print(f"\n[✓] Saved to: {args.output}")
    else:
        print("\n" + "="*60)
        print(mitre_techniques)
        print("="*60)


if __name__ == "__main__":
    main()