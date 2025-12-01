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
OUTPUT_DIR = "fuzzer_output"  # Thư mục lưu test cases
HASH_FILE = "tested_hashes.txt"
TEMP_WORKDIR = "temp_workdirs"  
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_WORKDIR, exist_ok=True)

# --- Metrics ---
class FuzzerMetrics:
    def __init__(self):
        self.total_generated = 0
        self.unique_generated = 0
        self.grammar_based = 0
        self.spliced = 0
        self.execution_success = 0
        self.execution_failed = 0
        self.start_time = time.time()
    
    def report(self):
        elapsed = time.time() - self.start_time
        rate = self.total_generated / elapsed if elapsed > 0 else 0
        return f"""
--- FUZZER METRICS ---
Total: {self.total_generated} | Unique: {self.unique_generated} | Rate: {rate:.2f}/s
Grammar: {self.grammar_based} | Spliced: {self.spliced}
Exec OK: {self.execution_success} | Failed: {self.execution_failed}
Runtime: {elapsed:.2f}s
"""

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
        
        # Corpus lưu các test case thành công (để splice)
        self.splice_corpus = []  # Lưu test cases đã execute thành công
        self.max_corpus_size = 200  # Tăng corpus size
        
        # Metrics tracking
        self.metrics = FuzzerMetrics()
        
        # Output file handle
        self.output_file = os.path.join(OUTPUT_DIR, f"testcases_{int(time.time())}.txt")
        self.output_handle = open(self.output_file, 'w', encoding='utf-8')
        
        print("Fuzzer đã sẵn sàng.")
        print(f"Output: {self.output_file}")

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
        """Chọn 1 quy tắc con dựa trên trọng số (weights) với exploration boost"""
        choices_weights = self.weights[parent_rule_name]
        choices = list(choices_weights.keys())
        weights = list(choices_weights.values())
        
        # Đảm bảo trọng số không âm
        min_weight = min(weights)
        if min_weight < 0:
            weights = [w - min_weight + 0.01 for w in weights]
        
        # 10% cơ hội chọn ngẫu nhiên hoàn toàn (exploration)
        if random.random() < 0.1:
            return random.choice(choices)
            
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
        # 30% cơ hội mutation
        if random.random() > 0.3 or not self.mutators:
            return command
        
        # Chọn ngẫu nhiên tag (cmd, powershell, generic)
        available_tags = [tag for tag in self.mutators if self.mutators[tag]]
        if not available_tags:
            return command
        
        tag = random.choice(available_tags)
        mutator_list = self.mutators[tag]
        
        # Áp dụng 1-2 mutators
        num_mutations = random.randint(1, 2)
        mutated = command
        
        for _ in range(num_mutations):
            mutator = random.choice(mutator_list)
            try:
                mutated = mutator.mutate(mutated)
            except Exception as e:
                pass  # Bỏ qua lỗi mutation
        
        return mutated

    def execute_command(self, command_string):
        """
        Dry-run: Chỉ validate syntax, không thực thi thật
        (Để tăng tốc độ sinh test cases)
        """
        correlation_id = str(uuid.uuid4())
        
        # Validation đơn giản: kiểm tra độ dài và ký tự cơ bản
        if len(command_string) < 3 or len(command_string) > 8000:
            return False, correlation_id
        
        # Giả lập thành công (để thêm vào splice corpus)
        # Trong thực tế có thể thêm syntax validation
        success = True
        
        return success, correlation_id

    def add_to_splice_corpus(self, test_case):
        """Thêm test case vào corpus để splice"""
        if test_case and len(test_case) > 5:
            self.splice_corpus.append(test_case)
            # Giới hạn kích thước corpus
            if len(self.splice_corpus) > self.max_corpus_size:
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

    def main_loop(self):
        """Vòng lặp fuzzing chính - Tập trung sinh test cases"""
        print(f"\n--- BẮT ĐẦU Fuzzing (PID: {os.getpid()}) ---")
        print(f"Output: {self.output_file}")
        print("[!] Chạy trong chế độ tối ưu (không SIEM)\n")
        
        loop_count = 0

        try:
            while True:
                loop_count += 1
                self.metrics.total_generated += 1
                
                # --- BƯỚC 1: SINH TEST CASE ---
                # 20% cơ hội splice nếu có corpus (giảm từ 30%)
                if random.random() < 0.2 and len(self.splice_corpus) >= 2:
                    spliced_seed = self.generate_spliced_seed()
                    if spliced_seed:
                        test_case = spliced_seed
                        self.metrics.spliced += 1
                    else:
                        # Fallback sang grammar-based
                        (smart_seed, path) = self.generate_smart_seed()
                        test_case = self.apply_havoc_mutations(smart_seed)
                        self.metrics.grammar_based += 1
                else:
                    # Sinh từ grammar
                    (smart_seed, path) = self.generate_smart_seed()
                    test_case = self.apply_havoc_mutations(smart_seed)
                    self.metrics.grammar_based += 1

                # --- BƯỚC 2: DEDUP ---
                cmd_hash = hashlib.sha256(test_case.encode()).hexdigest()
                if cmd_hash in self.tested_hashes:
                    continue 
                
                self.tested_hashes.add(cmd_hash)
                self.hash_file_handle.write(f"{cmd_hash}\n")
                self.metrics.unique_generated += 1
                
                # --- BƯỚC 3: VALIDATE (Dry-run) ---
                run_success, correlation_id = self.execute_command(test_case)
                
                if run_success:
                    self.metrics.execution_success += 1
                    # Thêm vào splice corpus
                    self.add_to_splice_corpus(test_case)
                else:
                    self.metrics.execution_failed += 1
                
                # --- BƯỚC 4: LƯU OUTPUT ---
                self.output_handle.write(f"{test_case}\n")
                
                # --- BƯỚC 5: REPORT METRICS ---
                if loop_count % 100 == 0:
                    print(self.metrics.report())
                    self.output_handle.flush()
                    self.hash_file_handle.flush()

        except KeyboardInterrupt:
            print("\n[!] Fuzzer đang dừng...")
            raise

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
        print("\n[!] Dừng fuzzer...")
    finally:
        if fuzzer:
            print("\n[i] Đang lưu kết quả...")
            print(fuzzer.metrics.report())
            fuzzer.output_handle.close()
            fuzzer.hash_file_handle.close()
            print(f"[i] Đã lưu {fuzzer.metrics.unique_generated} test cases vào {fuzzer.output_file}")
            print("[i] Tạm biệt.")