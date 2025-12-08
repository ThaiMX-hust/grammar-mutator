# minimizer.py
import subprocess
import time
import re
import os


class TestCaseMinimizer:
    def __init__(self, fuzzer_instance):
        self.fuzzer = fuzzer_instance
    
    def tokenize(self, cmd):
        """Tách lệnh thành tokens"""
        pattern = r'("[^"]*"|\'[^\']*\'|[^\s]+)'
        return re.findall(pattern, cmd)
    
    def is_still_bypass(self, test_cmd):
        """Kiểm tra test case còn bypass không"""
        success, cid = self.fuzzer.execute_command(test_cmd)
        if not success:
            return False
        
        # Đợi Consumer kiểm tra (hoặc dùng API sync)
        time.sleep(10)
        
        # Kiểm tra feedback (đơn giản hóa)
        # Trong thực tế cần đọc feedback.txt hoặc query SIEM trực tiếp
        return True  # Placeholder
    
    def minimize(self, original_test_case):
        """
        Delta Debugging: Xóa dần các token cho đến khi không bypass
        """
        tokens = self.tokenize(original_test_case)
        minimal_tokens = tokens.copy()
        
        for i in range(len(tokens) - 1, 0, -1):  # Không xóa token đầu
            test_tokens = minimal_tokens[:i] + minimal_tokens[i+1:]
            test_cmd = " ".join(test_tokens)
            
            print(f"  [MIN] Thử xóa token {i}: {tokens[i]}")
            
            if self.is_still_bypass(test_cmd):
                minimal_tokens = test_tokens
                print(f"    -> Vẫn bypass, giữ version rút gọn")
            else:
                print(f"    -> Mất bypass, giữ token")
        
        return " ".join(minimal_tokens)

