# ky_thuat_obfuscation.py
# Đây là thư viện kỹ thuật né tránh mà bạn (con người) duy trì.
# LLM sẽ sử dụng logic này để xây dựng các quy tắc văn phạm.

def get_string_obfuscations(keyword):
    """
    Trả về một danh sách các biến thể làm rối của một từ khóa cho CMD.
    """
    if not keyword:
        return '""'  # Trả về chuỗi rỗng nếu không có từ khóa

    variants = [
        f'"{keyword}"',  # Chuỗi gốc trong dấu ngoặc kép
        f'"{keyword.upper()}"',  # In hoa
        f'"{keyword.lower()}"',  # In thường
    ]
    
    # Kỹ thuật chèn Caret (^)
    if len(keyword) > 2:
        variants.append(f'"{keyword[0] + "^" + keyword[1:]}"')
    
    # Kỹ thuật chèn chuỗi rỗng ("")
    if len(keyword) > 3:
        variants.append(f'"{keyword[:2]}""{keyword[2:]}"')

    # Kỹ thuật nối chuỗi CMD (&)
    if len(keyword) > 3:
        variants.append(f'"{keyword[:2]}"&"{keyword[2:]}"')
        
    # Kỹ thuật dùng biến môi trường (ví dụ: %COMSPEC% -> cmd.exe)
    if keyword.lower() == 'cmd.exe':
         variants.append('"%COMSPEC%"')
         
    return variants

def get_wrappers():
    """
    Trả về các 'vỏ bọc' (wrappers) để chạy lệnh payload.
    Lưu ý: '{}' là nơi payload sẽ được chèn vào.
    """
    return [
        "cmd.exe /c {}",
        "cmd.exe /r {}", # Tương tự /c
        "echo {} | cmd",
        "%COMSPEC% /c {}",
        "cmd < {}" # Yêu cầu payload được ghi vào file tạm
    ]

def get_noise():
    """
    Trả về các kỹ thuật "gây nhiễu" (noise)
    để chèn vào giữa các lệnh.
    """
    return [
        '""',    # Chuỗi rỗng
        '&::',   # Comment
        'REM rác' # Comment
    ]