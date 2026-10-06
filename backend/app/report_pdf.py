from __future__ import annotations
from html import escape
from playwright.sync_api import sync_playwright

def render_pdf(audit:dict)->bytes:
    issues="".join(
        f"<tr><td>{escape(str(x['severity']))}</td><td>{escape(str(x['title']))}</td><td>{escape(str(x.get('page_url','')))}</td><td>{escape(str(x.get('recommendation','')))}</td></tr>"
        for x in audit.get("issues",[])
    )
    html=f"""<html><head><style>
    body{{font-family:Arial,sans-serif;padding:32px;color:#111}}
    h1{{font-size:28px}} .score{{font-size:42px;font-weight:700}}
    table{{width:100%;border-collapse:collapse;margin-top:20px}}
    th,td{{border:1px solid #ccc;padding:8px;text-align:left;font-size:11px;vertical-align:top}}
    </style></head><body>
    <h1>WebForge Website Audit</h1><p>{escape(audit['url'])}</p>
    <div class="score">{audit['score']} / 100</div>
    <p>Pages scanned: {audit.get('pages_scanned',0)} | Broken links: {len(audit.get('broken_links',[]))}</p>
    <h2>Engineering backlog</h2>
    <table><tr><th>Severity</th><th>Finding</th><th>Page</th><th>Recommendation</th></tr>{issues}</table>
    </body></html>"""
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        page.set_content(html,wait_until="load")
        pdf=page.pdf(format="A4",print_background=True)
        browser.close()
        return pdf
