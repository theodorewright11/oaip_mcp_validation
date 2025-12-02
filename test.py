import re
import hashlib

def normalize_key(k):
    # mimic Streamlit's internal normalization (roughly)
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", k.lower())
    if len(normalized) > 50:
        normalized = normalized[:40] + "_" + hashlib.md5(normalized.encode()).hexdigest()[:8]
    return normalized

example_keys = [
    "Select IWA(s):_Analyze data (GWA: something)",
    "Select DWA(s):_Analyze data (DWA: other thing)",
    "Select IWA(s):_Train models (GWA: stuff)",
    "Select DWA(s):_Train models (DWA: more stuff)"
]

print("🔍 Normalized key test:\n")
for key in example_keys:
    print(f"Original: {key}")
    print(f"→ Normalized: {normalize_key(key)}\n")
