import json
import os
import html as htmlmod

from tokens import FLYTE, UNION, FONT_FACES
from css import BASE_CSS
from js import ENGINE_JS
from content import PAGES

SITES = {"flyte": FLYTE, "union": UNION}

# ---------------------------------------------------------------- helpers

FMT_JS = {
    "s0": "function(v){return Math.round(v).toLocaleString()+' s';}",
    "s1": "function(v){return v.toFixed(1)+' s';}",
    "gib": "function(v){return v.toFixed(1)+' GiB';}",
    "k": "function(v){return (v/1000).toFixed(0)+'k';}",
    "k0": "function(v){return (v/1000).toFixed(0)+'k tok';}",
    "i0": "function(v){return Math.round(v);}",
}


def color_ref(theme, key):
    """Resolve a series color key ('series_a'/'series_b'/'bad'/...) to a CSS var()."""
    if key in ("series_a", "series_b", "bad", "accent", "spark"):
        return "var(--" + key.replace("_", "-") + ")"
    return key


def render_legend(theme, items):
    parts = []
    for label, colorkey in items:
        parts.append(
            '<span class="sw"><i style="background:{c}"></i>{l}</span>'.format(
                c=color_ref(theme, colorkey), l=htmlmod.escape(label)
            )
        )
    return '<div class="legend">' + "".join(parts) + "</div>"


def render_figure(theme, fig):
    legend_html = render_legend(theme, fig.get("legend", [])) if fig.get("legend") else ""
    body = (
        '<div class="figure" id="{fid}-card">'
        '<div class="figure-head"><span class="figure-title">{title}</span>'
        '<span class="figure-tag">{tag}</span></div>'
        "{legend}"
        '<div class="chart-wrap" id="{fid}"></div>'
        '<p class="figure-note">{note}</p>'
        "</div>"
    ).format(
        fid=fig["id"],
        title=htmlmod.escape(fig["title"]),
        tag=htmlmod.escape(fig["tag"]),
        legend=legend_html,
        note=fig["note"],
    )
    return body


def render_figure_script(theme, fig):
    d = fig["data"]
    if fig["kind"] == "bar":
        series_js = ",".join(
            '{{label:{l},color:{c},values:{v}}}'.format(
                l=json.dumps(s["label"]),
                c=json.dumps(color_ref(theme, s["color"])),
                v=json.dumps(s["values"]),
            )
            for s in d["series"]
        )
        return (
            "BenchBar({cid}, {{categories:{cats}, series:[{series}], yMax:{ymax}, "
            "yFmt:{yfmt}, barFmt:{barfmt}, unit:{unit}{oom}{height}{horizontal}}});"
        ).format(
            cid=json.dumps(fig["id"]),
            cats=json.dumps(d["categories"]),
            series=series_js,
            ymax=d["yMax"],
            yfmt=FMT_JS[d["yFmt"]],
            barfmt=FMT_JS[d["barFmt"]],
            unit=json.dumps(d.get("unit", "")),
            oom=(", oomText:" + json.dumps(d["oomText"])) if d.get("oomText") else "",
            height=(", height:" + str(d["height"])) if d.get("height") else "",
            horizontal=(", horizontal:true" if d.get("horizontal") else ""),
        )
    if fig["kind"] == "line":
        series_js = ",".join(
            '{{label:{l},color:{c},values:{v}}}'.format(
                l=json.dumps(s["label"]),
                c=json.dumps(color_ref(theme, s["color"])),
                v=json.dumps(s["values"]),
            )
            for s in d["series"]
        )
        return (
            "BenchLine({cid}, {{xLabels:{xl}, series:[{series}], yMax:{ymax}, yMin:{ymin}, "
            "yFmt:{yfmt}, ptFmt:{ptfmt}}});"
        ).format(
            cid=json.dumps(fig["id"]),
            xl=json.dumps(d["xLabels"]),
            series=series_js,
            ymax=d["yMax"],
            ymin=d.get("yMin", 0),
            yfmt=FMT_JS[d["yFmt"]],
            ptfmt=FMT_JS[d["ptFmt"]],
        )
    if fig["kind"] == "trace":
        return (
            "BenchTrace({cid}, {{util:{util}, mem:{mem}, color:{color}, memMax:{memmax}}});"
        ).format(
            cid=json.dumps(fig["id"]),
            util=json.dumps(d["util"]),
            mem=json.dumps(d["mem"]),
            color=json.dumps(color_ref(theme, d["color"])),
            memmax=d["memMax"],
        )
    raise ValueError(fig["kind"])


def render_table(theme, table):
    rows = "".join(
        "<tr><td>{k}</td><td class=\"mono\" style=\"color:var(--series-b);font-weight:600\">{a}</td>"
        "<td class=\"mono\" style=\"color:var(--series-a);font-weight:600\">{b}</td></tr>".format(
            k=htmlmod.escape(k), a=htmlmod.escape(a), b=htmlmod.escape(b)
        )
        for k, a, b in table["rows"]
    )
    return (
        '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;margin-top:8px">'
        '<thead><tr style="border-bottom:1px solid var(--border)">'
        '<th style="text-align:left;padding:10px 8px;font-size:13px;color:var(--ink-faint);font-weight:600">Metric</th>'
        '<th style="text-align:left;padding:10px 8px;font-size:13px;color:var(--ink-faint);font-weight:600">{ca}</th>'
        '<th style="text-align:left;padding:10px 8px;font-size:13px;color:var(--ink-faint);font-weight:600">{cb}</th>'
        "</tr></thead><tbody>{rows}</tbody></table></div>"
    ).format(ca=htmlmod.escape(table["col_a"]), cb=htmlmod.escape(table["col_b"]), rows=rows).replace(
        "<td>", '<td style="padding:9px 8px;border-bottom:1px solid var(--border-soft);font-size:14px;color:var(--ink-dim)">'
    )


def root_vars(theme):
    keys = [
        "bg", "bg_elev", "bg_elev2", "border", "border_soft", "ink", "ink_dim", "ink_faint",
        "accent", "accent_2", "accent_ink", "spark", "series_a", "series_b", "bad", "grid_line",
        "dark_band_bg", "dark_band_ink", "dark_band_ink_dim",
    ]
    lines = []
    for k in keys:
        lines.append("--{name}: {val};".format(name=k.replace("_", "-"), val=theme[k]))
    lines.append("--font-display: '{}';".format(theme["font_display"]))
    lines.append("--font-body: '{}';".format(theme["font_body"]))
    lines.append("--font-mono: '{}';".format(theme["font_mono"]))
    return "\n  ".join(lines)


def nav_html(theme, bench_href, crumb=None):
    other = UNION if theme is FLYTE else FLYTE
    links = (
        '<a href="{home}">{name}</a>'
        '<a href="{bench}">Benchmarks</a>'
        '<a href="{other_home}">{other_name} &#8599;</a>'
    ).format(
        home=theme["home_url"], name=theme["site_name"],
        bench=bench_href,
        other_home=other["home_url"], other_name=other["site_name"],
    )
    crumb_html = ""
    if crumb:
        crumb_html = ' <span class="nav-crumb">/ {}</span>'.format(htmlmod.escape(crumb))
    return (
        '<div class="nav"><div class="wrap nav-row">'
        '<a class="nav-brand" href="{bench}">{mark}{name}{crumb}</a>'
        '<div class="nav-links">{links}'
        '<a class="btn btn-primary btn-sm nav-cta" href="{devbox}">Try the Devbox</a>'
        "</div></div></div>"
    ).format(
        bench=bench_href, name=theme["site_name"], crumb=crumb_html,
        links=links, devbox=theme["devbox_url"],
        mark=NAV_MARK,
    )


NAV_MARK = (
    '<svg class="nav-mark" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M12 2L2 7L12 12L22 7L12 2Z" fill="var(--series-b)"/>'
    '<path d="M2 17L12 22L22 17" stroke="var(--ink-dim)" stroke-width="1.6" fill="none"/>'
    '<path d="M2 12L12 17L22 12" stroke="var(--series-b)" stroke-width="1.6" fill="none"/>'
    "</svg>"
)


def footer_html(theme, bench_href):
    other = UNION if theme is FLYTE else FLYTE
    return (
        '<footer><div class="wrap footer-row">'
        "<div>Flyte Benchmarks &mdash; reproducible orchestration studies. "
        '<a href="https://github.com/flyteorg/flyte-benchmarks" target="_blank" rel="noopener">Source &amp; raw data on GitHub &#8599;</a></div>'
        '<div class="footer-links">'
        '<a href="{bench}">All {name} benchmarks</a>'
        '<a href="{other}">{other_name}</a>'
        '<a href="{devbox}">Try the Devbox</a>'
        "</div></div></footer>"
    ).format(
        bench=bench_href, name=theme["site_name"],
        other=other["home_url"], other_name=other["site_name"],
        devbox=theme["devbox_url"],
    )


def cta_band_html(theme, heading=None):
    heading = heading or "See it for yourself"
    return (
        '<div class="cta-band"><div class="wrap">'
        "<h2>{heading}</h2>"
        "<p>Spin up a real Flyte cluster in minutes and run the same workloads on your own hardware. "
        "No infra to provision, no YAML to write first.</p>"
        '<a class="btn btn-primary" href="{devbox}">Try the Devbox &rarr;</a>'
        "</div></div>"
    ).format(heading=heading, devbox=theme["devbox_url"])


def page_shell(theme, title, description, body_html, canonical_path, extra_script=""):
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<style>
{fonts}
:root {{
  {vars}
}}
{base}
</style>
</head>
<body>
{body}
<script>
{engine}
{extra}
</script>
</body>
</html>""".format(
        title=htmlmod.escape(title),
        desc=htmlmod.escape(description),
        fonts=FONT_FACES,
        vars=root_vars(theme),
        base=BASE_CSS,
        body=body_html,
        engine=ENGINE_JS,
        extra=extra_script,
    )


# ---------------------------------------------------------------- detail page

def render_detail_page(page):
    theme = SITES[page["site"]]
    figures_html = "\n".join(render_figure(theme, f) for f in page["figures"])
    figures_script = "\n".join(
        "registerChart({card_id}, function(){{ {stmt} }});".format(
            card_id=json.dumps(f["id"] + "-card"), stmt=render_figure_script(theme, f)
        )
        for f in page["figures"]
    )
    stats_html = "".join(
        '<div class="stat"><span class="num{cls}" data-countup data-to="{to}" data-decimals="{dec}"'
        ' data-prefix="{pre}" data-suffix="{suf}" data-from="0">0</span>'
        '<div class="lbl">{lbl}</div></div>'.format(
            cls=" accent" if s.get("accent") else (" bad" if s.get("bad") else ""),
            to=s["to"], dec=s.get("decimals", 0),
            pre=s.get("prefix", ""), suf=s.get("suffix", ""),
            lbl=s["label"],
        )
        for s in page["stats"]
    )
    table_html = render_table(theme, page["table"]) if page.get("table") else ""

    body = """
{nav}
<main>
  <section class="hero bg-grid">
    <div class="wrap">
      <span class="eyebrow"><span class="dot"></span>{eyebrow}</span>
      <h1>{title}</h1>
      <p class="sub">{subtitle}</p>
      <div class="hero-meta">{meta}</div>
    </div>
  </section>

  <section>
    <div class="wrap">
      <div class="abstract"><span class="label">Abstract</span>{abstract}
        <p style="margin-top:14px"><a href="{pdf}" target="_blank" rel="noopener" style="color:var(--series-b);font-weight:600">Read the full paper (PDF) &#8599;</a></p>
      </div>
      <div class="stat-row" style="margin-top:22px">{stats}</div>
    </div>
  </section>

  <hr class="rule">

  <section>
    <div class="wrap">
      <div class="section-head">
        <div class="section-kicker">Key results</div>
        <h2>What the numbers show</h2>
        <p>Every chart below is drawn straight from the measured data in the paper &mdash; hover any bar or point for the exact value.</p>
      </div>
      {figures}
      {table_wrap}
    </div>
  </section>

  {cta}
</main>
{footer}
""".format(
        nav=nav_html(theme, bench_href="../index.html", crumb=page["title"]),
        eyebrow=page["eyebrow"],
        title=page["title"],
        subtitle=page["subtitle"],
        meta="".join("<span>{}</span>".format(m) for m in page["meta"]),
        abstract=page["abstract"],
        pdf=page["pdf_href"],
        stats=stats_html,
        figures=figures_html,
        table_wrap=(
            '<div class="figure"><div class="figure-head"><span class="figure-title">{t}</span>'
            '<span class="figure-tag">Table 1</span></div>{tbl}</div>'.format(
                t=page["table"]["title"], tbl=table_html
            )
            if page.get("table") else ""
        ),
        cta=cta_band_html(theme),
        footer=footer_html(theme, bench_href="../index.html"),
    )

    # Runs synchronously, in the same script block as the reveal engine
    # (not deferred to DOMContentLoaded) so every chart is registered before
    # the reveal IntersectionObserver's first (always-async) callback can
    # fire -- otherwise an above-the-fold figure could intersect before its
    # chart is registered and never get drawn at all.
    extra = figures_script
    return page_shell(
        theme,
        title="{} — {} Benchmarks".format(page["title"], theme["site_name"]),
        description=page["subtitle"],
        body_html=body,
        canonical_path="/benchmarks/" + page["slug"],
        extra_script=extra,
    )


# ---------------------------------------------------------------- landing page

LANDING_CARDS = {
    "flyte": [
        dict(
            href="flyte1-vs-flyte2/index.html",
            kicker="Scalability study",
            title="Outscaling Flyte v1",
            desc="Flyte v2 runs common orchestration patterns 4.3–6.5× faster and removes v1's single-process OOM cliff entirely.",
            stat="6.5× faster",
        ),
        dict(
            href="agents-write-flyte2-better/index.html",
            kicker="Agent-authoring-cost study",
            title="Agents Are More Token Efficient with Flyte v2",
            desc="A coding agent reaches a working pipeline in 1.78× fewer tokens on v2 — and solves patterns v1 can't express at all.",
            stat="1.78× fewer tokens",
        ),
    ],
    "union": [
        dict(
            href="flyte-vs-union/index.html",
            kicker="Multi-cluster scale-out study",
            title="Orchestration Without Limits",
            desc="Union scales out to complete 200,000-action workflows where single-cluster OSS Flyte OOM-kills its executor.",
            stat="200k actions, 0 failures",
        ),
        dict(
            href="union-reusable-containers/index.html",
            kicker="GPU-utilization study",
            title="Reuse or Reload",
            desc="Container reuse keeps a 7B-model GPU at a sustained 100% utilization — 4.1× faster than spinning a fresh container per call.",
            stat="4.1× faster",
        ),
    ],
}


def render_landing_page(site_key):
    theme = SITES[site_key]
    cards = LANDING_CARDS[site_key]
    cards_html = "".join(
        '<a class="bench-card reveal" href="{href}">'
        '<svg class="card-arrow" viewBox="0 0 24 24" fill="none"><path d="M7 17L17 7M17 7H9M17 7V15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        '<div class="card-kicker">{kicker}</div><h3>{title}</h3><p>{desc}</p>'
        '<div class="card-stat mono">{stat}</div>'
        "</a>".format(**c)
        for c in cards
    )
    soon_html = (
        '<div class="bench-card soon reveal"><div class="card-kicker">Coming soon</div>'
        "<h3>Have a workload you want benchmarked?</h3>"
        '<p>This is an evolving series &mdash; new studies land here as they ship. '
        '<a href="https://github.com/flyteorg/flyte-benchmarks" target="_blank" rel="noopener" style="color:var(--series-b)">Propose one on GitHub &#8599;</a></p>'
        "</div>"
    )

    body = """
{nav}
<main>
  <section class="hero bg-grid">
    <div class="wrap">
      <span class="eyebrow"><span class="dot"></span>{tagline}</span>
      <h1>{name} Benchmarks</h1>
      <p class="sub">Real clusters. No simulation. Every number below comes from a workload that actually ran, graded and reported as-is &mdash; failures included.</p>
    </div>
  </section>

  <section>
    <div class="wrap">
      <div class="section-head">
        <div class="section-kicker">Studies</div>
        <h2>Pick a study</h2>
      </div>
      <div class="bench-grid">{cards}{soon}</div>
    </div>
  </section>

  {cta}
</main>
{footer}
""".format(
        nav=nav_html(theme, bench_href="index.html"),
        tagline=theme["site_tagline"],
        name=theme["site_label"],
        cards=cards_html,
        soon=soon_html,
        cta=cta_band_html(theme, heading="Run these benchmarks yourself"),
        footer=footer_html(theme, bench_href="index.html"),
    )

    return page_shell(
        theme,
        title="{} Benchmarks".format(theme["site_label"]),
        description="Reproducible orchestration and authoring-cost benchmarks for {}.".format(theme["site_label"]),
        body_html=body,
        canonical_path="/benchmarks",
    )


# ---------------------------------------------------------------- main

OUT_MAP = {
    "flyte1-vs-flyte2": "../flyte.org/benchmarks/flyte1-vs-flyte2/index.html",
    "agents-write-flyte2-better": "../flyte.org/benchmarks/agents-write-flyte2-better/index.html",
    "flyte-vs-union": "../union.ai/benchmarks/flyte-vs-union/index.html",
    "union-reusable-containers": "../union.ai/benchmarks/union-reusable-containers/index.html",
}

if __name__ == "__main__":
    for slug, page in PAGES.items():
        html_out = render_detail_page(page)
        path = OUT_MAP[slug]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(html_out)
        print("wrote", path, len(html_out), "bytes")

    with open("../flyte.org/benchmarks/index.html", "w") as f:
        f.write(render_landing_page("flyte"))
    print("wrote ../flyte.org/benchmarks/index.html")

    with open("../union.ai/benchmarks/index.html", "w") as f:
        f.write(render_landing_page("union"))
    print("wrote ../union.ai/benchmarks/index.html")
