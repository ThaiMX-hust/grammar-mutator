# tao_van_pham.py
# Script này CHỈ chứa logic, nó sẽ TẢI file cấu hình rule
# để tự động tạo file văn phạm (grammar).

import json
import os
import argparse  # <-- Thêm argparse để nhận file config
import importlib.util  # <-- Thêm importlib để tải file config
import sys

# (Giả sử file obfuscation_lib.py tồn tại)
from obfuscation_lib import get_string_obfuscations, get_wrappers, get_noise

def load_rule_config(config_file_path):
    """
    Tải động một file cấu hình rule (ví dụ: rule_config_7zip.py)
    """
    try:
        spec = importlib.util.spec_from_file_location("rule_config", config_file_path)
        if spec is None:
            raise FileNotFoundError(f"Không thể tìm thấy file cấu hình: {config_file_path}")
            
        rule_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rule_config)
        
        # Kiểm tra xem file config có đủ các biến cần thiết không
        if not hasattr(rule_config, 'rule_name') or \
           not hasattr(rule_config, 'sigma_detection') or \
           not hasattr(rule_config, 'mitre_techniques'):
            print(f"[LỖI] File cấu hình {config_file_path} thiếu các biến cần thiết.")
            return None
            
        return rule_config
        
    except Exception as e:
        print(f"[LỖI] Không thể tải file cấu hình {config_file_path}: {e}")
        return None

def main(config_path):
    # ---- BƯỚC 1: Tải Ngữ cảnh (Đã tách riêng) ----
    print(f"Đang tải cấu hình rule từ: {config_path}")
    config = load_rule_config(config_path)
    if config is None:
        return

    # Lấy dữ liệu từ file config đã tải
    rule_name = config.rule_name
    sigma_detection = config.sigma_detection
    mitre_techniques = config.mitre_techniques

    # ---- BƯỚC 2: Tạo Prompt cho LLM/Search ----
    # (Logic này giữ nguyên, giờ nó dùng các biến vừa tải)
    prompt = f"""
Hãy tạo một file văn phạm (grammar) định dạng JSON cho fuzzer,
dựa trên các thông tin sau:

1.  **Rule Sigma (detection):** {sigma_detection}
2.  **Kỹ thuật thay thế (MITRE):** {mitre_techniques}
3.  **Thư viện Wrapper (Python):** {get_wrappers()}
4.  **Thư viện Obfuscation (Python):** {get_string_obfuscations.__doc__}
5.  **Thư viện Noise (Python):** {get_noise()}

File JSON phải có 2 key: 'rules' và 'weights'.
- 'rules' định nghĩa cấu trúc (sequence hoặc terminal).
- 'weights' định nghĩa các lựa chọn (choice) và trọng số ban đầu (luôn là 1.0).

Văn phạm phải:
1.  **<start>**: Chọn 1 wrapper từ Thư viện Wrapper.
2.  **<payload>**: Chọn giữa <sigma_payload> (test từ khóa) VÀ <mitre_payload> (test logic).
3.  **<sigma_payload>**: Là một chuỗi chứa <7z_obf> VÀ <dmp_file> VÀ <noise>.
4.  **<7z_obf>**: Là lựa chọn giữa các biến thể làm rối của '7z.exe', '7zr.exe', '7za.exe'.
5.  **<mitre_payload>**: Là lựa chọn giữa 'makecab.exe ...' VÀ 'powershell.exe ...'.
"""

    # ---- BƯỚC 3: Gọi Tool (LLM / Google Search) ----
    print("Đang gọi LLM (mô phỏng bằng google_search) để tạo văn phạm...")
    print(f"Prompt (rút gọn): {prompt[:200]}...")

    # (Đây vẫn là dữ liệu JSON mô phỏng mà LLM trả về)
    simulated_llm_output = {
        "rules": {
            "<start>": "<wrapper_choice>",
            "<payload>": "<payload_choice>",
            "<sigma_payload>": "<7z_obf> a <noise> <dmp_file>",
            "<mitre_payload_cab>": "makecab.exe <dmp_file> archive.cab",
            "<mitre_payload_psh>": "powershell.exe -c \"[System.IO.Compression.ZipFile]::CreateFromDirectory('C:\\temp', 'archive.zip')\"",
            "<dmp_file>": "C:\\Windows\\Temp\\lsass.dmp"
        },
        "weights": {
            "<wrapper_choice>": {
                "cmd.exe /c <payload>": 1.0,
                "echo <payload> | cmd": 1.0,
                "%COMSPEC% /c <payload>": 1.0
            },
            "<payload_choice>": {
                "<sigma_payload>": 1.0,
                "<mitre_payload_cab>": 1.0,
                "<mitre_payload_psh>": 1.0
            },
            "<7z_obf>": {
                '"7z.exe"': 1.0, '"7Z.EXE"': 1.0, '"7z^.exe"': 1.0,
                '"7z""exe"': 1.0, '"7zr.exe"': 1.0, '"7za.exe"': 1.0
            },
            "<noise>": { '""': 1.0, '&::': 1.0 }
        }
    }

    # ---- BƯỚC 4: Lưu file Văn phạm (Dùng `rule_name`) ----
    
    # 1. Tạo tên thư mục (dùng biến `rule_name` từ file config)
    output_dir = f"{rule_name}_fuzz_data"

    # 2. Tạo thư mục này (nếu nó chưa tồn tại)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Đã đảm bảo thư mục tồn tại: {output_dir}")

    # 3. Tạo đường dẫn file văn phạm bên trong thư mục mới
    output_filepath = os.path.join(output_dir, "grammar.json")

    # 4. Lưu file JSON vào đường dẫn mới
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(simulated_llm_output, f, indent=4)

    print(f"Đã tạo file văn phạm tối ưu tại: {output_filepath}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tạo Văn phạm Fuzzing (Grammar Generator) từ file cấu hình Rule")
    parser.add_argument(
        "-c", "--config",
        type=str,
        required=True,
        help="Đường dẫn đến file cấu hình rule (ví dụ: rule_config_7zip.py)"
    )
    args = parser.parse_args()
    
    main(args.config)