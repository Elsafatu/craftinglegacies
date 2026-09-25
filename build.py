#!/usr/bin/env python3
"""
Build Crafting Legacies.

    python3 build.py

Reads Markdown from content/ and writes finished HTML into public/.
Standard library only — nothing to install, nothing to rot.
Python 3.8 or newer.
"""

import hashlib
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

NAV = {"writing": "__NAV_WRITING__", "library": "__NAV_LIBRARY__",
       "about": "__NAV_ABOUT__", "circle": "__NAV_CIRCLE__",
       "contact": "__NAV_CONTACT__"}

# ── The Library ───────────────────────────────────────────────────────
# Each section is a Markdown file in content/library/. Add a file, add a
# line here, and it appears. Order here is the order on the hub page.

LIBRARY = [
    ("law", "The law",
     "The Acts that govern property, land and succession in Zambia, with a note "
     "on what each one actually does."),
    ("words", "The words",
     "Legal terms in plain English \u2014 what they mean, and why they matter to you."),
    ("cases", "The cases",
     "Decisions of the Zambian courts that shaped how property and succession work."),
    ("reading", "Further reading",
     "Books, papers and reports worth your time."),
]


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



# ── Article artwork ───────────────────────────────────────────────────
# Photographs, washed toward the page colour. An article uses its own
# picture if one exists as static/art-<slug>.jpg, otherwise the site's
# default picture. Drop a file in and it appears; no code changes.

ART_EXTS = ("jpg", "jpeg", "png", "webp")

# Browsers rename a download when a file of that name already exists —
# hero.jpg becomes hero_1.jpg, hero (1).jpg, hero-2.jpg and so on. Rather
# than make that your problem every time, match those too.
_COPY_SUFFIX = re.compile(r"^(?P<stem>.+?)[ _-]*\(?\d+\)?$")


def _matches(filename, wanted_stem):
    base, dot, ext = filename.rpartition(".")
    if not dot or ext.lower() not in ART_EXTS:
        return False
    if base == wanted_stem:
        return True
    m = _COPY_SUFFIX.match(base)
    return bool(m and m.group("stem") == wanted_stem)


def find_art(wanted_stem):
    """The file for this name, tolerating a browser's copy suffix."""
    folder = os.path.join(ROOT, "static")
    if not os.path.isdir(folder):
        return None
    # exact name wins; otherwise take the first renamed copy, alphabetically
    candidates = sorted(n for n in os.listdir(folder) if _matches(n, wanted_stem))
    for n in candidates:
        if n.rpartition(".")[0] == wanted_stem:
            return n
    return candidates[0] if candidates else None


def art_file(slug, allow_default=True):
    """This article's own picture; the site default only if permitted."""
    stems = ["art-" + slug] + (["art-default"] if allow_default else [])
    for stem in stems:
        found = find_art(stem)
        if found:
            return found
    return None


def article_art(slug, root="", tall=False, allow_default=True):
    name = art_file(slug, allow_default)
    if not name:
        return ""
    return ('<span class="scene{t}">'
            '<img src="{r}{n}" alt="" loading="lazy" decoding="async">'
            '</span>').format(t=" scene--tall" if tall else "", r=root, n=name)


def strip_link(p, root):
    # own picture only — the default belongs to the hero, not to every row
    art = article_art(p["slug"], root, allow_default=False)
    if not art:
        return ""
    return ('    <a class="plan-strip" href="{r}{u}" tabindex="-1" '
            'aria-hidden="true">{a}</a>'.format(r=root, u=p["url"], a=art))


def piece_html(p, root=""):
    return """  <article class="piece">
{art}
    <p class="meta">{meta}</p>
    <h3><a href="{root}{url}">{title}</a></h3>
    <p class="dek">{dek}</p>
  </article>""".format(meta=meta_line(p), root=root, url=p["url"],
                       art=strip_link(p, root),
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
        form = ('<p class="form-mail"><a href="mailto:hello@craftinglegacies.com'
                '?subject=Joining%20the%20Legacy%20Circle">Write to '
                'hello@craftinglegacies.com</a> and you will be added.</p>')
        note = ""

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

def hero_art():
    """A washed photograph behind the opening, if one has been supplied."""
    name = find_art("hero")
    if not name:
        return ""
    return ('<span class="hero-bg" aria-hidden="true">'
            '<img src="{}" alt="" fetchpriority="high" decoding="async">'
            '</span>').format(name)


def build_home(posts):
    portrait = ""
    if os.path.exists(os.path.join(ROOT, "static", "portrait.jpg")):
        portrait = ('<div class="portrait portrait--inline">'
                    '<img src="portrait.jpg" alt="Elsa Mwalilino" '
                    'width="560" height="700" loading="lazy"></div>')
    body = """
<div class="opening{heroclass}">
  {hero}
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
    {portrait}
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
""".format(pieces="\n".join(piece_html(p) for p in posts[:3]),
           hero=hero_art(), heroclass=" opening--image" if hero_art() else "",
           portrait=portrait, circle=circle_block())
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


def dropcap(html_body):
    """Give the first paragraph of an article an opening capital."""
    i = html_body.find("<p>")
    if i == -1:
        return html_body
    return html_body[:i] + '<p class="opens">' + html_body[i + 3:]


def banner_block(slug, root):
    art = article_art(slug, root, tall=True)
    if art:
        return '  <div class="plan-banner">{}</div>'.format(art)
    return '  <div class="wrap"><div class="rule"></div></div>'


def build_post(p):
    body = """
<article>
  <div class="article-head">
    <div class="wrap wide">
      <p class="meta">{meta}</p>
      <h1>{title}</h1>
      <p class="dek">{dek}</p>
    </div>
  </div>

{banner}

  <div class="wrap prose">
{content}
    <hr>
    <p class="readmore left"><a href="../writing.html">&larr; All writing</a></p>
  </div>
</article>
{circle}
""".format(meta=meta_line(p), title=html.escape(p.get("title", "Untitled")),
           dek=html.escape(p["standfirst"]),
           banner=banner_block(p["slug"], "../"),
           content=dropcap(markdown(p["body"])),
           circle=circle_block())
    page(body, p.get("title", "Untitled"), p["standfirst"] or SITE_DESC,
         p["url"], active="writing", ogtype="article")


def build_simple(name, active, circle=True):
    doc = read_doc(os.path.join(CONTENT, "pages", name + ".md"))

    portrait = ""
    if name == "about" and os.path.exists(os.path.join(ROOT, "static", "portrait.jpg")):
        portrait = ('<div class="portrait"><img src="portrait.jpg" '
                    'alt="Elsa Mwalilino" width="560" height="700"></div>')
    body = """
<div class="pagehead">
  <div class="wrap wide">
    <h1>{title}</h1>
    <p class="dek">{dek}</p>
  </div>
  <div class="rule"></div>
</div>

{portrait}

<div class="wrap prose">
{content}
</div>
{circle}
""".format(title=html.escape(doc.get("title", name.title())), portrait=portrait,
           dek=html.escape(doc.get("standfirst", "")),
           content=markdown(doc["body"]),
           circle=circle_block() if circle else "")
    page(body, doc.get("title", name.title()), doc.get("standfirst", SITE_DESC),
         name + ".html", active=active)


# ── Library entries ───────────────────────────────────────────────────
# Inside a library page, a "### Heading" followed by lines beginning with
# "+ " becomes a citation card. The first + line is the citation, a second
# one starting with http is the link. Everything after is the note.

def library_markdown(src):
    """Markdown, plus citation cards for ### headings with + lines."""
    out, buf = [], []
    lines = src.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        h = re.match(r"###\s+(.*)$", line.strip())
        if not h:
            buf.append(line)
            i += 1
            continue

        # flush ordinary markdown collected so far
        if buf:
            out.append(markdown("\n".join(buf)))
            buf = []

        title = h.group(1)
        i += 1
        cite, link = "", ""
        while i < len(lines) and lines[i].strip().startswith("+"):
            val = lines[i].strip().lstrip("+").strip()
            if val.lower().startswith("http"):
                link = val
            elif not cite:
                cite = val
            i += 1

        note = []
        while i < len(lines):
            nxt = lines[i].strip()
            if re.match(r"###\s+", nxt) or re.match(r"##\s+", nxt):
                break
            note.append(lines[i])
            i += 1

        heading = html.escape(title)
        if link:
            heading = ('<a href="{}" rel="noopener">{}</a>'
                       .format(html.escape(link, quote=True), heading))

        out.append(
            '<div class="entry">\n'
            '  <h3 class="entry-title">{h}</h3>\n'
            '{c}'
            '  <div class="entry-note">{n}</div>\n'
            '</div>'.format(
                h=heading,
                c=('  <p class="entry-cite">{}</p>\n'.format(html.escape(cite))
                   if cite else ""),
                n=markdown("\n".join(note).strip())))

    if buf:
        out.append(markdown("\n".join(buf)))
    return "\n".join(out)


def library_is_draft(slug):
    path = os.path.join(CONTENT, "library", slug + ".md")
    if not os.path.exists(path):
        return True
    return read_doc(path).get("draft", "").lower() in ("true", "yes", "1")


def build_library_hub():
    cards = []
    for slug, title, blurb in LIBRARY:
        if library_is_draft(slug):
            continue
        cards.append(
            '  <a class="shelf" href="library/{s}.html">\n'
            '    <span class="shelf-title">{t}</span>\n'
            '    <span class="shelf-blurb">{b}</span>\n'
            '  </a>'.format(s=slug, t=html.escape(title), b=html.escape(blurb)))

    body = """
<div class="pagehead">
  <div class="wrap wide">
    <h1>The Library</h1>
    <p class="dek">The law, the language and the reading behind the writing.
    Gathered here so it is in one place, for anyone who needs it.</p>
  </div>
  <div class="rule"></div>
</div>

<div class="wrap">
  <div class="shelves">
{cards}
  </div>
  <p class="libnote">Everything here links to the original source rather than
  copying it, so what you read is the version the publisher is maintaining.
  Always check that a provision is current before relying on it.</p>
</div>
{circle}
""".format(cards="\n".join(cards), circle=circle_block())
    page(body, "The Library",
         "Zambian legislation, legal terms in plain English, cases and further "
         "reading on property, land and succession.",
         "library.html", active="library")


def build_library_page(slug, title):
    doc = read_doc(os.path.join(CONTENT, "library", slug + ".md"))
    body = """
<div class="pagehead">
  <div class="wrap wide">
    <p class="kicker"><a href="../library.html">The Library</a></p>
    <h1>{title}</h1>
    <p class="dek">{dek}</p>
  </div>
  <div class="rule"></div>
</div>

<div class="wrap prose library">
{content}
  <hr>
  <p class="readmore left"><a href="../library.html">&larr; The Library</a></p>
</div>
{circle}
""".format(title=html.escape(doc.get("title", title)),
           dek=html.escape(doc.get("standfirst", "")),
           content=library_markdown(doc["body"]),
           circle=circle_block())
    page(body, doc.get("title", title), doc.get("standfirst", SITE_DESC),
         "library/{}.html".format(slug), active="library")


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

    static = os.path.join(ROOT, "static")
    if os.path.isdir(static):
        for asset in os.listdir(static):
            if not asset.startswith("."):
                shutil.copy(os.path.join(static, asset), os.path.join(OUT, asset))

    posts = load_posts()
    build_home(posts)
    build_writing(posts)
    for p in posts:
        build_post(p)
    build_library_hub()
    for slug, title, _ in LIBRARY:
        if os.path.exists(os.path.join(CONTENT, "library", slug + ".md")):
            build_library_page(slug, title)

    build_simple("about", "about")
    build_simple("legacy-circle", "circle", circle=False)
    build_simple("contact", "contact", circle=False)
    build_feed(posts)

    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: {}/sitemap.xml\n".format(SITE_URL))
    urls = (["index.html", "writing.html", "library.html", "about.html",
             "legacy-circle.html", "contact.html"]
            + ["library/{}.html".format(s) for s, _, _ in LIBRARY
               if not library_is_draft(s)]
            + [p["url"] for p in posts])
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "\n".join("  <url><loc>{}/{}</loc></url>".format(SITE_URL.rstrip("/"), u) for u in urls)
          + "\n</urlset>\n")

    print("Built {} pieces into public/".format(len(posts)))


if __name__ == "__main__":
    main()
