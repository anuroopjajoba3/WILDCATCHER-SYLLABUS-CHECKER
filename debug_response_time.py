cat > debug_response_time.py << 'EOF'
import json
from detectors.response_time_detector import detect_response_time

# Load your ground truth
with open('ground_truth.json', 'r') as f:
    ground_truth = json.load(f)

# First, let's check the structure
print("Checking structure of first entry...")
if ground_truth and len(ground_truth) > 0:
    first_entry = ground_truth[0]
    print(f"Keys: {first_entry.keys()}")
    print(f"response_time type: {type(first_entry.get('response_time'))}")
    print(f"response_time value: {first_entry.get('response_time')}")
    print()

# Analyze failures
false_negatives = []  # GT has value, we return "Missing"
false_positives = []  # GT is "Missing", we return value
format_mismatches = []  # Both have values but different

for entry in ground_truth:
    filename = entry.get('filename')
    response_time_data = entry.get('response_time')
    
    # Handle different possible structures
    if isinstance(response_time_data, dict):
        gt_response = response_time_data.get('gt', 'Missing')
        pred_response = response_time_data.get('pred', 'Missing')
    elif isinstance(response_time_data, str):
        # If it's a string, it might be the ground truth value directly
        gt_response = response_time_data
        pred_response = 'Missing'  # We'll need to get this from test_results.json
    else:
        continue
    
    if gt_response != "Missing" and pred_response == "Missing":
        false_negatives.append({
            'file': filename,
            'gt': gt_response,
            'pred': pred_response
        })
    elif gt_response == "Missing" and pred_response != "Missing":
        false_positives.append({
            'file': filename,
            'gt': gt_response,
            'pred': pred_response
        })
    elif gt_response != "Missing" and pred_response != "Missing" and gt_response != pred_response:
        format_mismatches.append({
            'file': filename,
            'gt': gt_response,
            'pred': pred_response
        })

print("\n=== FALSE NEGATIVES (Missing valid response times) ===")
print(f"Count: {len(false_negatives)}")
for item in false_negatives[:10]:  # Show first 10
    print(f"  {item['file']}")
    print(f"    GT: '{item['gt']}'")
    print(f"    Pred: '{item['pred']}'")
    print()

print("\n=== FALSE POSITIVES (Extracting when shouldn't) ===")
print(f"Count: {len(false_positives)}")
for item in false_positives[:10]:
    print(f"  {item['file']}")
    print(f"    GT: '{item['gt']}'")
    print(f"    Pred: '{item['pred']}'")
    print()

print("\n=== FORMAT MISMATCHES ===")
print(f"Count: {len(format_mismatches)}")
for item in format_mismatches[:10]:
    print(f"  {item['file']}")
    print(f"    GT: '{item['gt']}'")
    print(f"    Pred: '{item['pred']}'")
    print()
EOF