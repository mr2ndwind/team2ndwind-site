# team2ndwind.com (T2W Fit Studio / Team 2nd Wind)

Static site built the same way as the T2W Elite site (mr2ndwind/t2welite-site). Forms, calendars, alerts and tracking run through GoHighLevel. Replaces the GHL Vibe Studio build.

## How it works
- `content/pages/*.html`: page bodies (header block, then `---`, then HTML)
- `content/articles/*.md`: blog articles (header block, then `---`, then light markdown)
- `content/resources.json`: free-guide (lead magnet) pages at /resources/<slug>/
- `content/faq.json`: every FAQ answer, used by `{{faq:Question|Question}}`
- `config.json`: logo, GHL form IDs, calendar IDs, links, Jotform ID
- `src/site.css`: all styling (brand amber #FEA82F on black)
- `build.py`: run `python3 build.py` to regenerate `docs/`, which GitHub Pages serves

Every old Vibe URL (67 paths, including all /blog, /blog/category, /resources, /cancel, /pause) exists at the same path, so QR codes and Google links keep working.

## Page tokens
- `{{form:KEY}}` native GHL form from `config.json > forms.KEY` (blank ID shows a safe call/text fallback box)
- `{{form:KEY?a=b}}` same, with URL parameters (e.g. lead_magnet for Resource Download)
- `{{booking:KEY}}` native GHL calendar from `config.json > booking.KEY`
- `{{jotform}}` the pause/cancel Jotform (signature capture)
- `{{faq:...}}`, `{{success}}`, `{{stacks:...}}`, `{{resources:...}}`, `{{visit}}`, `{{reviews}}`, `{{cta:Title|Text}}`, `{{blog_grid}}`, `{{img:path}}`

## Forms on the site
| Page(s) | Form | Status |
|---|---|---|
| /contact, /contact-us, /free-trial, /assessment, /coach, /corporate-wellness | GHL: T2W Fit & Performance Inquiry Form (BpXKtCfymiNDViuXWVyi) | Live form |
| /free-trial | GHL calendar: T2W Free Trial / Intro Session (NJ1RN0xz5z6dLWBtFJzh) | Live calendar |
| /resources/* (7 guides) | GHL: T2W Resource Download Request (rtwnhNCHKmknXpynDQdE) with lead_magnet + resource_category | Live form |
| /cancel, /pause | Jotform 252755211236048 (captures signature) | Live form |
| /refer, /refer-a-friend | GHL: T2W Referral Form | TO BUILD, then paste ID into config.json > forms.referral |
| /new-caney | GHL: T2W New Caney Interest List | TO BUILD, then forms.new_caney |
| /community | GHL: T2W Community Event RSVP | TO BUILD, then forms.community_rsvp |

## Go-live
1. Create GitHub repo mr2ndwind/team2ndwind-site, push, Settings > Pages > Deploy from branch `main`, folder `/docs`.
2. Preview at mr2ndwind.github.io/team2ndwind-site/ and test every form (see checklist in the delivery notes).
3. Set `custom_domain` to `team2ndwind.com` in config.json, rebuild, push.
4. DNS: point team2ndwind.com A records to GitHub Pages (185.199.108.153 / .109.153 / .110.153 / .111.153) and www CNAME to mr2ndwind.github.io. Remove the domain from the GHL Vibe project first. Keep links.team2ndwind.com on GHL (forms and calendars depend on it).
5. GitHub Pages > Enforce HTTPS once the certificate issues.
6. Search Console: submit https://team2ndwind.com/sitemap.xml.

Rollback: re-attach team2ndwind.com to the Vibe project in GHL and revert DNS. The Vibe project is untouched.

## Known follow-ups
- Images still load from vibe.filesafe.space. Before deleting the Vibe project, move them into GHL Media Storage (or this repo) and update `config.json > img`.
- Hybrid Coaching ($299) links to Book Free Consultation because no $299 payment link was found. Add the link when available.
