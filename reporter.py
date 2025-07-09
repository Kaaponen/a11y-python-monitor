import os
from datetime import datetime


def save_report(results_by_url, output_dir="reports"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(output_dir, f"report_{timestamp}.md")
    html_path = os.path.join(output_dir, f"report_{timestamp}.html")

    with open(md_path, "w", encoding="utf-8") as md, open(html_path, "w", encoding="utf-8") as html:
        md.write(f"# Accessibility Report ({timestamp})\n\n")
        html.write(f"""<html>
<head>
  <meta charset='utf-8'>
  <title>Accessibility Report</title>
  <style>
    body {{ font-family: sans-serif; }}
    h1 {{ color: #333; }}
    h2 {{ margin-top: 2em; }}
    .pass {{ color: green; }}
    .fail {{ color: red; }}
    .legend span {{
        display: inline-block;
        padding: 0.25em 0.5em;
        margin-right: 1em;
        border-radius: 4px;
        color: white;
        font-weight: bold;
    }}
    .minor {{ background-color: #e69500; }}
    .serious {{ background-color: #e60000; }}
    .critical {{ background-color: #800000; }}
    code {{ background-color: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; }}
    em {{ color: #555; }}
    .violation {{ margin: 1em 0; padding: 0.5em; border-left: 4px solid transparent; }}
    .violation.minor {{ border-color: #e69500; }}
    .violation.serious {{ border-color: #e60000; }}
    .violation.critical {{ border-color: #800000; }}
  </style>
  <script>
    function filterViolations(level) {{
      let all = document.querySelectorAll('.violation');
      all.forEach(el => {{
        el.style.display = (level === 'all' || el.classList.contains(level)) ? 'block' : 'none';
      }});
    }}
  </script>
</head>
<body>
<h1>Accessibility Report ({timestamp})</h1>

<div class="legend">
  <strong>Legend:</strong>
  <span class="minor">Minor</span>
  <span class="serious">Serious</span>
  <span class="critical">Critical</span>
</div>

<label for="filter">Filter by severity:</label>
<select id="filter" onchange="filterViolations(this.value)">
  <option value="all">Show all</option>
  <option value="minor">Minor</option>
  <option value="serious">Serious</option>
  <option value="critical">Critical</option>
</select>
""")

        for url, results in results_by_url.items():
            md.write(f"\n## {url}\n")
            html.write(f"<h2>{url}</h2>")

            violations = results.get("violations", [])
            if not violations:
                md.write("✅ No accessibility violations found.\n")
                html.write(
                    "<p class='pass'>✅ No accessibility violations found.</p>")
                continue

            for v in violations:
                impact = v.get("impact", "minor")
                md.write(f"\n### ❌ {v['help']} ({v['id']})\n")
                md.write(f"[More info]({v['helpUrl']})\n")

                html.write(f"<div class='violation {impact}'>")
                html.write(f"<h3 class='fail'>❌ {v['help']} ({v['id']})</h3>")
                html.write(f"<p><a href='{v['helpUrl']}'>More info</a></p>")

                for node in v['nodes']:
                    html_snippet = node['html'].replace(
                        "<", "&lt;").replace(">", "&gt;")
                    issues = ', '.join([check['message']
                                       for check in node['any']])
                    md.write(f"- `{node['html']}`\n  - {issues}\n")
                    html.write(
                        f"<p><code>{html_snippet}</code><br><em>{issues}</em></p>")

                html.write("</div>")

        html.write("</body></html>")

    return md_path, html_path
