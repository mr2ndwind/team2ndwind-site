#!/usr/bin/env python3
"""Build the Team 2nd Wind / T2W Fit Studio static site into docs/ (served by GitHub Pages).

Same system as the T2W Elite site (mr2ndwind/t2welite-site):
  content/pages/*.html      page bodies with a small header block (key: value lines, then ---)
  content/articles/*.md     blog articles (key: value header, then ---, then light markdown)
  content/resources.json    free guide (lead magnet) pages -> /resources/<slug>/
  content/faq.json          every FAQ answer, referenced from pages with {{faq:Question|Question}}
  config.json               GHL form IDs, calendar IDs, links, logo
Run:  python3 build.py
All internal links are written relative ({{root}}) so the site works on the GitHub preview URL
(mr2ndwind.github.io/team2ndwind-site/) and on the real domain (team2ndwind.com).

Page tokens
  {{root}}                    relative path to site root
  {{img:attachments/x.png}}   image from the image host in config.json > img
  {{form:KEY}}                native GHL form (config.json > forms.KEY). Blank ID = safe fallback box
  {{form:KEY?a=b&c=d}}        same, with URL parameters (hidden-field values, e.g. lead_magnet)
  {{booking:KEY}}             native GHL calendar embed (config.json > booking.KEY)
  {{faq:Q1|Q2|...}}           FAQ accordion + FAQPage schema, answers from content/faq.json
  {{success}}                 member success strip
  {{stacks:slug,slug}}        Thorne wellness stack tiles
  {{resources:slug,slug}}     free guide tiles
  {{visit}}                   map + visit/call block
  {{reviews}}                 GHL reputation (reviews) widget
  {{cta:Title|Text}}          closing CTA band (InBody / Assessment / Memberships)
  {{blog_grid}}               article list with category filters
"""
import html, json, math, pathlib, re, shutil

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "docs"
CFG = json.loads((ROOT / "config.json").read_text())
SITE_URL = CFG["site_url"]
IMG_MAP = CFG.get("img_map", {})

def img_url(p):
    """Resolve a content image path to its hosted URL (GHL Media Storage map, falls back to legacy base)."""
    return IMG_MAP.get(p) or (CFG["img"] + p)
FAQ = json.loads((ROOT / "content" / "faq.json").read_text())
RESOURCES = json.loads((ROOT / "content" / "resources.json").read_text())

STACKS = {
    "foundational-health": "Foundational Health", "metabolic-energy": "Metabolic Energy", "lean-muscle": "Lean Muscle",
    "athlete-performance": "Athlete Performance", "recovery-joint": "Recovery & Joint", "sleep-stress": "Sleep & Stress",
    "womens-performance": "Women's Performance", "longevity-40": "Longevity 40+", "hormone-optimize": "Hormone Optimize",
    "immune-resilience": "Immune Resilience", "elite-youth": "Elite Youth", "gut-reset": "Gut Reset",
}
PEOPLE = [("Debbie", "attachments/d05a8a10-0875-41b9-895a-9cdb5c0c4137.png", "Build &rarr; Sweat"),
          ("CC", "attachments/aa84b7ea-bc56-4d5c-aef0-ec417703aabb.png", "Sweat &rarr; Flex"),
          ("Gary", "attachments/79f9641e-d21e-4a66-b409-87feb117bf2f.png", "Committed Club"),
          ("Jess", "attachments/9f0915d4-e440-4869-9403-2db3d2702b25.jpg", "Build &rarr; Sweat"),
          ("Soven", "attachments/8739fc61-f0f3-441e-85bb-b24af6542a7a.png", "Leaderboard Achievement")]


def esc(s):
    return html.escape(s, quote=True)


def parse_header(text):
    head, body = text.split("---\n", 1)
    meta = {}
    for line in head.strip().splitlines():
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    return meta, body


def form_embed(spec):
    key, _, query = spec.partition("?")
    fid = CFG["forms"].get(key)
    if not fid:
        return ('<div class="form-pending"><p><strong>This form is moving to our new system.</strong></p>'
                f'<p class="muted">In the meantime, call or text <a href="tel:{CFG["phone_tel"]}">{CFG["phone_display"]}</a> '
                f'or email <a href="mailto:{CFG["email"]}">{CFG["email"]}</a> and our team will take care of you.</p>'
                '<a class="btn" href="{{root}}contact/">Contact Our Team</a></div>')
    h = CFG["form_heights"].get(key, 900)
    src = f'{CFG["form_host"]}/widget/form/{fid}' + (f"?{query}" if query else "")
    return (f'<div class="form-box" style="min-height:{h}px"><iframe src="{esc(src)}" id="inline-{fid}" '
            f'data-layout="{{\'id\':\'INLINE\'}}" data-trigger-type="alwaysShow" data-trigger-value="" '
            f'data-activation-type="alwaysActivated" data-activation-value="" data-deactivation-type="neverDeactivate" '
            f'data-deactivation-value="" data-form-name="{esc(key)}" data-height="{h}" data-layout-iframe-id="inline-{fid}" '
            f'data-form-id="{fid}" title="{esc(key)} form" '
            f'style="width:100%;height:100%;min-height:{h}px;border:none;border-radius:8px"></iframe></div>')


def jotform_embed(fid):
    return (f'<div class="embed"><iframe id="JotFormIFrame-{fid}" title="T2W membership pause and cancellation request" '
            f'src="https://form.jotform.com/{fid}" allow="geolocation; microphone; camera; fullscreen" '
            f'style="min-width:100%;max-width:100%;height:1600px;border:none" scrolling="yes"></iframe></div>'
            f'<script src="https://cdn.jotfor.ms/s/umd/latest/for-form-embed-handler.js"></script>'
            f'<script>window.jotformEmbedHandler&&window.jotformEmbedHandler("iframe[id=\'JotFormIFrame-{fid}\']","https://form.jotform.com/")</script>')


def booking_embed(key):
    cid = CFG["booking"][key]
    return (f'<div class="embed"><iframe src="{CFG["form_host"]}/widget/booking/{cid}" id="{cid}_booking" '
            f'scrolling="no" style="width:100%;border:none;overflow:hidden;min-height:760px" '
            f'title="Book an appointment"></iframe></div>'
            f'<script src="{CFG["form_host"]}/js/form_embed.js" type="text/javascript"></script>')


FAQ_USED = []


def faq_block(spec):
    qs = [q.strip() for q in spec.split("|") if q.strip()]
    out = []
    for q in qs:
        if q not in FAQ:
            raise SystemExit(f"FAQ answer missing for: {q}")
        FAQ_USED.append((q, FAQ[q]))
        out.append(f"<details><summary>{esc(q)}</summary><p>{esc(FAQ[q])}</p></details>")
    return '<div class="faq">' + "".join(out) + "</div>"


def success_strip():
    return '<div class="people">' + "".join(
        f'<div class="person"><img src="{img_url(src)}" alt="{n}, T2W member" loading="lazy"><h3>{n}</h3><p>{t}</p></div>'
        for n, src, t in PEOPLE) + "</div>"


def stacks(spec):
    return '<div class="tiles">' + "".join(
        f'<a class="tile" href="{CFG["thorne"]}/stack/t2w-{s}" rel="noopener" target="_blank"><small>Thorne Stack</small>'
        f'<b>{esc(STACKS[s])}</b><span>SHOP STACK &rarr;</span></a>' for s in spec.split(",")) + "</div>"


def resource_tiles(spec):
    return '<div class="tiles">' + "".join(
        f'<a class="tile" href="{{{{root}}}}resources/{s}/"><small>{esc(RESOURCES[s]["category"])}</small>'
        f'<b>{esc(RESOURCES[s]["title"])}</b><span>FREE DOWNLOAD &rarr;</span></a>' for s in spec.split(",")) + "</div>"


def visit_block():
    return f"""<div class="split">
<iframe class="map" src="{CFG['map_embed']}" loading="lazy" title="Map to T2W Fit Studio" referrerpolicy="no-referrer-when-downgrade"></iframe>
<div class="grid" style="gap:16px">
<div class="card accent"><span class="eyebrow">Visit Us</span><h3>3074 N Aspen Ave, Suite 110<br>Broken Arrow, OK 74012</h3><p class="muted">Across from Battle Creek Church</p>
<a class="btn ghost sm" href="{CFG['map_link']}" rel="noopener" target="_blank">Get Directions</a></div>
<div class="card accent"><span class="eyebrow">Call Us</span><h3><a href="tel:{CFG['phone_tel']}" style="text-decoration:none">{CFG['phone_display']}</a></h3><p class="muted" style="margin:0">We're here to help!</p></div>
</div></div>"""


def reviews():
    return (f'<iframe src="{CFG["review_widget"]}" title="T2W reviews" frameborder="0" scrolling="no" '
            'style="min-width:100%;width:100%;min-height:420px;border:0"></iframe>'
            '<script src="https://reputationhub.site/reputation/assets/review-widget.js" type="text/javascript"></script>')


def cta_band(spec):
    title, _, text = spec.partition("|")
    return (f'<section class="cta"><div class="wrap"><h2>{esc(title)}</h2><p>{esc(text)}</p>'
            f'<div class="btns" style="justify-content:center">'
            f'<a class="btn" href="{CFG["booking_links"]["inbody"]}" rel="noopener">Book Free InBody Scan</a>'
            f'<a class="btn ghost" href="{{{{root}}}}assessment/">Take Wellness Assessment</a>'
            f'<a class="btn ghost" href="{{{{root}}}}memberships/">Explore Memberships</a></div></div></section>')


def md_to_html(md):
    """Light markdown: ## h2, ### h3, - list, > LABEL | text callout, ![alt](src) image, [text](href) links in paragraphs."""
    out, para, lst = [], [], []

    def inline(s):
        s = esc(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        return re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()
        if lst:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in lst) + "</ul>"); lst.clear()

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush(); continue
        if line.startswith("### "):
            flush(); out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            flush(); out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("![") and "](" in line:
            flush()
            alt, src = re.match(r"!\[(.*?)\]\((.*?)\)", line).groups()
            src = img_url(src) if not src.startswith("http") else src
            out.append(f'<img src="{esc(src)}" alt="{esc(alt)}" loading="lazy" style="border-radius:10px;margin:24px 0">')
        elif line.startswith("- "):
            if para:
                out.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()
            lst.append(line[2:])
        elif line.startswith("> "):
            flush()
            label, _, txt = line[2:].partition(" | ")
            cls = "callout key" if "COACH" in label else "callout"
            out.append(f'<div class="{cls}"><b>{esc(label)}</b>{inline(txt)}</div>')
        else:
            if lst:
                flush()
            para.append(line.strip())
    flush()
    return "\n".join(out)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def layout(title, desc, path, body, active=None, schema=None, noindex=False):
    depth = path.count("/")
    root = "../" * depth
    canon = f"{SITE_URL}/{path}"
    on = ' class="on"'

    def link(n, p):
        return f'<a href="{root}{p}"{on if active == p else ""}>{n}</a>'

    def dd(label, items):
        o = " on" if active in [p for _, p in items] else ""
        return (f'<div class="dd"><button class="dd-btn{o}" type="button">{label}</button><div class="dd-menu">'
                + "".join(link(n, p) for n, p in items) + "</div></div>")

    programs = [("All Programs", "programs/"), ("Athlete Performance", "athlete-performance/"),
                ("Youth Athletes", "youth-athlete-development/"), ("Family Membership", "family-membership/"),
                ("Wellhub &amp; ClassPass", "wellhub-classpass/")]
    wellness = [("Wellness Center", "wellness/"), ("InBody Scan", "inbody/"), ("Recovery", "recovery/"),
                ("Women's Wellness", "womens-health/"), ("Longevity", "longevity/"), ("Supplements", "supplements/"),
                ("Corporate Wellness", "corporate-wellness/")]
    nav = (dd("Programs", [("Start Here", "start/")] + programs) + link("Memberships", "memberships/")
           + link("Schedule", "schedule/") + dd("Wellness", wellness) + link("Community", "community/")
           + link("Blog", "blog/") + link("About", "about/") + link("Contact", "contact/"))
    schemas = schema if isinstance(schema, list) else ([schema] if schema else [])
    ld = "".join(f'<script type="application/ld+json">{json.dumps(s)}</script>' for s in schemas)
    robots = '<meta name="robots" content="noindex,follow">' if noindex else ""
    page = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">{robots}
<meta property="og:type" content="website"><meta property="og:site_name" content="Team 2nd Wind">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canon}"><meta property="og:image" content="{CFG['og_image']}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:site" content="@T2WFitStudio">
<meta name="theme-color" content="#0A0A0B">
<link rel="icon" href="{CFG['logo']}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Oswald:wght@500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/site.css">
{ld}
</head><body>
<header class="top"><div class="wrap">
<a class="logo" href="{root or './'}" aria-label="Team 2nd Wind home"><img src="{CFG['logo']}" alt="T2W Fit Studio" width="140" height="52"></a>
<button class="menu-btn" aria-expanded="false" aria-controls="nav">MENU</button>
<nav class="nav" id="nav">{nav}<a class="btn sm" href="{root}free-trial/">Start Free Trial</a></nav>
</div></header>
<main>
{body}
</main>
<footer><div class="wrap">
<div class="foot">
<div><img src="{CFG['logo']}" alt="T2W Fit Studio" width="150" height="56" style="height:56px;width:auto;margin-bottom:16px">
<p class="muted">Train With Purpose. Show Up For Yourself. Build Your Second Wind.</p>
<p class="tag">FIND YOUR 2ND WIND.</p>
<a class="btn sm" href="{root}free-trial/">Claim 7-Day Free Trial</a></div>
<div><h4>Train</h4><ul>
<li><a href="{root}start/">Start Here</a></li>
<li><a href="{root}programs/">Programs</a></li>
<li><a href="{root}memberships/">Memberships</a></li>
<li><a href="{root}schedule/">Schedule</a></li>
<li><a href="{root}athlete-performance/">Athlete Performance</a></li>
<li><a href="{root}youth-athlete-development/">Youth Athletes</a></li>
<li><a href="{root}family-membership/">Family Membership</a></li>
<li><a href="{root}results/">Results</a></li>
<li><a href="{root}blog/">Blog</a> &middot; <a href="{root}about/">About</a> &middot; <a href="{root}faq/">FAQ</a></li>
<li><a href="{CFG['elite_url']}" rel="noopener">T2W Elite Basketball</a></li></ul></div>
<div><h4>Wellness</h4><ul>
<li><a href="{root}assessment/">Wellness Assessment</a></li>
<li><a href="{root}inbody/">InBody Scan</a></li>
<li><a href="{root}wellness/">Wellness Center</a></li>
<li><a href="{root}recovery/">Recovery</a></li>
<li><a href="{root}womens-health/">Women's Wellness</a></li>
<li><a href="{root}longevity/">Longevity</a></li>
<li><a href="{root}corporate-wellness/">Corporate Wellness</a></li>
<li><a href="{root}supplements/">Supplements</a></li></ul></div>
<div><h4>Members &amp; Contact</h4><ul>
<li><a href="{root}member-hub/">Member Hub</a></li>
<li><a href="{root}community/">T2W Community</a></li>
<li><a href="{root}refer/">Refer &amp; Earn</a></li>
<li><a href="{root}pause/">Pause Membership</a></li>
<li><a href="{root}cancel/">Cancel Membership</a></li>
<li><a href="{root}new-caney/">New Caney, TX &mdash; Coming Soon</a></li>
<li><a href="tel:{CFG['phone_tel']}">{CFG['phone_display']}</a></li>
<li>3074 N Aspen Ave, Suite 110<br>Broken Arrow, OK 74012</li>
<li><a href="{CFG['facebook']}" rel="noopener">Facebook</a> &middot; <a href="{CFG['instagram']}" rel="noopener">Instagram</a></li></ul></div>
</div>
<div class="legal"><span>&copy; <span id="yr">2026</span> Team 2nd Wind LLC | T2W Fit Studio. All rights reserved.</span>
<span><a href="{root}faq/">FAQ</a> &middot; <a href="{root}terms-of-use/">Terms of Use</a> &middot; <a href="{root}privacy-policy/">Privacy Policy</a></span></div>
</div></footer>
<script>
document.getElementById('yr').textContent=new Date().getFullYear();
var b=document.querySelector('.menu-btn'),n=document.getElementById('nav');
b.addEventListener('click',function(){{var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o)}});
</script>
<script src="{CFG['form_host']}/js/form_embed.js"></script>
</body></html>
"""
    page = page.replace("{{root}}", root)
    dest = OUT / path / "index.html" if path else OUT / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page)
    write_ghl_snippet(page, path, root, noindex)
    return None if noindex else canon


def write_ghl_snippet(page, path, root, noindex):
    """Self-contained snippet for a GHL Custom Code element (one per page, in docs/_ghl/)."""
    if noindex and not path.strip('/') in ('pause','cancel'):
        return
    css = (ROOT / "src" / "site.css").read_text()
    body = re.search(r"<body>(.*)</body>", page, re.S).group(1)
    fonts = re.search(r'<link href="https://fonts.googleapis.com[^>]+>', page).group(0)

    def fix(m):
        attr, val = m.group(1), m.group(2)
        if re.match(r"(https?:|tel:|mailto:|#|//|data:)", val):
            return m.group(0)
        v = val
        while v.startswith("../"):
            v = v[3:]
        if v in ("./", ""):
            v = ""
        return f'{attr}="{SITE_URL}/{v}"'

    body = re.sub(r'(href|src)="([^"]*)"', fix, body)
    # GHL: Jotform's embed handler hides the iframe until it resizes; keep the fixed-height iframe visible instead
    body = re.sub(r'<script src="https://cdn\.jotfor\.ms/[^"]*"></script>', '', body)
    body = re.sub(r'<script>window\.jotformEmbedHandler[^<]*</script>', '', body)
    snippet = (f'{fonts}\n<style>\n{css}\n</style>\n'
               f'<div class="t2w-ghl" style="background:#0A0A0B">\n{body}\n</div>\n')
    name = slugify(path) if path else "home"
    d = OUT / "_ghl"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.html").write_text(snippet)


def render_tokens(body):
    FAQ_USED.clear()
    body = re.sub(r"\{\{faq:(.+?)\}\}", lambda m: faq_block(m.group(1)), body)
    body = re.sub(r"\{\{form:([a-z_]+(?:\?[^}]*)?)\}\}", lambda m: form_embed(m.group(1)), body)
    body = body.replace("{{jotform}}", jotform_embed(CFG["jotform_pause_cancel"]))
    body = re.sub(r"\{\{booking:([a-z]+)\}\}", lambda m: booking_embed(m.group(1)), body)
    body = re.sub(r"\{\{stacks:([a-z0-9,-]+)\}\}", lambda m: stacks(m.group(1)), body)
    body = re.sub(r"\{\{resources:([a-z0-9,-]+)\}\}", lambda m: resource_tiles(m.group(1)), body)
    body = re.sub(r"\{\{cta:(.+?)\}\}", lambda m: cta_band(m.group(1)), body)
    body = re.sub(r"\{\{img:(.+?)\}\}", lambda m: img_url(m.group(1)), body)
    body = body.replace("{{success}}", success_strip()).replace("{{visit}}", visit_block()).replace("{{reviews}}", reviews())
    body = (body.replace("{{inbody}}", CFG["booking_links"]["inbody"]).replace("{{consult}}", CFG["booking_links"]["consult"])
            .replace("{{phone}}", CFG["phone_display"]).replace("{{tel}}", CFG["phone_tel"]))
    faq_schema = None
    if FAQ_USED:
        faq_schema = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ_USED]}
    return body, faq_schema


def post_card(a):
    img = f'<img src="{img_url(a["image"])}" alt="" loading="lazy">' if a.get("image") else ""
    return (f'<a class="post-card" data-c="{slugify(a["category"])}" href="{{{{root}}}}blog/{a["slug"]}/" style="padding:0;overflow:hidden">'
            f'{img}<div style="padding:22px;display:flex;flex-direction:column;flex:1">'
            f'<span class="meta">{esc(a["category"])} &middot; {esc(a["date"])}</span>'
            f'<h3>{esc(a["title"])}</h3><p>{esc(a["description"])}</p><span class="more">READ ARTICLE &rarr;</span></div></a>')


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    shutil.copy(ROOT / "src" / "site.css", OUT / "assets" / "site.css")
    urls = []

    # Articles
    arts = []
    for f in sorted((ROOT / "content" / "articles").glob("*.md")):
        meta, body = parse_header(f.read_text())
        meta["slug"], meta["body"] = f.stem, body
        arts.append(meta)
    arts.sort(key=lambda a: a["iso"], reverse=True)

    for a in arts:
        g = a.get("guide")
        guide = RESOURCES.get(g) if g else None
        guide_box = (f'<div class="card accent" style="margin:28px 0"><span class="eyebrow">Free Guide</span><h3>{esc(guide["title"])}</h3>'
                     f'<p class="muted">{esc(guide["intro"])}</p><a class="btn" href="{{{{root}}}}resources/{g}/">Download the Free Guide</a></div>') if guide else ""
        img = f'<img src="{img_url(a["image"])}" alt="{esc(a["title"])}" style="border-radius:10px;margin-bottom:28px">' if a.get("image") else ""
        body = f"""<section class="page-hero"><div class="wrap article">
<div class="crumbs"><a href="{{{{root}}}}">Home</a> / <a href="{{{{root}}}}blog/">Blog</a> / <a href="{{{{root}}}}blog/category/{slugify(a['category'])}/">{esc(a['category'].title())}</a></div>
<span class="eyebrow">{esc(a['category'])}</span><h1 style="font-size:clamp(2rem,4.6vw,3.2rem)">{esc(a['title'])}</h1>
<p class="lead">{esc(a['description'])}</p>
<div class="post-meta">By {esc(a.get('author', 'Team 2nd Wind'))} &middot; {esc(a['date'])} &middot; {esc(a['read'])}</div></div></section>
<section><div class="wrap article">{img}{guide_box if a.get('guide_top', 'yes') == 'yes' else ''}{md_to_html(a['body'])}
{guide_box}
<div class="card" style="margin-top:28px"><h3>Ready to Train With Purpose?</h3><p class="muted">Start with a free InBody scan or our 60-second Wellness Assessment and we'll point you to the right program.</p>
<div class="btns" style="margin-top:12px"><a class="btn" href="{{{{root}}}}free-trial/">Book an Intro Session</a><a class="btn ghost" href="{{{{root}}}}assessment/">Take Wellness Assessment</a></div></div>
<p class="disclaimer">The information in this article is general education and is not individualized medical advice. Consult a qualified professional before beginning any new fitness or nutrition program.</p>
</div></section>"""
        schema = {"@context": "https://schema.org", "@type": "Article", "headline": a["title"], "datePublished": a["iso"],
                  "author": {"@type": "Organization", "name": "Team 2nd Wind"},
                  "publisher": {"@type": "Organization", "name": "Team 2nd Wind", "logo": {"@type": "ImageObject", "url": CFG["logo"]}},
                  "description": a["description"]}
        if a.get("image"):
            schema["image"] = img_url(a["image"])
        body, _ = render_tokens(body)
        urls.append(layout(a["seo"], a["seo_description"], f"blog/{a['slug']}/", body, active="blog/", schema=schema))

    cats = []
    for a in arts:
        if a["category"] not in cats:
            cats.append(a["category"])
    all_cats = ["Fitness", "Nutrition", "Recovery", "Youth Sports Performance", "Basketball Development",
                "Strength Training", "Fat Loss", "Healthy Lifestyle"]
    filters = '<div class="filters" id="filters"><button class="on" data-c="all">All</button>' + "".join(
        f'<button data-c="{slugify(c)}">{esc(c.title())}</button>' for c in all_cats if c.upper() in [x.upper() for x in cats]) + "</div>"
    grid_js = ("<script>document.querySelectorAll('#filters button').forEach(function(b){b.onclick=function(){"
               "document.querySelectorAll('#filters button').forEach(function(x){x.classList.remove('on')});b.classList.add('on');"
               "document.querySelectorAll('#posts .post-card').forEach(function(p){p.style.display=(b.dataset.c==='all'||p.dataset.c===b.dataset.c)?'':'none'})}})</script>")
    blog_grid = filters + '<div class="grid g3" id="posts">' + "".join(post_card(a) for a in arts) + "</div>" + grid_js

    # Category pages (kept at the old URLs)
    for c in all_cats:
        items = [a for a in arts if a["category"].upper() == c.upper()]
        grid = ('<div class="grid g3">' + "".join(post_card(a) for a in items) + "</div>") if items else \
            '<div class="card center"><p class="muted" style="margin:0">New articles in this category are coming soon.</p><a class="btn sm" href="{{root}}blog/">View All Articles</a></div>'
        body = (f'<section class="page-hero"><div class="wrap"><div class="crumbs"><a href="{{{{root}}}}">Home</a> / <a href="{{{{root}}}}blog/">Blog</a></div>'
                f'<span class="eyebrow">Blog Category</span><h1>{esc(c)}</h1><p class="lead">Articles and coaching tips on {esc(c.lower())} from the Team 2nd Wind coaches in Broken Arrow, OK.</p></div></section>'
                f'<section><div class="wrap">{grid}</div></section>')
        body, _ = render_tokens(body)
        urls.append(layout(f"{c} Tips | T2W Fit Broken Arrow", f"{c} articles and coaching tips from the Team 2nd Wind coaches in Broken Arrow, OK.",
                           f"blog/category/{slugify(c)}/", body, active="blog/", noindex=not items))

    # Resources (lead magnets)
    for slug, r in RESOURCES.items():
        q = f"lead_magnet={r['lead_magnet'].replace(' ', '%20')}&resource_category={r['category'].replace(' ', '%20')}"
        bullets = "".join(f"<li>{esc(b)}</li>" for b in r["bullets"])
        body = f"""<section class="page-hero"><div class="wrap">
<div class="crumbs"><a href="{{{{root}}}}">Home</a> / <a href="{{{{root}}}}blog/">Resources</a> / {esc(r['category'])}</div>
<span class="eyebrow">{esc(r['category'])} &middot; Free Download</span><h1>{esc(r['title'])}</h1><p class="lead">{esc(r['intro'])}</p></div></section>
<section><div class="wrap split">
<div><span class="eyebrow">What You'll Get</span><h2>Inside the Guide</h2><ul class="checks">{bullets}</ul>
<div class="card" style="margin-top:28px"><h3>Ready for Coaching Beyond the Guide?</h3><p class="muted">Take the next step in your fitness journey with our expert coaching programs.</p>
<div class="btns" style="margin-top:10px"><a class="btn sm" href="{{{{root}}}}free-trial/">Book Intro</a><a class="btn ghost sm" href="{{{{root}}}}memberships/">View Memberships</a></div></div></div>
<div><span class="eyebrow">Where Should We Send It?</span><p>Fill out the form to get instant access.</p>{{{{form:resource?{q}}}}}</div>
</div></section>"""
        body, _ = render_tokens(body)
        urls.append(layout(r["seo"], r["intro"], f"resources/{slug}/", body, active="blog/"))

    # Pages
    for f in sorted((ROOT / "content" / "pages").glob("*.html")):
        meta, body = parse_header(f.read_text())
        body = body.replace("{{blog_grid}}", blog_grid)
        body, faq_schema = render_tokens(body)
        schema = [faq_schema] if faq_schema else []
        if meta["path"] == "":
            schema.append({"@context": "https://schema.org", "@type": "ExerciseGym", "name": "T2W Fit Studio",
                           "alternateName": "Team 2nd Wind", "url": SITE_URL, "telephone": "+1-918-918-3234", "image": CFG["logo"],
                           "email": CFG["email"],
                           "address": {"@type": "PostalAddress", "streetAddress": "3074 N Aspen Ave Suite 110",
                                       "addressLocality": "Broken Arrow", "addressRegion": "OK", "postalCode": "74012", "addressCountry": "US"},
                           "areaServed": ["Broken Arrow", "Tulsa", "Bixby", "Jenks", "Owasso"],
                           "sameAs": [CFG["facebook"], CFG["instagram"]]})
        urls.append(layout(meta["title"], meta["description"], meta["path"], body,
                           active=meta.get("nav", meta["path"]), schema=schema, noindex=meta.get("noindex") == "yes"))

    # 404, robots, sitemap, .nojekyll, CNAME
    (OUT / "404.html").write_text((OUT / "not-found" / "index.html").read_text().replace('href="../', 'href="/').replace('src="../', 'src="/'))
    shutil.rmtree(OUT / "not-found")
    urls = sorted({u for u in urls if u and "not-found" not in u})
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    (OUT / ".nojekyll").write_text("")
    if CFG.get("custom_domain"):
        (OUT / "CNAME").write_text(CFG["custom_domain"] + "\n")
    print(f"Built {len(urls)} indexable pages into {OUT}")


if __name__ == "__main__":
    build()
