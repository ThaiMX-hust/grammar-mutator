# tao_van_pham.py
# Script này CHỈ chứa logic, nó sẽ TẢI file cấu hình rule
# để tự động tạo file văn phạm (grammar).

import json
import os
import sys
import argparse
import importlib.util
import re
from pathlib import Path

def load_rule_config(config_file_path):
    """Tải động file cấu hình rule"""
    try:
        spec = importlib.util.spec_from_file_location("config", config_file_path)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        return config
    except SyntaxError as e:
        print(f"[LỖI] Syntax error trong file config: {e}")
        print(f"[HINT] Hãy thêm 'r' trước triple-quoted strings:")
        print(f"       sigma_detection = r\"\"\"...\"\"\"")
        sys.exit(1)
    except Exception as e:
        print(f"[LỖI] Không thể tải file cấu hình: {e}")
        sys.exit(1)

def extract_keywords_from_sigma(sigma_detection: str) -> dict:
    """
    Trích xuất keywords từ Sigma detection logic
    
    Returns:
        dict: {
            'exact_keywords': ['keyword1', 'keyword2'],
            'regex_patterns': [r'\d+', r'[a-z]+'],
            'logic': 'contains|all' | 'contains' | 'endswith'
        }
    """
    keywords = {
        'exact_keywords': [],
        'regex_patterns': [],
        'logic': 'contains'
    }
    
    # Extract logic type
    if 'contains|all' in sigma_detection:
        keywords['logic'] = 'contains|all'
    elif 'endswith' in sigma_detection:
        keywords['logic'] = 'endswith'
    
    # Extract exact keywords (strings in quotes)
    exact_matches = re.findall(r"['\"]([^'\"]+)['\"]", sigma_detection)
    keywords['exact_keywords'] = [k.strip() for k in exact_matches if k.strip() and not k.startswith('#')]
    
    return keywords

def generate_obfuscation_rules(keyword: str) -> dict:
    """
    Tạo các rule obfuscation cho 1 keyword
    
    Returns:
        dict: {
            'node_name': '<obf_keyword>',
            'weights': {
                'original': 0.3,
                'uppercase': 0.2,
                ...
            }
        }
    """
    # Sanitize keyword cho node name
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', keyword.lower())
    node_name = f"<obf_{safe_name}>"
    
    weights = {
        keyword: 0.3,                           # Original
        keyword.upper(): 0.2,                   # UPPERCASE
        keyword.title(): 0.15,                  # Title Case
    }
    
    # CMD caret obfuscation
    if len(keyword) > 2:
        mid = len(keyword) // 2
        weights[f"{keyword[:mid]}^{keyword[mid:]}"] = 0.15
    
    # PowerShell string concat
    if len(keyword) > 3:
        mid = len(keyword) // 2
        weights[f"('{keyword[:mid]}'+'{keyword[mid:]}')"] = 0.1
    
    # Quoted
    weights[f'"{keyword}"'] = 0.1
    
    return {
        'node_name': node_name,
        'weights': weights
    }

def generate_prompt(config, auto_fetch=False):
    """Tạo prompt cho Gemini dựa trên cấu hình rule"""
    rule_name = config.rule_name
    sigma_detection = config.sigma_detection
    mitre_techniques = getattr(config, 'mitre_techniques', '')
    
    # Extract keywords from Sigma
    sigma_info = extract_keywords_from_sigma(sigma_detection)
    keywords = sigma_info['exact_keywords']
    
    print(f"\n[i] Extracted keywords: {keywords}")
    
    # Generate obfuscation rules for each keyword
    obf_rules = []
    for keyword in keywords[:5]:  # Limit to 5 keywords
        obf_rule = generate_obfuscation_rules(keyword)
        obf_rules.append(obf_rule)
    
    # Build sigma_payload structure
    sigma_payload_parts = []
    for obf_rule in obf_rules:
        sigma_payload_parts.append(obf_rule['node_name'])
    
    sigma_payload_template = " ".join(sigma_payload_parts)
    
    prompt = f"""
Bạn là chuyên gia tạo grammar JSON cho fuzzer. Hãy tạo file grammar ĐÚNG CẤU TRÚC sau:

=== RULE NAME ===
{rule_name}

=== SIGMA DETECTION ===
{sigma_detection}

=== EXTRACTED KEYWORDS ===
{', '.join(keywords)}

=== MITRE ATT&CK TECHNIQUES ===
{mitre_techniques[:1000]}...

=== CẤU TRÚC GRAMMAR YÊU CẦU ===

**QUAN TRỌNG:** Tránh vòng lặp vô hạn!

```json
{{
  "rules": {{
    "<start>": "<wrapper>",
    "<sigma_payload>": "{sigma_payload_template}",
    "<mitre_payload>": "<mitre_choice>"
  }},
  "weights": {{
    "<wrapper>": {{
      "cmd.exe /c <payload>": 0.2,
      "echo <payload> | cmd": 0.2,
      "%COMSPEC% /c <payload>": 0.2,
      "powershell -c <payload>": 0.2,
      "<payload>": 0.2
    }},
    "<payload>": {{
      "<sigma_payload>": 0.6,
      "<mitre_payload>": 0.4
    }},
```
Tiếp tục với:
{chr(10).join([f'    "{obf_rule["node_name"]}": {{ ... }},' for obf_rule in obf_rules])}
    "<mitre_choice>": {{
      "alternative_technique_1": 0.3,
      "alternative_technique_2": 0.3,
      "alternative_technique_3": 0.2,
      "alternative_technique_4": 0.2
    }}
  }}
}}
```

=== QUY TẮC BẮT BUỘC ===
1. **KHÔNG tạo node trùng tên** giữa "rules" và "weights"
2. **Tổng weights trong mỗi node = 1.0**
3. **Sigma payload**: Obfuscate các keywords từ Sigma detection
4. **MITRE payload**: Alternative techniques từ MITRE ATT&CK (4-5 techniques)
5. **Wrapper**: Các cách execute command (cmd, powershell, echo, %COMSPEC%)
6. **Không dùng node <noise>** - đơn giản hóa

=== VÍ DỤ OBFUSCATION CHO KEYWORD "{keywords[0] if keywords else 'example'}" ===

{obf_rules[0]['weights'] if obf_rules else {}}

=== OUTPUT ===
Trả về JSON HOÀN CHỈNH, không markdown, không giải thích.
"""
    
    return prompt

def main(config_path, auto_fetch=False):
    """Main function"""
    # Load config
    config = load_rule_config(config_path)
    
    # Create output directory
    output_dir = Path(f"{config.rule_name}_fuzz_data")
    output_dir.mkdir(exist_ok=True)
    
    # Generate prompt
    prompt = generate_prompt(config, auto_fetch=auto_fetch)
    
    # Save prompt
    prompt_file = output_dir / "prompt.txt"
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"\n[✓] Đã tạo prompt tại: {prompt_file}")
    print(f"\n[i] Copy prompt vào Gemini để tạo grammar.json")
    print(f"[i] Lưu kết quả vào: {output_dir / 'grammar.json'}")
    print(f"\n=== CHECKLIST ===")
    print(f"  [ ] Copy prompt từ {prompt_file}")
    print(f"  [ ] Paste vào Gemini Web")
    print(f"  [ ] Lưu JSON output vào {output_dir / 'grammar.json'}")
    print(f"  [ ] Validate JSON: python -m json.tool {output_dir / 'grammar.json'}")
    print(f"  [ ] Chạy fuzzer: python grammar_fuzzer.py -g {output_dir / 'grammar.json'}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate grammar prompt from Sigma rule config")
    parser.add_argument('-c', '--config', required=True, help='Path to rule config file')
    parser.add_argument('--auto-fetch', action='store_true', help='Auto-fetch mitre_techniques')
    
    args = parser.parse_args()
    
    main(args.config, auto_fetch=args.auto_fetch)