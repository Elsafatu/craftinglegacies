# Crafting Legacies

craftinglegacies.com — a static publishing site. No frameworks, no dependencies,
nothing to maintain. You write Markdown, run one command, and get finished HTML.

## What's here

    content/posts/     your articles, one Markdown file each
    content/pages/     About, The Legacy Circle, Contact
    theme/             the design — styles.css and base.html
    build.py           the build script (Python standard library only)
    public/            generated output — never edit this by hand

## Publishing an article

**1. Create the file** in `content/posts/`, named `YYYY-MM-DD-short-title.md`.
The date sets publication date; the rest becomes the web address.

**2. Write it**, starting with the header block:

    ---
    title: When there is no will
    date: 2026-04-19
    subject: Estates & succession
    standfirst: One sentence that makes someone want to read on.
    ---

    Your first paragraph starts here.

    ## A subheading

    More writing. Leave a blank line between paragraphs.

**3. Build.** From this folder:

    python3 build.py

**4. Preview** before it goes anywhere:

    python3 -m http.server -d public 8000

Then open http://localhost:8000

**5. Publish** by pushing to GitHub. Live in about a minute.

## Holding a piece at the top

Add `featured: true` to the header block and that article stays first on the
homepage and the writing index regardless of date. Everything else falls in date
order beneath it. Remove the line when you want it to drop back into sequence.

Only mark one piece at a time — two featured articles means neither is.

## Formatting you can use

    ## Heading            (## for sections, ### for sub-sections)
    **bold**  *italic*
    [link text](https://example.com)
    > A pull quote
    - Bulleted item
    1. Numbered item
    ---                   (a horizontal rule)

That's the whole vocabulary, deliberately. It covers essays and nothing more, so
there is nothing to go wrong.

## Going live on Cloudflare Pages

Your domain is already at Cloudflare, which makes this straightforward.

1. Put this folder in a GitHub repository (github.com — free).
2. In the Cloudflare dashboard: **Workers & Pages → Create → Pages →
   Connect to Git**, and choose the repository.
3. Build command: `python3 build.py` — Output directory: `public`
4. Deploy. It goes live at a `.pages.dev` address within a minute.
5. **Custom domains → Set up a domain →** `craftinglegacies.com`. Because the
   domain is registered with Cloudflare, the DNS is configured automatically.

Every push to GitHub republishes the site.

## Making The Legacy Circle work

The signup form is currently visual only. To make it live:

1. Open a free account at buttondown.com or mailerlite.com.
2. Find the form action URL they give you (it looks like
   `https://buttondown.com/api/emails/embed-subscribe/yourname`).
3. Paste it into `SUBSCRIBE_ACTION` near the top of `build.py`.
4. Rebuild. The form starts collecting addresses immediately.

## Changing the look

Everything visual lives in `theme/styles.css`, with the colours defined once at
the top:

    --beige           background
    --warm            secondary background panels
    --ink             body text
    --muted           secondary text
    --rule            hairlines
    --emerald         links and small text
    --emerald-bright  display type, the mark, rules
    --clay            dates and metadata

Change those and the whole site changes with them.

## Before you launch

- Replace the three sample articles in `content/posts/`. They are marked as
  samples in the text — the site should not go live until at least one real
  piece is on it.
- Set up `hello@craftinglegacies.com` (Cloudflare Email Routing does this free —
  it forwards to your existing inbox) or change the address in
  `content/pages/contact.md`.
- Connect the Legacy Circle form.

## Keeping a copy

Once this is on GitHub, GitHub holds the master copy and Cloudflare rebuilds
from it. Until then, the only copy is on your own computer — keep the folder
somewhere you back up.
