import os
import json
from datetime import datetime


def save_json(results_by_url, output_dir="reports"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(output_dir, f"report_{timestamp}.json")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_by_url, f, indent=2, ensure_ascii=False)

    return json_path
