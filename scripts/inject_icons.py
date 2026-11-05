"""
inject_icons.py -- adds the site icon tags (favicon, Apple touch icon, web manifest, theme color)
to every HTML page and template under docs/, and to the inline page heads in
scripts/GenerateAllPages.ps1 and python_scripts/generate_recognition_pages_2025.py.
Safe to re-run: files that already have the tags are skipped. Inserts just before </head>.
Usage (repo root):  python scripts/inject_icons.py [--dry-run]
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER = b"site.webmanifest"
SNIPPET = (b'    <link rel="icon" href="/static-football-rankings/favicon.ico" sizes="any">\n'
           b'    <link rel="icon" type="image/svg+xml" href="/static-football-rankings/images/icons/icon.svg">\n'
           b'    <link rel="apple-touch-icon" href="/static-football-rankings/images/icons/apple-touch-icon.png">\n'
           b'    <link rel="manifest" href="/static-football-rankings/site.webmanifest">\n'
           b'    <meta name="theme-color" content="#1b5e20">\n')
HEAD_END = re.compile(rb"([ \t]*)</head>", re.I)
dry = "--dry-run" in sys.argv

targets = []
for d, dirs, files in os.walk(os.path.join(ROOT, "docs")):
    dirs[:] = [x for x in dirs if x not in ("data", "images")]
    targets += [os.path.join(d, f) for f in files if f.lower().endswith(".html")]
targets += [os.path.join(ROOT, "scripts", "GenerateAllPages.ps1"),
            os.path.join(ROOT, "python_scripts", "generate_recognition_pages_2025.py")]

done = skipped = nohead = 0
for p in targets:
    if not os.path.exists(p):
        continue
    b = open(p, "rb").read()
    if MARKER in b:
        skipped += 1
        continue
    n = len(HEAD_END.findall(b))
    if not n:
        nohead += 1
        continue
    if b"\r\n" in b:
        snip = SNIPPET.replace(b"\n", b"\r\n")
    else:
        snip = SNIPPET
    new = HEAD_END.sub(lambda m: snip + m.group(0), b)   # every </head> (the .ps1/.py files hold several page heads)
    if not dry:
        open(p, "wb").write(new)
    done += 1
print(f"{'Would patch' if dry else 'Patched'} {done} files, {skipped} already had the icon tags, {nohead} without </head>.")
