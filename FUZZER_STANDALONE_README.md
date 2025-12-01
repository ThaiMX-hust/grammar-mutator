# Grammar Fuzzer - Standalone Mode (Không cần SIEM)

## 📝 Tổng quan

Grammar Fuzzer đã được tối ưu để chạy **độc lập** mà không cần hệ thống SIEM. Fuzzer tập trung vào việc **sinh test cases đa dạng và chất lượng cao** với tốc độ tối đa.

## 🎯 Tính năng

### ✅ Đã tối ưu:
- **Grammar-based generation**: Sinh test cases từ `grammar.json`
- **Splicing**: Lai ghép test cases từ corpus
- **Havoc mutations**: Áp dụng mutators ngẫu nhiên
- **Deduplication**: Tránh test cases trùng lặp (SHA256 hash)
- **Metrics tracking**: Theo dõi tốc độ sinh và chất lượng
- **Fast validation**: Dry-run mode (không execute thật)

### ❌ Đã loại bỏ:
- Feedback loop từ SIEM
- Minimization (cần SIEM để verify)
- Weight updates (cần feedback)
- Consumer dependency
- Queue/Feedback files

## 🚀 Cách sử dụng

### Bước 1: Tạo Grammar File

```bash
# Tạo prompt
python gen_grammar_file.py -c data/rule_config_7zip.py

# Manual: Paste prompt vào Gemini → Lưu kết quả vào grammar.json
# File output: rule_7zip_compress_dump_fuzz_data/grammar.json
```

### Bước 2: Chạy Fuzzer

```bash
python grammar_fuzzer.py -g rule_7zip_compress_dump_fuzz_data/grammar.json
```

### Bước 3: Kiểm tra Output

```bash
# Test cases được lưu vào
dir fuzzer_output\testcases_*.txt

# Xem 10 test cases đầu tiên
Get-Content fuzzer_output\testcases_*.txt | Select-Object -First 10
```

## 📊 Metrics

Mỗi 100 vòng, fuzzer sẽ hiển thị metrics:

```
--- FUZZER METRICS ---
Total: 1000 | Unique: 950 | Rate: 150.23/s
Grammar: 800 | Spliced: 200
Exec OK: 950 | Failed: 50
Runtime: 6.66s
```

**Giải thích:**
- **Total**: Tổng số test cases đã sinh
- **Unique**: Số test cases unique (sau dedup)
- **Rate**: Tốc độ sinh (test cases/giây)
- **Grammar**: Số test cases sinh từ grammar
- **Spliced**: Số test cases lai ghép
- **Exec OK/Failed**: Validation status

## 🔧 Tùy chỉnh

### Điều chỉnh tốc độ Splicing

```python
# Trong main_loop() - dòng ~289
if random.random() < 0.2 and len(self.splice_corpus) >= 2:
    # Thay 0.2 thành:
    # - 0.1: Ít splice hơn (nhiều grammar-based)
    # - 0.5: Nhiều splice hơn (ít grammar-based)
```

### Điều chỉnh Havoc Mutation Rate

```python
# Trong apply_havoc_mutations() - dòng ~133
if random.random() > 0.3 or not self.mutators:
    # Thay 0.3 thành:
    # - 0.1: Nhiều mutation (70% test cases bị mutate)
    # - 0.7: Ít mutation (30% test cases bị mutate)
```

### Điều chỉnh Exploration Rate

```python
# Trong _weighted_choice() - dòng ~123
if random.random() < 0.1:
    # Thay 0.1 thành:
    # - 0.2: Nhiều exploration (chọn random 20%)
    # - 0.05: Ít exploration (theo weights chặt chẽ)
```

## 📈 Workflow

```
1. Load grammar.json
   ↓
2. Loop vô hạn:
   ├─> 80% Grammar-based generation
   │   ├─> generate_smart_seed()
   │   └─> apply_havoc_mutations() (30% chance)
   │
   ├─> 20% Splicing
   │   └─> splice_test_cases(corpus_a, corpus_b)
   │
   ├─> Dedup (SHA256 hash check)
   │
   ├─> Validate (dry-run)
   │
   ├─> Save to output file
   │
   └─> Update metrics (mỗi 100 vòng)
```

## 📁 Files Structure

```
fuzzer_output/
├── testcases_1733072400.txt   # Test cases (1 dòng = 1 test case)
└── testcases_1733072500.txt

tested_hashes.txt                # Hash của test cases đã sinh
```

## 🎓 Ví dụ Output

```bash
# Chạy fuzzer
python grammar_fuzzer.py -g rule_7zip_compress_dump_fuzz_data/grammar.json

# Output:
Khởi tạo Fuzzer với văn phạm: rule_7zip_compress_dump_fuzz_data/grammar.json
  [+] Loaded: 03_powershell_concat (Tag: powershell)
Fuzzer đã sẵn sàng.
Output: fuzzer_output\testcases_1733072400.txt

--- BẮT ĐẦU Fuzzing (PID: 12345) ---
Output: fuzzer_output\testcases_1733072400.txt
[!] Chạy trong chế độ tối ưu (không SIEM)

--- FUZZER METRICS ---
Total: 100 | Unique: 95 | Rate: 150.23/s
Grammar: 82 | Spliced: 18
Exec OK: 95 | Failed: 5
Runtime: 0.67s

--- FUZZER METRICS ---
Total: 200 | Unique: 189 | Rate: 148.11/s
Grammar: 160 | Spliced: 40
Exec OK: 189 | Failed: 11
Runtime: 1.35s

...
```

## 🔍 Phân tích Test Cases

### Xem phân bố độ dài

```powershell
Get-Content fuzzer_output\testcases_*.txt | ForEach-Object { $_.Length } | Measure-Object -Average -Minimum -Maximum

# Output:
# Average: 125.3
# Minimum: 35
# Maximum: 450
```

### Tìm test cases chứa keyword

```powershell
Get-Content fuzzer_output\testcases_*.txt | Select-String "7z.exe"
```

### Đếm số lượng unique wrappers

```powershell
Get-Content fuzzer_output\testcases_*.txt | ForEach-Object { ($_ -split ' ')[0] } | Sort-Object -Unique
```

## 🐛 Troubleshooting

### Lỗi: `ModuleNotFoundError: No module named 'base_mutator'`

```bash
# Kiểm tra file có tồn tại
ls base_mutator.py

# Nếu không có, mutators sẽ bị skip (vẫn chạy được)
```

### Lỗi: `Grammar file not found`

```bash
# Kiểm tra đường dẫn
ls rule_7zip_compress_dump_fuzz_data/grammar.json

# Nếu không có, chạy gen_grammar_file.py trước
python gen_grammar_file.py -c data/rule_config_7zip.py
```

### Tốc độ sinh chậm (< 50/s)

```python
# Tắt mutations hoàn toàn
# Trong apply_havoc_mutations() - dòng ~133
if random.random() > 1.0:  # Never mutate
    return command
```

## 📚 Tích hợp với SIEM (Tương lai)

Để tích hợp lại SIEM sau này:

1. Uncomment các dòng feedback loop
2. Thêm lại `consumer.py`
3. Thay `execute_command()` thành subprocess.run() thật
4. Enable `update_weights()` và `minimize_test_case()`

## 🎯 Next Steps

1. **Chạy fuzzer qua đêm** để tạo corpus lớn
2. **Phân tích output** để tìm patterns thú vị
3. **Tích hợp SIEM** khi sẵn sàng để học hỏi từ feedback
4. **Tùy chỉnh grammar.json** để tăng chất lượng test cases

---

**Tốc độ ước tính**: 150-300 test cases/giây (không execute thật)
**Corpus size**: ~1 triệu test cases trong 1-2 giờ
