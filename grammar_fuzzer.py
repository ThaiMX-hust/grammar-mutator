# grammar_fuzzer.py
# Fuzzer "Lai" (Hybrid) - Standalone Mode (No SIEM)

import os
import random
import time
import importlib.util
from pathlib import Path
import hashlib
import argparse
import json
import re

# --- Cấu hình ---
MUTATOR_DIR = "mutators" 
OUTPUT_DIR = "fuzzer_output"  # Thư mục lưu test cases
HASH_FILE = "tested_hashes.txt"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Metrics Tracking ---
class FuzzerMetrics:
    def __init__(self):
        self.total_generated = 0
        self.unique_generated = 0
        self.grammar_based = 0
        self.spliced = 0
        self.start_time = time.time()
    
    def report(self):
        elapsed = time.time() - self.start_time
        rate = self.total_generated / elapsed if elapsed > 0 else 0
        return f"""
--- FUZZER METRICS ---
Total: {self.total_generated} | Unique: {self.unique_generated} | Rate: {rate:.2f}/s
Grammar: {self.grammar_based} | Spliced: {self.spliced}
Runtime: {elapsed:.2f}s
"""

class GrammarFuzzer:
    def __init__(self, grammar_file):
        print(f"Khởi tạo Fuzzer với văn phạm: {grammar_file}")
        self.grammar_file = grammar_file
        try:
            with open(grammar_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.rules = data['rules']
                self.weights = data['weights']
        except Exception as e:
            print(f"[LỖI] Không thể tải file văn phạm: {e}")
            exit(1)

        # Tải mutators (optional)
        self.mutators = self.load_mutators()
        
        # Hash tracking
        self.tested_hashes = set()
        if os.path.exists(HASH_FILE):
            with open(HASH_FILE, 'r') as f:
                self.tested_hashes = set(line.strip() for line in f)
        self.hash_file_handle = open(HASH_FILE, 'a')
        
        # Splice corpus
        self.splice_corpus = []
        self.max_corpus_size = 200
        
        # Metrics
        self.metrics = FuzzerMetrics()
        
        # Output file - Extract rule name from grammar path
        rule_name = self._extract_rule_name(grammar_file)
        self.output_file = os.path.join(OUTPUT_DIR, f"{rule_name}_{int(time.time())}.txt")
        self.output_handle = open(self.output_file, 'w', encoding='utf-8')
        
        print("Fuzzer đã sẵn sàng.")
        print(f"Output: {self.output_file}")
    
    def _extract_rule_name(self, grammar_file):
        """Extract rule name from grammar file path"""
        # Try to get from parent folder name
        # Example: apt_29_thinktanks_bypass_uac_powershell_fuzz_data/grammar.json
        #          -> apt_29_thinktanks_bypass_uac_powershell
        path = Path(grammar_file)
        folder_name = path.parent.name
        
        # Remove _fuzz_data suffix if exists
        if folder_name.endswith('_fuzz_data'):
            return folder_name.replace('_fuzz_data', '')
        
        # Fallback to filename without extension
        return path.stem

    def load_mutators(self):
        """Tải các mutator từ MUTATOR_DIR (optional)"""
        try:
            from base_mutator import BaseMutator
        except ImportError:
            print("[WARN] 'base_mutator.py' not found. Mutations disabled.")
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
        """Chọn 1 quy tắc con dựa trên trọng số"""
        choices_weights = self.weights[parent_rule_name]
        choices = list(choices_weights.keys())
        weights = list(choices_weights.values())
        
        min_weight = min(weights)
        if min_weight < 0:
            weights = [w - min_weight + 0.01 for w in weights]
        
        # 10% exploration: chọn random
        if random.random() < 0.1:
            return random.choice(choices)
            
        return random.choices(choices, weights=weights, k=1)[0]

    def generate_smart_seed(self, current_rule_name="<start>"):
        """Sinh mẫu từ văn phạm"""
        
        if current_rule_name in self.weights:
            chosen_rule = self._weighted_choice(current_rule_name)
            (child_string, child_path) = self.generate_smart_seed(chosen_rule)
            return (child_string, [current_rule_name] + child_path)

        if current_rule_name in self.rules:
            rule_sequence = self.rules[current_rule_name]
            parts_to_expand = re.findall(r"(<[^>]+>)", rule_sequence)
            
            if not parts_to_expand:
                return (rule_sequence, [current_rule_name])

            generated_string = rule_sequence
            generated_path = [current_rule_name]
            
            for part in parts_to_expand:
                (child_string, child_path) = self.generate_smart_seed(part)
                generated_string = generated_string.replace(part, child_string, 1)
                generated_path.extend(child_path)
                
            return (generated_string, generated_path)
        
        # Check if string contains tags to expand (even if not in rules/weights)
        parts_to_expand = re.findall(r"(<[^>]+>)", current_rule_name)
        if parts_to_expand:
            generated_string = current_rule_name
            generated_path = [current_rule_name]
            
            for part in parts_to_expand:
                (child_string, child_path) = self.generate_smart_seed(part)
                generated_string = generated_string.replace(part, child_string, 1)
                generated_path.extend(child_path)
                
            return (generated_string, generated_path)
            
        return (current_rule_name, [current_rule_name])

    def apply_havoc_mutations(self, command):
        """Áp dụng mutations (30% chance)"""
        if random.random() > 0.3 or not self.mutators:
            return command
        
        available_tags = [tag for tag in self.mutators if self.mutators[tag]]
        if not available_tags:
            return command
        
        tag = random.choice(available_tags)
        mutator_list = self.mutators[tag]
        
        num_mutations = random.randint(1, 2)
        mutated = command
        
        for _ in range(num_mutations):
            mutator = random.choice(mutator_list)
            try:
                mutated = mutator.mutate(mutated)
            except Exception:
                pass
        
        return mutated

    def add_to_splice_corpus(self, test_case):
        """Thêm test case vào corpus"""
        if test_case and len(test_case) > 5:
            self.splice_corpus.append(test_case)
            if len(self.splice_corpus) > self.max_corpus_size:
                self.splice_corpus.pop(0)

    def splice_test_cases(self, test_case_a, test_case_b):
        """Lai ghép 2 test cases"""
        def tokenize(cmd):
            pattern = r'("[^"]*"|\'[^\']*\'|[^\s]+)'
            return re.findall(pattern, cmd)
        
        tokens_a = tokenize(test_case_a)
        tokens_b = tokenize(test_case_b)
        
        if not tokens_a or not tokens_b:
            return test_case_a
        
        splice_point_a = random.randint(1, len(tokens_a) - 1)
        splice_point_b = random.randint(1, len(tokens_b) - 1)
        
        spliced_tokens = tokens_a[:splice_point_a] + tokens_b[splice_point_b:]
        return " ".join(spliced_tokens)
    
    def generate_spliced_seed(self):
        """Sinh seed bằng splicing"""
        if len(self.splice_corpus) < 2:
            return None
        
        test_case_a = random.choice(self.splice_corpus)
        test_case_b = random.choice(self.splice_corpus)
        
        if test_case_a == test_case_b:
            return None
        
        return self.splice_test_cases(test_case_a, test_case_b)

    def main_loop(self):
        """Vòng lặp fuzzing chính"""
        print(f"\n--- BẮT ĐẦU Fuzzing (PID: {os.getpid()}) ---")
        print(f"Output: {self.output_file}")
        print("[!] Chạy trong chế độ standalone (không SIEM)\n")
        
        loop_count = 0

        try:
            while True:
                loop_count += 1
                self.metrics.total_generated += 1
                
                # --- SINH TEST CASE ---
                # 20% splicing (giảm từ 30%)
                if random.random() < 0.2 and len(self.splice_corpus) >= 2:
                    spliced_seed = self.generate_spliced_seed()
                    if spliced_seed:
                        test_case = spliced_seed
                        self.metrics.spliced += 1
                    else:
                        (smart_seed, path) = self.generate_smart_seed()
                        test_case = self.apply_havoc_mutations(smart_seed)
                        self.metrics.grammar_based += 1
                else:
                    (smart_seed, path) = self.generate_smart_seed()
                    test_case = self.apply_havoc_mutations(smart_seed)
                    self.metrics.grammar_based += 1

                # --- DEDUP ---
                cmd_hash = hashlib.sha256(test_case.encode()).hexdigest()
                if cmd_hash in self.tested_hashes:
                    continue 
                
                self.tested_hashes.add(cmd_hash)
                self.hash_file_handle.write(f"{cmd_hash}\n")
                self.metrics.unique_generated += 1
                
                # --- THÊM VÀO CORPUS ---
                self.add_to_splice_corpus(test_case)
                
                # --- LƯU VÀO FILE ---
                self.output_handle.write(f"{test_case}\n")
                
                # --- REPORT ---
                if loop_count % 100 == 0:
                    print(self.metrics.report())
                    self.output_handle.flush()
                    self.hash_file_handle.flush()

        except KeyboardInterrupt:
            print("\n[!] Fuzzer đang dừng...")
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grammar Fuzzer - Standalone Mode")
    parser.add_argument(
        "-g", "--grammar",
        type=str,
        default="grammar.json",
        help="File văn phạm JSON"
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