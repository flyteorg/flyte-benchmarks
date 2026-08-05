"""Shared stylesheet. Colors come entirely from CSS custom properties set in
a per-page :root block (see tokens.py) so this one ruleset serves both
domains -- only the palette changes, never the structure."""

BASE_CSS = """
*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  * { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font-body), system-ui, sans-serif;
  font-size: 16px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  overflow-x: hidden;
}

::selection { background: var(--accent); color: var(--accent-ink); }

a { color: inherit; }
a:focus-visible, button:focus-visible, .card:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }

h1, h2, h3, h4 { font-family: var(--font-display), system-ui, sans-serif; font-weight: 800; margin: 0; text-wrap: balance; letter-spacing: -0.01em; }
p { margin: 0; }

.mono { font-family: var(--font-mono), ui-monospace, monospace; font-variant-numeric: tabular-nums; }

.wrap { max-width: 1180px; margin: 0 auto; padding: 0 28px; }
@media (max-width: 640px) { .wrap { padding: 0 20px; } }

/* Decorative grid sits on its own layer behind hero content -- never apply
   the mask to an element that also contains readable text. */
.bg-grid { position: relative; }
.bg-grid::before {
  content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-image:
    linear-gradient(var(--grid-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
  background-size: 42px 42px;
  -webkit-mask-image: radial-gradient(ellipse 70% 65% at 50% 0%, #000 0%, transparent 85%);
          mask-image: radial-gradient(ellipse 70% 65% at 50% 0%, #000 0%, transparent 85%);
}
.bg-grid > .wrap { position: relative; z-index: 1; }

/* ---------- nav ---------- */
.nav {
  position: sticky; top: 0; z-index: 40;
  background: color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-soft);
}
.nav-row { display: flex; align-items: center; justify-content: space-between; height: 64px; gap: 24px; }
.nav-brand { display: flex; align-items: center; gap: 10px; font-family: var(--font-display); font-weight: 800; font-size: 17px; text-decoration: none; color: var(--ink); white-space: nowrap; }
.nav-mark { width: 22px; height: 22px; flex: none; }
.nav-crumb { color: var(--ink-faint); font-weight: 600; }
.nav-links { display: flex; align-items: center; gap: 28px; font-size: 14.5px; font-weight: 600; }
.nav-links a { text-decoration: none; color: var(--ink-dim); transition: color .15s; }
.nav-links a:hover { color: var(--ink); }
.nav-links a.nav-cta { margin-left: 4px; color: var(--accent-ink); }
.nav-links a.nav-cta:hover { color: var(--accent-ink); }

/* ---------- buttons ---------- */
.btn {
  display: inline-flex; align-items: center; gap: 8px;
  font-family: var(--font-display); font-weight: 700; font-size: 15px;
  padding: 11px 22px; border-radius: 999px; text-decoration: none;
  border: 1px solid transparent; cursor: pointer; white-space: nowrap;
  transition: transform .15s ease, box-shadow .15s ease, background .15s ease, border-color .15s ease;
}
.btn:hover { transform: translateY(-1px); }
.btn-primary {
  background: var(--accent); color: var(--accent-ink);
  background-image: linear-gradient(180deg, rgba(255,255,255,.24), transparent);
  box-shadow: 0 1px 0 rgba(0,0,0,.2), 0 0 0 0 var(--accent);
}
.btn-primary:hover { box-shadow: 0 6px 24px -6px var(--accent); }
.btn-ghost { background: transparent; border-color: var(--border); color: var(--ink); }
.btn-ghost:hover { border-color: var(--accent); }
.btn-sm { padding: 8px 16px; font-size: 13.5px; }
.btn svg { width: 15px; height: 15px; }

/* ---------- hero ---------- */
.hero { position: relative; padding: 88px 0 64px; }
.eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  font-family: var(--font-mono); font-size: 12.5px; font-weight: 600;
  letter-spacing: .07em; text-transform: uppercase; color: var(--series-b);
  padding: 5px 11px; border: 1px solid var(--border); border-radius: 999px;
  background: color-mix(in srgb, var(--series-b) 10%, transparent);
}
.eyebrow .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--series-b); box-shadow: 0 0 0 3px color-mix(in srgb, var(--series-b) 25%, transparent); }
.hero h1 { font-size: clamp(34px, 5.4vw, 58px); line-height: 1.06; max-width: 15ch; }
.hero .sub { font-size: clamp(17px, 2vw, 21px); color: var(--ink-dim); max-width: 62ch; margin-top: 18px; line-height: 1.55; }
.hero-meta { display: flex; flex-wrap: wrap; gap: 10px 22px; margin-top: 26px; font-family: var(--font-mono); font-size: 13px; color: var(--ink-faint); }
.hero-meta b { color: var(--ink-dim); font-weight: 600; }

/* ---------- section rhythm ---------- */
section { padding: 56px 0; }
.section-head { max-width: 62ch; margin-bottom: 34px; }
.section-kicker { font-family: var(--font-mono); font-size: 12.5px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-faint); margin-bottom: 10px; }
.section-head h2 { font-size: clamp(24px, 3vw, 32px); }
.section-head p { color: var(--ink-dim); margin-top: 12px; font-size: 17px; }
hr.rule { border: none; height: 1px; background: var(--border-soft); margin: 0; }

/* ---------- abstract ---------- */
.abstract {
  border: 1px solid var(--border); border-left: 3px solid var(--series-b);
  background: var(--bg-elev); border-radius: 16px;
  padding: 26px 28px; font-size: 16.5px; line-height: 1.7; color: var(--ink-dim);
}
.abstract b { color: var(--ink); }
.abstract .label { display: block; font-family: var(--font-mono); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--series-b); font-weight: 700; margin-bottom: 12px; }

/* ---------- stat row ---------- */
.stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1px; background: var(--border); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; }
.stat { background: var(--bg-elev); padding: 22px 22px 20px; }
.stat .num { font-family: var(--font-mono); font-weight: 600; font-size: clamp(26px, 3.4vw, 36px); color: var(--ink); display: block; letter-spacing: -0.01em; }
.stat .num.accent { color: var(--series-b); }
.stat .num.bad { color: var(--bad); }
.stat .lbl { font-size: 13.5px; color: var(--ink-faint); margin-top: 6px; line-height: 1.4; }

/* ---------- figure / chart cards ---------- */
.figure { border: 1px solid var(--border); background: var(--bg-elev); border-radius: 18px; padding: 26px 26px 22px; margin-top: 20px; opacity: 0; transform: translateY(14px); transition: opacity .6s ease, transform .6s ease; }
.figure.in-view { opacity: 1; transform: none; }
.figure-head { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; flex-wrap: wrap; margin-bottom: 4px; }
.figure-title { font-family: var(--font-display); font-weight: 700; font-size: 18px; }
.figure-tag { font-family: var(--font-mono); font-size: 11.5px; color: var(--ink-faint); letter-spacing: .04em; }
.figure-note { color: var(--ink-dim); font-size: 14.5px; margin-top: 14px; line-height: 1.55; max-width: 68ch; }
.figure-note b { color: var(--ink); }
.legend { display: flex; gap: 18px; flex-wrap: wrap; font-size: 13px; color: var(--ink-dim); margin-top: 4px; }
.legend .sw { display: inline-flex; align-items: center; gap: 7px; }
.legend .sw i { width: 11px; height: 11px; border-radius: 3px; display: inline-block; }

.chart-wrap { position: relative; margin-top: 14px; }
.chart-wrap svg { width: 100%; height: auto; display: block; overflow: visible; }
.axis-label { fill: var(--ink-faint); font-family: var(--font-mono); font-size: 10.5px; }
.grid-line { stroke: var(--border-soft); stroke-width: 1; }
.bar-label { fill: var(--ink); font-family: var(--font-mono); font-size: 11px; font-weight: 600; text-anchor: middle; }
.oom-label { fill: var(--bad); font-family: var(--font-mono); font-size: 11px; font-weight: 700; text-anchor: middle; }

.tooltip {
  position: absolute; pointer-events: none; z-index: 10;
  background: var(--bg-elev2); border: 1px solid var(--border); border-radius: 10px;
  padding: 8px 11px; font-family: var(--font-mono); font-size: 12.5px; color: var(--ink);
  box-shadow: 0 10px 30px -8px rgba(0,0,0,.6);
  opacity: 0; transform: translate(-50%, -6px); transition: opacity .1s ease;
  white-space: nowrap;
}
.tooltip.show { opacity: 1; }
.tooltip .k { color: var(--ink-faint); }

/* ---------- code ---------- */
pre.code {
  font-family: var(--font-mono); font-size: 13px; line-height: 1.55;
  background: #000000; border: 1px solid var(--border); border-radius: 10px;
  padding: 16px 18px; overflow-x: auto; color: #d9d3ee;
}
pre.code .k { color: var(--series-b); }
pre.code .c { color: var(--ink-faint); font-style: italic; }
pre.code .s { color: var(--spark); }

/* ---------- CTA band ---------- */
.cta-band {
  background: var(--dark-band-bg);
  color: var(--dark-band-ink);
  background-image: radial-gradient(ellipse 60% 120% at 50% 0%, color-mix(in srgb, var(--accent) 20%, transparent), transparent);
  padding: 68px 0;
  text-align: center;
}
.cta-band h2 { font-size: clamp(24px, 3.4vw, 34px); max-width: 26ch; margin: 0 auto; }
.cta-band p { color: var(--dark-band-ink-dim); margin: 14px auto 0; max-width: 52ch; font-size: 16.5px; }
.cta-band .btn { margin-top: 26px; padding: 14px 28px; font-size: 16px; }

/* ---------- footer ---------- */
footer { border-top: 1px solid var(--border-soft); padding: 40px 0 48px; }
.footer-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; font-size: 13.5px; color: var(--ink-faint); }
.footer-row a { color: var(--ink-dim); text-decoration: none; }
.footer-row a:hover { color: var(--ink); }
.footer-links { display: flex; gap: 20px; flex-wrap: wrap; }

/* ---------- landing grid ---------- */
.bench-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
.bench-card {
  display: block; text-decoration: none; color: var(--ink);
  border: 1px solid var(--border); background: var(--bg-elev); border-radius: 18px;
  padding: 26px; position: relative; overflow: hidden;
  transition: border-color .2s ease, transform .2s ease;
}
.bench-card:hover { border-color: var(--series-b); transform: translateY(-3px); }
.bench-card .card-kicker { font-family: var(--font-mono); font-size: 11.5px; color: var(--ink-faint); letter-spacing: .05em; text-transform: uppercase; }
.bench-card h3 { font-size: 21px; margin-top: 10px; line-height: 1.25; }
.bench-card p { color: var(--ink-dim); margin-top: 10px; font-size: 14.5px; line-height: 1.55; }
.bench-card .card-stat { margin-top: 18px; font-family: var(--font-mono); font-size: 22px; font-weight: 700; color: var(--series-b); }
.bench-card .card-arrow { position: absolute; top: 24px; right: 24px; width: 18px; height: 18px; color: var(--ink-faint); transition: transform .2s ease, color .2s ease; }
.bench-card:hover .card-arrow { transform: translate(3px,-3px); color: var(--series-b); }
.bench-card.soon { opacity: .55; }
.bench-card.soon:hover { transform: none; border-color: var(--border); }

.reveal { opacity: 0; transform: translateY(16px); transition: opacity .6s ease, transform .6s ease; }
.reveal.in-view { opacity: 1; transform: none; }

@media (max-width: 780px) {
  .nav-links { display: none; }
  section { padding: 40px 0; }
}
"""
