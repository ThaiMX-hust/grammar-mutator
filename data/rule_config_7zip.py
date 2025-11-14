# Tên duy nhất cho rule, dùng để tạo thư mục
rule_name = "rule_7zip_compress_dump"

# Thông tin từ Rule Sigma "7Zip Compressing Dump Files"
sigma_detection = """
detection:
    selection_img:
        Image|endswith: ['\7z.exe', '\7zr.exe', '\7za.exe']
    selection_extension:
        CommandLine|contains: ['.dmp', '.dump', '.hdmp']
    condition: all of selection_*
"""

# Thông tin từ file T1560.001.md (từ tag)
mitre_techniques = """
- makecab.exe #{input_file} #{output_file}
- [System.IO.Compression.ZipFile]::CreateFromDirectory(...)
"""