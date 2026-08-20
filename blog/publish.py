#!/usr/bin/env python3
"""Automate blog publishing.

Usage:
    python3 publish.py 2026_08_19.md

Converts a markdown post in the blog directory into a standalone HTML post
(blog/YYYY-MM-DD.html) using the same template as the other posts, then
prepends a preview article for it to blog/index.html.

Requires the `markdown` library:  pip install markdown
"""

import argparse
import datetime
import html
import re
import sys
from pathlib import Path

import markdown

BLOG_DIR = Path(__file__).resolve().parent

DATE_RE = re.compile(r"^(\d{4})[-_](\d{2})[-_](\d{2})\.md$")

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Ocelot Code Systems Blog</title>
    <link rel="stylesheet" href="../styles.css">
    <link rel="stylesheet" href="styles.css">
</head>
<body>
<header class="site-header">
    <div class="site-header-inner">
        <a href="../index.html" class="site-brand">Ocelot Code Systems</a>
        <nav class="site-nav">
            <a href="../index.html">Home</a>
            <a href="index.html">Blog</a>
            <a href="../index.html#services">Services</a>
            <a href="../index.html#contact">Contact</a>
        </nav>
    </div>
</header>

<article class="blog-post">
    <header class="blog-header">
        <h1 class="blog-title">{title}</h1>
        <p class="post-metadata">
            <time datetime="{date}">{human_date}</time>
        </p>
    </header>

    <div class="blog-content">
{body}
    </div>
</article>

<footer class="site-footer">
    <p>&copy; 2026 Ocelot Code Systems. Built with intention, tested to prove.</p>
</footer>
</body>
</html>
"""


def parse_date(filename: str) -> datetime.date:
    match = DATE_RE.match(filename)
    if not match:
        sys.exit(f"Error: filename must look like YYYY_MM_DD.md, got {filename!r}")
    year, month, day = (int(part) for part in match.groups())
    return datetime.date(year, month, day)


def convert_body(body_md: str) -> str:
    converted = markdown.markdown(body_md, extensions=["tables", "fenced_code"])
    converted = converted.rstrip()
    sections = re.split(r"(?=<h2>)", converted)
    rendered = []
    for section in sections:
        section = section.strip()
        indented = "\n".join("            " + line for line in section.splitlines())
        rendered.append(f"        <section class=\"blog-section\">\n{indented}\n        </section>")
    return "\n\n".join(rendered)


def build_preview(md_text: str) -> tuple[list[str], list[tuple[str, str]]]:
    intro: list[str] = []
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_paras: list[str] = []
    para: list[str] = []
    in_fence = False

    def flush() -> None:
        nonlocal para
        text = " ".join(p.strip() for p in para if p.strip())
        para = []
        if not text:
            return
        if current_title is None:
            intro.append(text)
        else:
            current_paras.append(text)

    for line in md_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            para = []
            continue
        if in_fence:
            para = []
            continue
        if stripped.startswith("#"):
            flush()
            if stripped.startswith("## "):
                if current_title is not None:
                    sections.append((current_title, current_paras))
                    current_paras = []
                current_title = stripped[3:].strip()
            continue
        if stripped.startswith("|"):
            para = []
            continue
        if not stripped:
            flush()
            continue
        para.append(stripped)
    flush()
    if current_title is not None:
        sections.append((current_title, current_paras))

    first_paras = [(title, paras[0]) for title, paras in sections if paras]
    return intro, first_paras


def render_article(title: str, date: datetime.date, href: str, intro: list[str], sections: list[tuple[str, str]]) -> str:
    human_date = date.strftime("%B %d, %Y")
    iso_date = date.isoformat()
    lines = [
        "<article class=\"article-item\" data-expanded=\"false\">",
        "    <header class=\"item-header\" data-toggle=\"article\">",
        "        <div class=\"header-content\">",
        f"            <h3><a href=\"{href}\">{html.escape(title, quote=False)}</a></h3>",
        f"            <time datetime=\"{iso_date}\">{human_date}</time>",
        "        </div>",
        "        <span class=\"toggle-indicator\"></span>",
        "    </header>",
        "    <div class=\"preview-content\">",
    ]
    for paragraph in intro[:1]:
        lines.append(f"        <p>{html.escape(paragraph, quote=False)}</p>")
    for section_title, first_para in sections[:3]:
        lines.append(f"        <h4>{html.escape(section_title, quote=False)}</h4>")
        lines.append(f"        <p>{html.escape(first_para, quote=False)}</p>")
    lines.append("        <p>...</p>")
    lines.append(f"        <h3><a href=\"{href}\">View Post</a></h3>")
    lines.append("    </div>")
    lines.append("</article>")
    return "\n".join(lines)


def render_index_block(title: str, date: datetime.date, href: str, intro: list[str], sections: list[tuple[str, str]]) -> str:
    article = render_article(title, date, href, intro, sections)
    indented = "\n".join("            " + line for line in article.splitlines())
    return f"            <!-- Article 1 - Most Recent -->\n{indented}"


ARTICLE_RE = re.compile(
    r"(?s)(?:<!-- Article \d+(?: - Most Recent)? -->\s*)?<article class=\"article-item\".*?</article>"
)
COMMENT_RE = re.compile(r"^\s*<!-- Article \d+(?: - Most Recent)? -->\s*$")


def update_index(index_path: Path, article_html: str, href: str) -> None:
    text = index_path.read_text(encoding="utf-8")

    def drop_existing(match: re.Match) -> str:
        return "" if f'href="{href}"' in match.group(0) else match.group(0)

    text = ARTICLE_RE.sub(drop_existing, text)

    anchor = "<div class=\"articles-container\">\n"
    if anchor not in text:
        sys.exit("Error: could not find '<div class=\"articles-container\">' in index.html")
    text = text.replace(anchor, anchor + article_html + "\n", 1)

    out_lines = []
    count = 0
    for line in text.splitlines(keepends=True):
        if COMMENT_RE.match(line):
            count += 1
            indent = line[: len(line) - len(line.lstrip())]
            label = "<!-- Article 1 - Most Recent -->" if count == 1 else f"<!-- Article {count} -->"
            out_lines.append(f"{indent}{label}\n")
        else:
            out_lines.append(line)
    text = "".join(out_lines)
    text = re.sub(r"[ \t]*\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    index_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a blog markdown post to HTML and add a preview to index.html.")
    parser.add_argument("post", help="markdown file in the blog directory, e.g. 2026_08_19.md")
    args = parser.parse_args()

    post_name = Path(args.post).name
    date = parse_date(post_name)
    src_path = BLOG_DIR / post_name
    if not src_path.exists():
        sys.exit(f"Error: {src_path} does not exist")

    md_text = src_path.read_text(encoding="utf-8")
    lines = md_text.splitlines()
    if not lines or not lines[0].startswith("# "):
        sys.exit("Error: markdown file must start with an '# <Title>' line")
    title = lines[0][2:].strip()

    body_md = "\n".join(lines[1:]).strip()
    body = convert_body(body_md)

    iso_date = date.isoformat()
    human_date = date.strftime("%B %d, %Y")
    html_path = BLOG_DIR / f"{iso_date}.html"
    html_path.write_text(
        PAGE_TEMPLATE.format(title=html.escape(title), date=iso_date, human_date=human_date, body=body),
        encoding="utf-8",
    )
    print(f"Wrote {html_path.name}")

    intro, sections = build_preview(md_text)
    href = f"{iso_date}.html"
    block = render_index_block(title, date, href, intro, sections)
    update_index(BLOG_DIR / "index.html", block, href)
    print(f"Updated index.html with preview for {href}")


if __name__ == "__main__":
    main()