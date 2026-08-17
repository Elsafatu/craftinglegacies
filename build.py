#!/usr/bin/env python3
"""
Build Crafting Legacies.

    python3 build.py

Reads Markdown from content/ and writes finished HTML into public/.
Standard library only — nothing to install, nothing to rot.
Python 3.8 or newer.
"""

import html
import os
import re
import shutil
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
THEME = os.path.join(ROOT, "theme")
OUT = os.path.join(ROOT, "public")

SITE_URL = "https://craftinglegacies.com"
SITE_TITLE = "Crafting Legacies"
SITE_DESC = ("Writing on land governance, property, estates and legacy planning "
             "by Elsa Mwalilino, a Zambian estates and real estate attorney.")

# Paste the form action URL from Buttondown, MailerLite or similar here.
# Left blank, the form shows a note instead of pretending to work.
SUBSCRIBE_ACTION = ""


# ── Markdown ──────────────────────────────────────────────────────────

def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def markdown(src):
    out, buf, mode = [], [], None

    def flush():
        nonlocal buf, mode
        if not buf:
            mode = None
            return
        if mode == "p":
            out.append("<p>" + inline(" ".join(buf)) + "</p>")
        elif mode == "quote":
            out.append("<blockquote><p>" + inline(" ".join(buf)) + "</p></blockquote>")
        elif mode in ("ul", "ol"):
            items = "".join("<li>" + inline(i) + "</li>" for i in buf)
            out.append("<{0}>{1}</{0}>".format(mode, items))
        buf, mode = [], None

    for raw in src.split("\n"):
        stripped = raw.strip()

        if not stripped:
            flush()
            continue
        if re.fullmatch(r"-{3,}", stripped):
            flush()
            out.append("<hr>")
            continue

        h = re.match(r"(#{2,4})\s+(.*)", stripped)
        if h:
            flush()
            out.append("<h{0}>{1}</h{0}>".format(len(h.group(1)), inline(h.group(2))))
            continue

        li = re.match(r"[-*]\s+(.*)", stripped)
        if li:
            if mode != "ul":
                flush()
                mode = "ul"
            buf.append(li.group(1))
            continue

        oli = re.match(r"\d+[.)]\s+(.*)", stripped)
        if oli:
            if mode != "ol":
                flush()
                mode = "ol"
            buf.append(oli.group(1))
            continue

        q = re.match(r">\s?(.*)", stripped)
        if q:
            if mode != "quote":
                flush()
                mode = "quote"
            buf.append(q.group(1))
            continue

        if mode != "p":
            flush()
            mode = "p"
        buf.append(stripped)

    flush()
    return "\n".join(out)


# ── Content ───────────────────────────────────────────────────────────

def read_doc(path):
    with open(path, encoding="utf-8") as f:
        text = f.read().replace("\r\n", "\n").lstrip()

    meta = {}
    if text.startswith("---\n"):
        head, _, text = text[4:].partition("\n---")
        text = text.lstrip("\n")
        for line in head.split("\n"):
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip().lower()] = v.strip()
    meta["body"] = text
    return meta


def load_posts():
    posts = []
    folder = os.path.join(CONTENT, "posts")
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md") or name.startswith("_"):
            continue
        p = read_doc(os.path.join(folder, name))
        p["slug"] = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name[:-3])
        p["url"] = "writing/{}.html".format(p["slug"])
        p.setdefault("date", name[:10])
        p.setdefault("subject", "")
        p.setdefault("standfirst", "")
        p["featured"] = p.get("featured", "").lower() in ("true", "yes", "1")
        try:
            p["dt"] = datetime.strptime(p["date"], "%Y-%m-%d")
        except ValueError:
            p["dt"] = datetime.min
        posts.append(p)

    # Newest first, but anything marked `featured: true` holds the top.
    posts.sort(key=lambda p: p["dt"], reverse=True)
    posts.sort(key=lambda p: not p["featured"])
    return posts


# ── Rendering ─────────────────────────────────────────────────────────

with open(os.path.join(THEME, "base.html"), encoding="utf-8") as f:
    BASE = f.read()

NAV = {"writing": "__NAV_WRITING__", "about": "__NAV_ABOUT__",
       "circle": "__NAV_CIRCLE__", "contact": "__NAV_CONTACT__"}


def write(path, text):
    dest = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(dest) or OUT, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text)


def page(body, title, desc, path, active="", ogtype="website"):
    root = "../" * path.count("/")
    full = title if title == SITE_TITLE else "{} — {}".format(title, SITE_TITLE)
    out = (BASE
           .replace("__BODY__", body)
           .replace("__TITLE__", html.escape(full, quote=True))
           .replace("__DESC__", html.escape(desc, quote=True))
           .replace("__CANONICAL__", "{}/{}".format(SITE_URL.rstrip("/"), path))
           .replace("__OGTYPE__", ogtype)
           .replace("__ROOT__", root)
           .replace("__YEAR__", str(datetime.now().year)))
    for key, token in NAV.items():
        out = out.replace(token, ' aria-current="page"' if key == active else "")
    write(path, out)


def pretty_date(dt):
    return dt.strftime("%d %B %Y").lstrip("0") if dt != datetime.min else ""


def meta_line(p):
    bits = []
    if p["featured"]:
        bits.append('<span class="flag">Featured</span>')
    if p["subject"]:
        bits.append(html.escape(p["subject"]))
    if pretty_date(p["dt"]):
        bits.append(pretty_date(p["dt"]))
    return " &middot; ".join(bits)


def piece_html(p, root=""):
    return """  <article class="piece">
    <p class="meta">{meta}</p>
    <h3><a href="{root}{url}">{title}</a></h3>
    <p class="dek">{dek}</p>
  </article>""".format(meta=meta_line(p), root=root, url=p["url"],
                       title=html.escape(p.get("title", "Untitled")),
                       dek=html.escape(p["standfirst"]))


def circle_block():
    if SUBSCRIBE_ACTION:
        form = ('<form class="form" action="{}" method="post">'
                '<input type="email" name="email" placeholder="Your email address" '
                'aria-label="Your email address" required>'
                '<button type="submit">Join the Circle</button></form>'
                ).format(SUBSCRIBE_ACTION)
        note = ""
    else:
        form = ('<form class="form" onsubmit="return false">'
                '<input type="email" placeholder="Your email address" '
                'aria-label="Your email address">'
                '<button type="submit">Join the Circle</button></form>')
        note = ('<p class="form-note">Not yet connected &mdash; set SUBSCRIBE_ACTION '
                'in build.py to make this live.</p>')

    return """
<section class="invite">
  <div class="wrap">
    <h2>Crafting a legacy begins with understanding what you have, what it means, and what you
    want it to become.</h2>
    <p class="circle-name">The Legacy Circle</p>
    <p>A small group of readers who receive new essays, commentary and research as they are
    published &mdash; and who are thinking about the same questions. Occasional, never noisy.</p>
    {form}
    {note}
  </div>
</section>
""".format(form=form, note=note)


# ── Pages ─────────────────────────────────────────────────────────────

def build_home(posts):
    body = """
<div class="opening">
  <div class="wrap wide">
    <p class="banner">By Elsa Mwalilino</p>
    <h1>Live Intentionally.<br>Build Intentionally.<br>Leave Intentionally.</h1>
    <p>I am a Zambian lawyer working in property, estates and governance. This is where I write
    about how those systems actually co-exist &mdash; and what it takes to build something that
    outlasts you.</p>
  </div>
  <div class="rule"></div>
</div>

<div class="wrap">
  <p class="eyebrow">Recent writing</p>
{pieces}
  <p class="readmore"><a href="writing.html">Read everything &rarr;</a></p>
</div>

<section class="concerns">
  <div class="wrap">
    <p class="eyebrow">What I am working on</p>
    <h2>Six questions, returned to often.</h2>
    <p>Most of what appears here sits somewhere among <strong>land governance</strong>,
    <strong>property and conveyancing</strong> and <strong>estates and succession</strong> &mdash;
    the practical end, where transactions either complete or quietly fail.</p>
    <p>Behind those sit the slower questions: <strong>corporate governance</strong>, and how
    authority and records decide whether an institution survives its founder;
    <strong>law and development</strong>, and who the system reaches; and
    <strong>legacy planning</strong>, which is really all of the above, arranged deliberately
    rather than left to chance.</p>
  </div>
</section>

<section class="about">
  <div class="wrap">
    <p class="eyebrow">About</p>
    <h2>A lawyer who kept asking why the system worked this way.</h2>
    <p>Elsa Mwalilino is a Zambian estates and real estate attorney, researcher and writer, and a
    Senior Associate at Kaumbu Mwondela Legal Practitioners, where she leads the Conveyancing and
    Company Secretarial departments.</p>
    <p>She holds an LLB and an MSc in Human Rights, Governance and Development from the University
    of Zambia. Her practice supplied the transactions; her research took her into the systems
    behind them.</p>
    <p class="readmore left"><a href="about.html">More about this work &rarr;</a></p>
  </div>
</section>
{circle}
""".format(pieces="\n".join(piece_html(p) for p in posts[:3]), circle=circle_block())
    page(body, SITE_TITLE, SITE_DESC, "index.html")


def build_writing(posts):
    body = """
<div class="pagehead">
  <div class="wrap wide">
    <h1>Writing</h1>
    <p class="dek">Articles, commentary, research and practical reflections on land governance,
    property, estates and the work of building something that lasts.</p>
  </div>
  <div class="rule"></div>
</div>

<div class="wrap">
{pieces}
</div>
{circle}
""".format(pieces="\n".join(piece_html(p) for p in posts), circle=circle_block())
    page(body, "Writing", "Articles and commentary by Elsa Mwalilino.",
         "writing.html", active="writing")


def build_post(p):
    body = """
<article>
  <div class="article-head">
    <div class="wrap wide">
      <p class="meta">{meta}</p>
      <h1>{title}</h1>
      <p class="dek">{dek}</p>
    </div>
    <div class="rule"></div>
  </div>

  <div class="wrap prose">
{content}
    <hr>
    <p class="readmore left"><a href="../writing.html">&larr; All writing</a></p>
  </div>
</article>
{circle}
""".format(meta=meta_line(p), title=html.escape(p.get("title", "Untitled")),
           dek=html.escape(p["standfirst"]), content=markdown(p["body"]),
           circle=circle_block())
    page(body, p.get("title", "Untitled"), p["standfirst"] or SITE_DESC,
         p["url"], active="writing", ogtype="article")


def build_simple(name, active, circle=True):
    doc = read_doc(os.path.join(CONTENT, "pages", name + ".md"))
    body = """
<div class="pagehead">
  <div class="wrap wide">
    <h1>{title}</h1>
    <p class="dek">{dek}</p>
  </div>
  <div class="rule"></div>
</div>

<div class="wrap prose">
{content}
</div>
{circle}
""".format(title=html.escape(doc.get("title", name.title())),
           dek=html.escape(doc.get("standfirst", "")),
           content=markdown(doc["body"]),
           circle=circle_block() if circle else "")
    page(body, doc.get("title", name.title()), doc.get("standfirst", SITE_DESC),
         name + ".html", active=active)


def build_feed(posts):
    dated = sorted(posts, key=lambda p: p["dt"], reverse=True)
    items = "\n".join("""  <item>
    <title>{title}</title>
    <link>{site}/{url}</link>
    <guid>{site}/{url}</guid>
    <pubDate>{date}</pubDate>
    <description>{desc}</description>
  </item>""".format(title=html.escape(p.get("title", "")), site=SITE_URL.rstrip("/"),
                    url=p["url"],
                    date=p["dt"].replace(tzinfo=timezone.utc).strftime("%a, %d %b %Y 00:00:00 +0000"),
                    desc=html.escape(p["standfirst"])) for p in dated[:20])

    write("feed.xml", """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>{title}</title>
  <link>{site}</link>
  <description>{desc}</description>
  <language>en</language>
{items}
</channel></rss>
""".format(title=SITE_TITLE, site=SITE_URL, desc=html.escape(SITE_DESC), items=items))


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copy(os.path.join(THEME, "styles.css"), os.path.join(OUT, "styles.css"))

    posts = load_posts()
    build_home(posts)
    build_writing(posts)
    for p in posts:
        build_post(p)
    build_simple("about", "about")
    build_simple("legacy-circle", "circle", circle=False)
    build_simple("contact", "contact", circle=False)
    build_feed(posts)

    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: {}/sitemap.xml\n".format(SITE_URL))
    urls = ["index.html", "writing.html", "about.html", "legacy-circle.html",
            "contact.html"] + [p["url"] for p in posts]
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "\n".join("  <url><loc>{}/{}</loc></url>".format(SITE_URL.rstrip("/"), u) for u in urls)
          + "\n</urlset>\n")

    print("Built {} pieces into public/".format(len(posts)))


if __name__ == "__main__":
    main()
