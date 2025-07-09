import os
import csv
from datetime import datetime

def save_csv(results_by_url, output_dir="reports"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(output_dir, f"report_{timestamp}.csv")

    with open(csv_path, mode="w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["URL", "Issue ID", "Description", "Impact", "Element HTML", "Message", "Help URL"])

        for url, results in results_by_url.items():
            for v in results.get("violations", []):
                impact = v.get("impact", "minor")
                for node in v["nodes"]:
                    html_snippet = node["html"]
                    messages = [check["message"] for check in node.get("any", [])]
                    for msg in messages:
                        writer.writerow([url, v["id"], v["help"], impact, html_snippet, msg, v["helpUrl"]])

    return csv_path
