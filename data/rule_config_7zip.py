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

tags="""
tags:
    - attack.t1036
    - attack.defense-evasion
"""