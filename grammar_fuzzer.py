# grammar_fuzzer.py
# Fuzzer "Lai" (Hybrid) có Hướng dẫn (Guided)
# Thay thế cho producer.py

import os
import subprocess
import random
import time
import importlib.util
from pathlib import Path
import hashlib
import uuid
import argparse
import json
import re

# --- Cấu hình ---
# (Lấy từ producer.py)
MUTATOR_DIR = "mutators" 
QUEUE_FILE = "queue.txt"
HASH_FILE = "tested_hashes.txt"
FEEDBACK_FILE = "feedback.txt" # File Consumer sẽ ghi phản hồi Prio

# --- Priority Flags ---
# (Lấy từ producer.py)
PRIO_1_BYPASS_SUCCESS = "Prio 1"
PRIO_2_BYPASS_FAIL = "Prio 2"
PRIO_3_DETECTED_OR_ERROR = "Prio 3"

class GrammarFuzzer:
    def __init__(self, grammar_file):
        print(f"Khởi tạo Fuzzer với văn phạm: {grammar_file}")
        self.grammar_file = grammar_file
        try:
            with open(grammar_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.rules = data['rules']     # Dict các quy tắc (sequences)
                self.weights = data['weights'] # Dict các lựa chọn (choices)
        except Exception as e:
            print(f"[LỖI] Không thể tải file văn phạm: {e}")
            exit(1)

        # Tải các mutator cũ (Havoc)
        self.mutators = self.load_mutators()
        
        # Tải "bộ nhớ" hash
        self.tested_hashes = set()
        if os.path.exists(HASH_FILE):
            with open(HASH_FILE, 'r') as f:
                self.tested_hashes = set(line.strip() for line in f)
        self.hash_file_handle = open(HASH_FILE, 'a')
        
        # Mở file feedback để đọc
        if not os.path.exists(FEEDBACK_FILE):
            open(FEEDBACK_FILE, 'w').close() # Tạo file nếu chưa có
        self.feedback_handle = open(FEEDBACK_FILE, 'r')
        self.feedback_cache = {} # Lưu feedback đã đọc
        print("Fuzzer đã sẵn sàng.")

    def load_mutators(self):
        # (Logic này lấy từ producer.py)
        # ... (Giả sử hàm này tải các mutator từ MUTATOR_DIR) ...
        print(f"Đã tải {len(self.mutators.get('generic', []))} mutator 'Havoc'")
        # Tải BaseMutator
        # Tải PowerShellConcat
        # ... (Code đầy đủ của hàm load_mutators) ...
        return {"generic": [], "cmd": [], "powershell": []} # Giả lập

    def _weighted_choice(self, parent_rule_name):
        """Chọn 1 quy tắc con dựa trên trọng số (weights)"""
        choices_weights = self.weights[parent_rule_name]
        choices = list(choices_weights.keys())
        weights = list(choices_weights.values())
        
        # Đảm bảo trọng số không âm
        min_weight = min(weights)
        if min_weight < 0:
            weights = [w - min_weight + 0.01 for w in weights]
            
        return random.choices(choices, weights=weights, k=1)[0]

    def generate_smart_seed(self, current_rule_name="<start>"):
        """
        Đệ quy sinh mẫu từ văn phạm.
        Trả về: (generated_string, path_list)
        """
        
        # 1. Nếu là một LỰA CHỌN (có trong weights)
        if current_rule_name in self.weights:
            chosen_rule = self._weighted_choice(current_rule_name)
            (child_string, child_path) = self.generate_smart_seed(chosen_rule)
            return (child_string, [current_rule_name] + child_path)

        # 2. Nếu là một CHUỖI QUY TẮC (có trong rules)
        if current_rule_name in self.rules:
            rule_sequence = self.rules[current_rule_name]
            
            # Tìm tất cả các <tag> trong chuỗi
            parts_to_expand = re.findall(r"(<[^>]+>)", rule_sequence)
            
            if not parts_to_expand: # Không có gì để mở rộng, là 1 chuỗi lá
                return (rule_sequence, [current_rule_name])

            generated_string = rule_sequence
            generated_path = [current_rule_name]
            
            for part in parts_to_expand:
                (child_string, child_path) = self.generate_smart_seed(part)
                # Thay thế <tag> bằng chuỗi đã sinh
                generated_string = generated_string.replace(part, child_string, 1)
                generated_path.extend(child_path)
                
            return (generated_string, generated_path)
            
        # 3. Nếu là một NÚT LÁ (Terminal - không có trong rules/weights)
        # (Ví dụ: "cmd.exe /c <payload>" sau khi <payload> được thay thế)
        return (current_rule_name, [current_rule_name])


    def apply_havoc_mutations(self, command):
        """
        Áp dụng các đột biến "Havoc" (từ mutator cũ)
        lên "Smart Seed" (từ văn phạm).
        """
        # (Logic này lấy từ producer.py)
        # ... (Giả sử hàm này chọn ngẫu nhiên 1 mutator và chạy) ...
        # Ví dụ: if random.random() < 0.1: ...
        return command # Tạm thời bỏ qua bước này cho đơn giản

    def execute_command(self, command_string):
        """
        Thực thi lệnh. (Lấy từ producer.py)
        """
        # print(f"  [>] Đang thực thi: {command_string[:100]}...")
        try:
            result = subprocess.run(
                command_string, shell=True, capture_output=True, 
                text=True, timeout=10, encoding='utf-8'
            )
            return result.returncode == 0
        except Exception:
            return False

    def update_weights(self, path, feedback):
        """Cập nhật trọng số (weights) dựa trên Prio 1/2/3"""
        print(f"  [i] Học hỏi: {feedback} cho đường đi {path[0]} -> {path[-1]}")
        
        # Định nghĩa hệ số học
        ADJUSTMENT_FACTORS = {
            PRIO_1_BYPASS_SUCCESS: 1.2, # Thưởng 20%
            PRIO_2_BYPASS_FAIL: 0.9,    # Phạt nhẹ 10%
            PRIO_3_DETECTED_OR_ERROR: 0.8 # Phạt nặng 20%
        }
        factor = ADJUSTMENT_FACTORS.get(feedback, 1.0)
        
        if factor == 1.0:
            return # Không học gì

        # Lặp qua đường đi để cập nhật
        for i in range(len(path) - 1):
            parent = path[i]
            child = path[i+1]
            
            if parent in self.weights and child in self.weights[parent]:
                current_weight = self.weights[parent][child]
                self.weights[parent][child] = max(0.01, current_weight * factor) # Đảm bảo không về 0

        # Chuẩn hóa (normalize) các trọng số đã bị thay đổi
        self._normalize_weights(path)
        
    def _normalize_weights(self, path):
        """Chuẩn hóa lại trọng số để tổng là 1.0"""
        updated_parents = {path[i] for i in range(len(path) - 1) if path[i] in self.weights}
        
        for parent in updated_parents:
            choices = self.weights[parent]
            total_weight = sum(choices.values())
            
            if total_weight == 0: continue
            
            for choice in choices:
                choices[choice] = choices[choice] / total_weight

    def save_weights(self):
        """Lưu trọng số đã học được vào file JSON"""
        try:
            data = {"rules": self.rules, "weights": self.weights}
            with open(self.grammar_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[LỖI] Không thể lưu trọng số: {e}")

    def check_for_feedback(self):
        """Đọc file FEEDBACK_FILE để học hỏi"""
        new_lines = self.feedback_handle.readlines()
        if not new_lines:
            return
            
        for line in new_lines:
            if line.strip():
                try:
                    correlation_id, feedback_prio = line.strip().split('|')
                    self.feedback_cache[correlation_id] = feedback_prio
                except Exception:
                    pass # Bỏ qua dòng lỗi

    def main_loop(self):
        """Vòng lặp fuzzing chính"""
        print(f"\n--- BẮT ĐẦU Fuzzing (PID: {os.getpid()}) ---")
        print(f"Theo dõi Queue: {QUEUE_FILE} | Phản hồi: {FEEDBACK_FILE}")
        
        # Lưu trữ các "đường đi" (path) đang chờ phản hồi
        pending_feedback = {} # {correlation_id: path}
        loop_count = 0

        while True:
            loop_count += 1
            
            # --- BƯỚC 1: SINH MẪU ---
            (smart_seed, path) = self.generate_smart_seed()
            
            # --- BƯỚC 2: ĐỘT BIẾN "LAI" (HYBRID) ---
            test_case = self.apply_havoc_mutations(smart_seed)

            # --- BƯỚC 3: CHECK HASH & THỰC THI ---
            # (Logic từ producer.py)
            cmd_hash = hashlib.sha256(test_case.encode()).hexdigest()
            if cmd_hash in self.tested_hashes:
                continue 
            
            self.tested_hashes.add(cmd_hash)
            self.hash_file_handle.write(f"{cmd_hash}\n")
            self.hash_file_handle.flush()
            
            correlation_id = str(uuid.uuid4())
            run_success = self.execute_command(test_case)
            
            # --- BƯỚC 4: GHI VÀO QUEUE ---
            # (Logic từ producer.py)
            with open(QUEUE_FILE, 'a', encoding='utf-8') as qf:
                qf.write(f"{correlation_id}|{run_success}|cmd|{test_case}\n")
            
            # Lưu lại path để chờ phản hồi
            pending_feedback[correlation_id] = path
            
            # --- BƯỚC 5: KIỂM TRA PHẢN HỒI (HỌC HỎI) ---
            self.check_for_feedback()
            
            # Xử lý các phản hồi đã nhận được
            ids_to_remove = []
            for cid, feedback_prio in self.feedback_cache.items():
                if cid in pending_feedback:
                    path_to_update = pending_feedback[cid]
                    # --- BƯỚC 6: CẬP NHẬT TRỌNG SỐ ---
                    self.update_weights(path_to_update, feedback_prio)
                    
                    del pending_feedback[cid]
                    ids_to_remove.append(cid)
            
            # Xóa cache đã xử lý
            for cid in ids_to_remove:
                del self.feedback_cache[cid]

            # --- BƯỚC 7: LƯU TRỌNG SỐ (Định kỳ) ---
            if loop_count % 100 == 0:
                print(f"  [i] Đã chạy {loop_count} vòng. Đang lưu trọng số...")
                self.save_weights()
            
            # time.sleep(0.01) # Có thể thêm sleep nếu cần

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grammar Fuzzer (thay thế producer.py)")
    parser.add_argument(
        "-g", "--grammar",
        type=str,
        default="grammar-rule-7zip.json",
        help="File văn phạm JSON (được tạo bởi LLM)"
    )
    args = parser.parse_args()

    fuzzer = None
    try:
        fuzzer = GrammarFuzzer(grammar_file=args.grammar)
        fuzzer.main_loop()
    except KeyboardInterrupt:
        print("\n[!] Fuzzer đang dừng...")
    finally:
        if fuzzer:
            print("[i] Đang lưu trạng thái trọng số cuối cùng...")
            fuzzer.save_weights()
            fuzzer.hash_file_handle.close()
            fuzzer.feedback_handle.close()
            print("[i] Đã đóng file. Tạm biệt.")