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
from minimizer import TestCaseMinimizer

# --- Cấu hình ---
# (Lấy từ producer.py)
MUTATOR_DIR = "mutators" 
QUEUE_FILE = "queue.txt"
HASH_FILE = "tested_hashes.txt"
FEEDBACK_FILE = "feedback.txt"
TEMP_WORKDIR = "temp_workdirs"  
os.makedirs(TEMP_WORKDIR, exist_ok=True)

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

        # Thêm: Corpus lưu các test case thành công (để splice)
        self.splice_corpus = []  # Lưu các test case Prio 1/2
        
        # Khởi tạo TestCaseMinimizer
        self.minimizer = TestCaseMinimizer(self)
        self.path_coverage = {}
        self.rare_path_boost = 1.5

        print("Fuzzer đã sẵn sàng.")

    def load_mutators(self):
        """Tải các mutator từ MUTATOR_DIR"""
        try:
            from base_mutator import BaseMutator
        except ImportError:
            print("[ERROR] 'base_mutator.py' not found.")
            return {"generic": [], "cmd": [], "powershell": []}

        mutators = {"generic": [], "cmd": [], "powershell": []}
        mutator_files = list(Path(MUTATOR_DIR).glob("*.py"))

        for py_file in mutator_files:
            if py_file.name in ["__init__.py"]:
                continue

            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BaseMutator) and attr is not BaseMutator:
                        instance = attr()
                        for tag in instance.tags:
                            if tag in mutators:
                                mutators[tag].append(instance)
                                print(f"  [+] Loaded: {py_file.stem} (Tag: {tag})")
            except Exception as e:
                print(f"  [!] Error loading {py_file.name}: {e}")

        return mutators

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
        Thực thi lệnh và tạo thư mục temp theo ID
        """
        print(f"  [>] Đang thực thi: {command_string[:100]}...")
        correlation_id = str(uuid.uuid4())
        
        # Tạo thư mục tạm
        temp_dir_path = os.path.join(os.getcwd(), TEMP_WORKDIR, correlation_id)
        try:
            os.makedirs(temp_dir_path, exist_ok=True)
        except Exception as e:
            print(f"[ERROR] Could not create temp dir: {e}")
            return False, correlation_id
        
        try:
            result = subprocess.run(
                command_string, shell=True, capture_output=True, 
                text=True, timeout=10, encoding='utf-8',
                cwd=temp_dir_path
            )
            success = result.returncode == 0
        except Exception:
            success = False
        
        # Xóa thư mục tạm
        try:
            os.rmdir(temp_dir_path)
        except:
            pass
            
        return success, correlation_id

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

    def add_to_splice_corpus(self, test_case, priority):
        """Thêm test case thành công vào corpus để splice"""
        if priority in [PRIO_1_BYPASS_SUCCESS, PRIO_2_BYPASS_FAIL]:
            self.splice_corpus.append(test_case)
            # Giới hạn kích thước corpus
            if len(self.splice_corpus) > 100:
                self.splice_corpus.pop(0)  # Xóa test case cũ nhất
    
    def splice_test_cases(self, test_case_a, test_case_b):
        """
        Lai ghép 2 test case:
        1. Tách thành tokens (theo dấu cách, quotes, etc.)
        2. Lấy ngẫu nhiên phần từ A và B
        3. Ghép lại
        """
        # Tách thành tokens (giữ nguyên dấu ngoặc kép, quotes)
        def tokenize(cmd):
            # Regex để tách: giữ nguyên chuỗi trong "", '', và các ký tự đặc biệt
            pattern = r'("[^"]*"|\'[^\']*\'|[^\s]+)'
            return re.findall(pattern, cmd)
        
        tokens_a = tokenize(test_case_a)
        tokens_b = tokenize(test_case_b)
        
        if not tokens_a or not tokens_b:
            return test_case_a
        
        # Chọn ngẫu nhiên điểm cắt
        splice_point_a = random.randint(1, len(tokens_a) - 1)
        splice_point_b = random.randint(1, len(tokens_b) - 1)
        
        # Lai ghép: Lấy phần đầu của A + phần cuối của B
        spliced_tokens = tokens_a[:splice_point_a] + tokens_b[splice_point_b:]
        
        return " ".join(spliced_tokens)
    
    def generate_spliced_seed(self):
        """
        Sinh test case bằng Splicing nếu có đủ corpus
        """
        if len(self.splice_corpus) < 2:
            return None  # Không đủ test case để splice
        
        # Chọn ngẫu nhiên 2 test case
        test_case_a = random.choice(self.splice_corpus)
        test_case_b = random.choice(self.splice_corpus)
        
        if test_case_a == test_case_b:
            return None  # Tránh splice với chính nó
        
        spliced = self.splice_test_cases(test_case_a, test_case_b)
        print(f"  [SPLICE] {test_case_a[:30]}... + {test_case_b[:30]}...")
        return spliced

    def minimize_test_case(self, test_case, correlation_id):
        """
        Thu nhỏ test case bằng cách xóa từng phần tử và kiểm tra lại
        Chỉ áp dụng cho Prio 1 (Bypass thành công)
        """
        print(f"  [MIN] Đang thu nhỏ test case...")
        
        # Tokenize
        def tokenize(cmd):
            pattern = r'("[^"]*"|\'[^\']*\'|[^\s]+)'
            return re.findall(pattern, cmd)
        
        tokens = tokenize(test_case)
        if len(tokens) <= 2:  # Quá ngắn, không thu nhỏ
            return test_case
        
        minimal_tokens = tokens.copy()
        
        # Thử xóa từng token
        for i in range(len(tokens) - 1, -1, -1):  # Đi ngược từ cuối
            if i == 0:  # Không xóa token đầu (thường là wrapper)
                continue
                
            test_tokens = minimal_tokens[:i] + minimal_tokens[i+1:]
            test_cmd = " ".join(test_tokens)
            
            # Thực thi test
            success, temp_id = self.execute_command(test_cmd)
            
            # Đợi Consumer kiểm tra (ngắn hơn vòng lặp chính)
            time.sleep(5)
            
            # Kiểm tra SIEM
            # (Cần Consumer hỗ trợ API sync hoặc đọc feedback nhanh)
            # Giả sử: Nếu vẫn bypass thì giữ version rút gọn
            if success:  # Simplified check
                minimal_tokens = test_tokens
                print(f"    [-] Xóa token {i}: '{tokens[i]}' -> Vẫn bypass")
            else:
                print(f"    [+] Giữ token {i}: '{tokens[i]}' -> Cần thiết")
        
        minimal_cmd = " ".join(minimal_tokens)
        print(f"  [MIN] Kết quả: {test_case[:50]}... -> {minimal_cmd[:50]}...")
        return minimal_cmd

    def main_loop(self):
        """Vòng lặp fuzzing chính"""
        print(f"\n--- BẮT ĐẦU Fuzzing (PID: {os.getpid()}) ---")
        print(f"Theo dõi Queue: {QUEUE_FILE} | Phản hồi: {FEEDBACK_FILE}")
        
        pending_feedback = {}
        loop_count = 0

        while True:
            loop_count += 1
            
            # --- BƯỚC 1: SINH MẪU (Thêm Splicing) ---
            # 30% cơ hội splice nếu có corpus
            if random.random() < 0.3 and len(self.splice_corpus) >= 2:
                spliced_seed = self.generate_spliced_seed()
                if spliced_seed:
                    test_case = spliced_seed
                    path = ["<spliced>"]  # Đánh dấu là spliced
                else:
                    # Fallback sang grammar-based
                    (smart_seed, path) = self.generate_smart_seed()
                    test_case = self.apply_havoc_mutations(smart_seed)
            else:
                # Sinh từ grammar như cũ
                (smart_seed, path) = self.generate_smart_seed()
                test_case = self.apply_havoc_mutations(smart_seed)

            # --- BƯỚC 3: CHECK HASH & THỰC THI ---
            cmd_hash = hashlib.sha256(test_case.encode()).hexdigest()
            if cmd_hash in self.tested_hashes:
                continue 
            
            self.tested_hashes.add(cmd_hash)
            self.hash_file_handle.write(f"{cmd_hash}\n")
            self.hash_file_handle.flush()
            
            run_success, correlation_id = self.execute_command(test_case)
            
            # --- BƯỚC 4: GHI VÀO QUEUE ---
            with open(QUEUE_FILE, 'a', encoding='utf-8') as qf:
                qf.write(f"{correlation_id}|{run_success}|cmd|{test_case}\n")
            
            # Lưu test case vào dict tạm để minimize sau
            pending_feedback[correlation_id] = {
                "path": path,
                "test_case": test_case
            }
            
            # --- BƯỚC 5: KIỂM TRA PHẢN HỒI ---
            self.check_for_feedback()
            
            # Xử lý các phản hồi
            ids_to_remove = []
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
                    del pending_feedback[cid]
                    ids_to_remove.append(cid)
            
            for cid in ids_to_remove:
                del self.feedback_cache[cid]

            # --- BƯỚC 7: LƯU TRỌNG SỐ ---
            if loop_count % 100 == 0:
                print(f"  [i] Đã chạy {loop_count} vòng. Đang lưu trọng số...")
                print(f"  [i] Splice Corpus: {len(self.splice_corpus)} test cases")
                self.save_weights()

                time.sleep(0.01) # Có thể thêm sleep nếu cần

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