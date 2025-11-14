# tao_van_pham.py
# Script này CHỈ chứa logic, nó sẽ TẢI file cấu hình rule
# để tự động tạo file văn phạm (grammar).

import json
import os
import argparse
import importlib.util
from obfuscation_lib import get_string_obfuscations, get_wrappers, get_noise

def load_rule_config(config_file_path):
    """Tải động file cấu hình rule"""
    try:
        spec = importlib.util.spec_from_file_location("rule_config", config_file_path)
        if spec is None:
            raise FileNotFoundError(f"Không thể tìm thấy file cấu hình: {config_file_path}")
            
        rule_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rule_config)
        
        if not hasattr(rule_config, 'rule_name') or \
           not hasattr(rule_config, 'sigma_detection') or \
           not hasattr(rule_config, 'mitre_techniques'):
            print(f"[LỖI] File cấu hình {config_file_path} thiếu các biến cần thiết.")
            return None
            
        return rule_config
        
    except Exception as e:
        print(f"[LỖI] Không thể tải file cấu hình {config_file_path}: {e}")
        return None

def generate_prompt(config):
    """Tạo prompt cho Gemini dựa trên cấu hình rule"""
    rule_name = config.rule_name
    sigma_detection = config.sigma_detection
    mitre_techniques = config.mitre_techniques
    
    wrappers = get_wrappers()
    noise = get_noise()
    
    # Tạo ví dụ obfuscation
    obfuscation_examples = get_string_obfuscations("7z.exe")
    
    prompt = f"""
Bạn là một chuyên gia về an ninh mạng (offensive security) và là một kỹ sư fuzzing.
Nhiệm vụ của bạn là tạo ra một file văn phạm (grammar) JSON tập trung cao độ (highly-focused) để bypass một rule SIEM cụ thể.

Đây là toàn bộ thông tin đầu vào của bạn:
---

### 1. Rule Name:
{rule_name}

### 2. Rule Sigma (Detection Logic):
{sigma_detection}

### 3. Kỹ thuật thay thế (MITRE Techniques):
{mitre_techniques}
### 4. Thư viện Kỹ thuật (Primitives):

#### Wrappers (Vỏ bọc)
{json.dumps(wrappers, indent=2, ensure_ascii=False)}

#### Obfuscation (Ví dụ làm rối cho 'some_keyword'):
{json.dumps(obfuscation_examples, indent=2, ensure_ascii=False)}

#### Noise (Gây nhiễu):
{json.dumps(noise, indent=2, ensure_ascii=False)}

---

### YÊU CẦU:

Dựa trên các thông tin trên, hãy **TỰ ĐỘNG PHÂN TÍCH** các từ khóa (keywords) và logic, sau đó **TẠO RA** một file văn phạm JSON hoàn chỉnh.

File văn phạm PHẢI tuân thủ các logic sau:

1.  **Cấu trúc file:** JSON phải có 2 key chính: "rules" và "weights".
2.  **Quy tắc Gốc (<start>):** Phải là một lựa chọn (trong 'weights') tên là "<wrapper_choice>", bao gồm TẤT CẢ các wrapper trong thư viện. Quy tắc "rules" `<start>` sẽ trỏ đến "<wrapper_choice>".
3.  **Quy tắc Logic (<payload>):** Phải có một lựa chọn tên là "<payload_choice>" (trong 'weights') cho phép fuzzer chọn giữa:
    * "<sigma_payload>" (để tấn công các từ khóa của Rule Sigma)
    * "<mitre_payload>" (để tấn công logic bằng các kỹ thuật thay thế)
4.  **Quy tắc Sigma (<sigma_payload>):**
    * **Phân tích** 'Rule Sigma (Detection)' để tìm các TỪ KHÓA (ví dụ: '7z.exe', '.dmp') và LOGIC (ví dụ: 'all of', 'contains', 'endswith').
    * **Tạo** các quy tắc lựa chọn (ví dụ: "<obf_7z_exe>", "<obf_dmp>") cho TỪNG TỪ KHÓA bạn tìm thấy, sử dụng logic từ 'Thư viện Obfuscation'.
    * **Tạo** quy tắc sequence "<sigma_payload>" để kết hợp các quy tắc obfuscation này và 'Thư viện Noise' theo đúng 'LOGIC' (ví dụ: "all of" nghĩa là phải có cả hai).
5.  **Quy tắc MITRE (<mitre_payload>):**
    * **Phân tích** 'MITRE Techniques' để tìm các LỆNH thay thế (ví dụ: 'makecab.exe ...', 'powershell.exe...Compression.ZipFile').
    * **Tạo** một lựa chọn (trong 'weights') tên là "<mitre_choice>" để fuzzer chọn một trong các lệnh này. Quy tắc "rules" `<mitre_payload>` sẽ trỏ đến "<mitre_choice>".
6.  **Trọng số (Weights):** Tất cả các lựa chọn ban đầu phải có trọng số là `1.0`.
7.  **Tính Sáng tạo (Quan trọng):** Dựa trên logic của 'Thư viện Obfuscation', hãy **tự mình đề xuất thêm 1-2 biến thể obfuscation mới** (ví dụ: dùng biến môi trường như `%COMSPEC%`) và thêm chúng vào các quy tắc lựa chọn (choice) có liên quan.

---
### OUTPUT (CHỈ JSON):

Chỉ trả về nội dung file JSON. Không giải thích. Không viết gì khác..
### ĐẦU RA JSON MẪU (ONE-SHOT EXAMPLE)

Đây là file JSON đầu ra "chuẩn" cho ví dụ trên:

```json
{{
  "rules": {{
    "<start>": "<wrapper_choice>",
    "<payload>": "<sigma_payload>",
    "<sigma_payload>": "<obf_whoami>"
  }},
  "weights": {{
    "<wrapper_choice>": {{
      "cmd.exe /c <payload>": 1.0,
      "echo <payload> | cmd": 1.0
    }},
    "<obf_whoami>": {{
      "\\"whoami.exe\\"": 1.0,
      "\\"WHOAMI.EXE\\"": 1.0,
      "\\"who^ami.exe\\"": 1.0,
      "\\"who\\"\\"ami.exe\\"": 1.0
    }}
  }}
}}
```
"""
    return prompt.strip()

def main(config_path):
    print(f"Đang tải cấu hình rule từ: {config_path}")
    config = load_rule_config(config_path)
    if config is None:
        return

    # Tạo prompt
    prompt = generate_prompt(config)
    
    # Tạo thư mục output
    output_dir = f"{config.rule_name}_fuzz_data"
    os.makedirs(output_dir, exist_ok=True)
    
    # Lưu prompt vào file
    prompt_filepath = os.path.join(output_dir, "prompt.txt")
    with open(prompt_filepath, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"✓ Đã tạo prompt tại: {prompt_filepath}")
    print(f"\n--- PROMPT CONTENT ---\n{prompt}\n--- END PROMPT ---")
    print(f"\nHãy copy prompt trên lên Gemini Web GUI để tạo grammar.json")
    print(f"Sau đó lưu kết quả vào: {os.path.join(output_dir, 'grammar.json')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tạo Prompt cho Gemini từ file cấu hình Rule")
    parser.add_argument(
        "-c", "--config",
        type=str,
        required=True,
        help="Đường dẫn đến file cấu hình rule (ví dụ: data/rule_config_7zip.py)"
    )
    args = parser.parse_args()
    
    main(args.config)