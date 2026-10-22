# scripts/build_html_report.py
import os
import json

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_path = os.path.join(base_dir, "FINAL_PROJECT_REPORT_EVIDENCE.md")
    html_path = os.path.join(base_dir, "FINAL_PROJECT_REPORT_EVIDENCE.html")
    public_html_path = os.path.join(base_dir, "frontend", "public", "FINAL_PROJECT_REPORT_EVIDENCE.html")

    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    encoded_md = json.dumps(md_content)

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MockMate AI - Final Project Report Evidence & Facts</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.0/github-markdown.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        body {
            box-sizing: border-box;
            min-width: 200px;
            max-width: 1080px;
            margin: 0 auto;
            padding: 40px 20px;
            background-color: #f6f8fa;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        }
        .markdown-body {
            background: #ffffff;
            padding: 48px 56px;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
            border: 1px solid #d0d7de;
        }
        .top-toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding: 14px 20px;
            background: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            border: 1px solid #d0d7de;
        }
        .btn {
            background: #2da44e;
            color: #ffffff;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 14px;
        }
        .btn:hover {
            background: #2c974b;
        }
        .btn-secondary {
            background: #f6f8fa;
            color: #24292f;
            border: 1px solid #d0d7de;
        }
        .btn-secondary:hover {
            background: #f3f4f6;
        }
        @media print {
            body {
                padding: 0;
                background: #ffffff;
            }
            .markdown-body {
                box-shadow: none;
                border: none;
                padding: 0;
            }
            .top-toolbar {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="top-toolbar">
        <div>
            <strong style="color: #24292f; font-size: 16px;">MockMate AI - Academic Report Ground-Truth Evidence</strong>
            <span style="color: #57606a; margin-left: 12px; font-size: 13px;">October 21, 2026</span>
        </div>
        <div style="display: flex; gap: 10px;">
            <button class="btn btn-secondary" onclick="window.print()">Print / Save as PDF</button>
            <a class="btn" href="MOCKMATE_PROJECT_REPORT_PACKAGE.zip" download>Download ZIP Package</a>
        </div>
    </div>
    
    <article class="markdown-body" id="content"></article>

    <script>
        const rawMarkdown = """ + encoded_md + """;
        marked.setOptions({
            gfm: true,
            breaks: true
        });
        document.getElementById('content').innerHTML = marked.parse(rawMarkdown);
        hljs.highlightAll();
    </script>
</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_template)

    with open(public_html_path, "w", encoding="utf-8") as f:
        f.write(html_template)

    print(f"Generated {html_path} ({len(html_template)} bytes)")
    print(f"Generated {public_html_path}")

if __name__ == "__main__":
    main()
