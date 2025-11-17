# minimizer.py
import subprocess
import time
import re
import os
from grammar_fuzzer import GrammarFuzzer

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

# grammar_fuzzer.py
# ...existing code...

from minimizer import TestCaseMinimizer

class GrammarFuzzer:
    def __init__(self, grammar_file):
        # ...existing code...
        self.minimizer = TestCaseMinimizer(self)
        self.path_coverage = {}
        self.rare_path_boost = 1.5

    # ...existing code...

    def main_loop(self):
        # ...existing code...
        
        # Lưu test case vào dict tạm để minimize sau
        pending_feedback[correlation_id] = {
            "path": path,
            "test_case": test_case
        }
        
        # ...existing code... (xử lý feedback)
        
        for cid, feedback_prio in self.feedback_cache.items():
            if cid in pending_feedback:
                data = pending_feedback[cid]
                path_to_update = data["path"]
                original_test_case = data["test_case"]
                
                if feedback_prio == PRIO_1_BYPASS_SUCCESS:
                    # Minimize
                    minimal = self.minimizer.minimize(original_test_case)
                    
                    # Lưu seed
                    seed_file = f"seeds/cmd_min_{int(time.time())}.txt"
                    with open(seed_file, 'w') as f:
                        f.write(minimal)
                    
                    # Thêm vào splice corpus
                    self.add_to_splice_corpus(minimal, feedback_prio)
                
                self.update_weights(path_to_update, feedback_prio)