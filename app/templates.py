"""Các mẫu hình ảnh (HTML + CSS động) — thiết kế ở khung 1080x1920."""
from __future__ import annotations

import html
import re

TEMPLATE_VERSION = "t2"

CSS = """
:root{--a:#F59E0B;--b:#A855F7;--fg:#F8FAFC;--mut:#A9B4D0}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;overflow:hidden;background:#0A0F1F;color:var(--fg);
 font-family:'Be Vietnam Pro','Noto Sans','Segoe UI','DejaVu Sans',sans-serif;-webkit-font-smoothing:antialiased}
.bg{position:absolute;inset:0;overflow:hidden;background:linear-gradient(165deg,#0A0F1F 0%,#111A38 55%,#1B1238 100%)}
.blob{position:absolute;width:1300px;height:1300px;border-radius:50%}
.live .blob{animation:drift 14s ease-in-out infinite alternate}
.b1{left:-520px;top:-340px;opacity:.50;background:radial-gradient(circle,var(--a) 0%,transparent 62%)}
.b2{right:-640px;top:520px;opacity:.50;background:radial-gradient(circle,var(--b) 0%,transparent 62%)}
.live .b2{animation-duration:18s}
.b3{left:-320px;bottom:-760px;opacity:.30;background:radial-gradient(circle,#22D3EE 0%,transparent 62%)}
.live .b3{animation-duration:22s}
@keyframes drift{from{transform:translate(0,0) scale(1)}to{transform:translate(120px,-90px) scale(1.15)}}
.wrap{position:absolute;inset:0;padding:190px 96px 400px;display:flex;flex-direction:column;justify-content:center;gap:44px}
.center{align-items:center;text-align:center}
.rise{opacity:0;animation:rise .8s cubic-bezier(.2,.8,.2,1) var(--d,0s) both}
@keyframes rise{from{opacity:0;transform:translateY(60px)}to{opacity:1;transform:none}}
.pop{opacity:0;animation:pop .7s cubic-bezier(.2,1.4,.4,1) var(--d,0s) both}
@keyframes pop{from{opacity:0;transform:scale(.6)}to{opacity:1;transform:none}}
.grow{transform-origin:left center;transform:scaleX(0);animation:grow .9s ease-out var(--d,0s) both}
@keyframes grow{to{transform:scaleX(1)}}
.pill{display:inline-block;align-self:flex-start;padding:18px 40px;border-radius:999px;background:rgba(255,255,255,.10);
 border:2px solid rgba(255,255,255,.20);font-size:40px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
.center .pill{align-self:center}
.grad{background:linear-gradient(90deg,var(--a),var(--b));-webkit-background-clip:text;background-clip:text;color:transparent}
h1,h2{font-weight:900;line-height:1.1;white-space:pre-line;word-break:break-word}
.sub{font-size:52px;line-height:1.35;color:var(--mut);font-weight:500;white-space:pre-line}
.foot{position:absolute;left:0;right:0;bottom:250px;text-align:center;font-size:36px;font-weight:600;
 letter-spacing:.16em;text-transform:uppercase;color:var(--mut);opacity:0;animation:rise .8s ease-out 1.2s both}
.cta{align-self:flex-start;margin-top:20px;padding:26px 56px;border-radius:999px;font-size:44px;font-weight:800;color:#0A0F1F;
 background:linear-gradient(90deg,var(--a),var(--b))}
.bar{height:14px;width:240px;border-radius:8px;background:linear-gradient(90deg,var(--a),var(--b))}
.w{display:inline-block;margin-right:.28em;opacity:0;animation:rise .6s cubic-bezier(.2,.8,.2,1) var(--d,0s) both}
ul{list-style:none;display:flex;flex-direction:column;gap:30px}
li{display:flex;align-items:center;gap:36px;padding:34px 40px;border-radius:36px;background:rgba(255,255,255,.07);
 border:2px solid rgba(255,255,255,.12);font-size:54px;font-weight:700;line-height:1.25}
.ico{flex:none;width:112px;height:112px;border-radius:50%;display:flex;align-items:center;justify-content:center;
 font-size:58px;font-weight:900;color:#0A0F1F;background:linear-gradient(135deg,var(--a),var(--b))}
.logo{width:380px;height:380px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:210px;font-weight:900;
 color:#0A0F1F;background:linear-gradient(135deg,var(--a),var(--b));position:relative}
.logo::after{content:"";position:absolute;inset:-70px;border-radius:50%;background:radial-gradient(circle,var(--a) 0%,transparent 68%);
 opacity:.35;z-index:-1;animation:glow 3s ease-in-out infinite alternate}
@keyframes glow{from{transform:scale(.9);opacity:.25}to{transform:scale(1.15);opacity:.5}}
.url{padding:22px 50px;border-radius:999px;border:2px solid rgba(255,255,255,.25);font-size:42px;font-weight:600}
"""

PAGE = """<!doctype html><html lang="vi" style="--a:%%A%%;--b:%%B%%"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@500;700;800;900&display=block" rel="stylesheet">
<style>%%CSS%%</style></head><body class="%%LIVE%%">
<div class="bg"><div class="blob b1"></div><div class="blob b2"></div><div class="blob b3"></div></div>
%%BODY%%</body></html>"""


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def _fs(text: str, steps) -> int:
    longest = max((len(l) for l in str(text).splitlines()), default=0) or 1
    for limit, px in steps:
        if longest <= limit:
            return px
    return steps[-1][1]


def _color(c: str, default: str) -> str:
    return c if re.fullmatch(r"#[0-9a-fA-F]{6}", c or "") else default


def _kicker(s, d=".1s"):
    return f'<div class="pill rise" style="--d:{d}">{esc(s["kicker"])}</div>' if s["kicker"] else ""


def _sub(s, d="1s"):
    return f'<p class="sub rise" style="--d:{d}">{esc(s["sub"])}</p>' if s["sub"] else ""


def _foot(st):
    return f'<div class="foot">{esc(st["brand"])}</div>' if st.get("brand") else ""


def hero(s, st):
    fs = _fs(s["headline"], [(10, 220), (16, 176), (26, 140), (40, 112), (999, 92)])
    return f"""<div class="wrap">{_kicker(s,".2s")}
<h1 class="grad rise" style="--d:.5s;font-size:{fs}px">{esc(s["headline"])}</h1>
{_sub(s,"1s")}<div class="cta pop" style="--d:1.4s">{esc(st["brand"])}</div></div>"""


def stat(s, st):
    fs = _fs(s["headline"], [(3, 380), (5, 250), (7, 200), (10, 160), (999, 120)])
    return f"""<div class="wrap center">{_kicker(s,".1s")}
<h1 class="grad pop" style="--d:.4s;font-size:{fs}px;white-space:nowrap">{esc(s["headline"])}</h1>
<div class="bar grow" style="--d:1s"></div>{_sub(s,"1.2s")}</div>{_foot(st)}"""


def statement(s, st):
    words = s["headline"].split()
    step = min(0.07, 1.6 / max(len(words), 1))
    spans = "".join(f'<span class="w" style="--d:{0.3 + i * step:.2f}s">{esc(w)}</span>' for i, w in enumerate(words))
    fs = _fs(s["headline"], [(40, 100), (80, 84), (140, 72), (999, 60)])
    return f"""<div class="wrap">{_kicker(s,".1s")}
<h2 style="font-size:{fs}px">{spans}</h2>{_sub(s,"1.8s")}</div>{_foot(st)}"""


def listing(s, st):
    fs = _fs(s["headline"], [(18, 104), (30, 86), (999, 70)])
    rows = []
    for i, raw in enumerate(s["items"][:5]):
        m = re.match(r"^(\S)\s+(.*)$", raw)
        if m and not m.group(1).isalnum():
            icon, text = m.group(1), m.group(2)
        else:
            icon, text = str(i + 1), raw
        rows.append(f'<li class="rise" style="--d:{0.7 + i * 0.28:.2f}s"><span class="ico">{esc(icon)}</span><span>{esc(text)}</span></li>')
    return f"""<div class="wrap">{_kicker(s,".1s")}
<h2 class="grad rise" style="--d:.3s;font-size:{fs}px">{esc(s["headline"])}</h2>
<ul>{"".join(rows)}</ul></div>{_foot(st)}"""


def outro(s, st):
    name = s["headline"] or st["brand"]
    initial = (name.strip()[:1] or "A").upper()
    tag = s["sub"] or st.get("tagline", "")
    url = f'<div class="url rise" style="--d:1.2s">{esc(st["url"])}</div>' if st.get("url") else ""
    return f"""<div class="wrap center" style="gap:50px"><div class="logo pop" style="--d:.2s">{esc(initial)}</div>
<h1 class="grad rise" style="--d:.7s;font-size:{_fs(name,[(12,130),(22,100),(999,78)])}px">{esc(name)}</h1>
<p class="sub rise" style="--d:1s">{esc(tag)}</p>{url}</div>"""


RENDERERS = {"hero": hero, "stat": stat, "statement": statement, "list": listing, "outro": outro}


def build_html(scene: dict, st: dict) -> str:
    body = RENDERERS[scene["template"]](scene, st)
    return (
        PAGE.replace("%%CSS%%", CSS)
        .replace("%%LIVE%%", "live" if st.get("continuous") else "")
        .replace("%%A%%", _color(st.get("accent_from"), "#F59E0B"))
        .replace("%%B%%", _color(st.get("accent_to"), "#A855F7"))
        .replace("%%BODY%%", body)
    )
