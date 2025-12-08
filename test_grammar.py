import json
from grammar_fuzzer import GrammarFuzzer

# Load grammar
fuzzer = GrammarFuzzer("apt_29_thinktanks_bypass_uac_powershell_fuzz_data/grammar.json")

# Generate 10 test cases
for i in range(10):
    seed, path = fuzzer.generate_smart_seed()
    print(f"{i+1}. {seed}")
    print(f"   Path: {' -> '.join(path[:3])}...\n")