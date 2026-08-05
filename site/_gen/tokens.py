"""Design tokens for the two benchmark micro-sites.

Shared convention across all four papers: "Flyte" (v1 or OSS) is always the
same muted violet, everywhere, on both domains -- the throughline that makes
this read as one body of work. Each domain's own chrome (nav, buttons, the
"other side" of its comparisons) carries that domain's real brand color:
flyte.org's development-tool purple, union.ai's platform blue. Union's own
data-series color is its real brand gold, matching the convention already
established in the shipped PDFs.
"""

FONTS_DIR = "fonts"


def load_b64(name):
    with open(f"{FONTS_DIR}/{name}.b64") as f:
        return f.read().strip()


FONT_FACES = """
@font-face {{
  font-family: 'Inter';
  font-weight: 400 800;
  font-style: normal;
  font-display: swap;
  src: url(data:font/woff2;base64,{inter}) format('woff2');
}}
@font-face {{
  font-family: 'Manrope';
  font-weight: 400 800;
  font-style: normal;
  font-display: swap;
  src: url(data:font/woff2;base64,{manrope}) format('woff2');
}}
@font-face {{
  font-family: 'IBM Plex Mono';
  font-weight: 400;
  font-style: normal;
  font-display: swap;
  src: url(data:font/woff2;base64,{plexmono400}) format('woff2');
}}
@font-face {{
  font-family: 'IBM Plex Mono';
  font-weight: 600;
  font-style: normal;
  font-display: swap;
  src: url(data:font/woff2;base64,{plexmono600}) format('woff2');
}}
""".format(
    inter=load_b64("inter"),
    manrope=load_b64("manrope"),
    plexmono400=load_b64("plexmono-400"),
    plexmono600=load_b64("plexmono-600"),
)


FLYTE = dict(
    site_name="flyte.org",
    site_label="Flyte",
    site_tagline="Open source",
    home_url="https://flyte.org",
    benchmarks_url="https://claude.ai/code/artifact/f038a17a-6188-4462-beaf-831272d81a8d",
    devbox_url="https://flyte.org/devbox",
    bg="#050310",
    bg_elev="#0d0a1c",
    bg_elev2="#161129",
    border="#2a2340",
    border_soft="#1c1730",
    ink="#f2eefc",
    ink_dim="#a79fc4",
    ink_faint="#7a7297",
    accent="#8c4fff",
    accent_2="#6f2aef",
    accent_ink="#ffffff",
    spark="#ffbc1d",
    series_a="#a78bfa",   # "Flyte" / v1 -- shared throughline color
    series_b="#8c4fff",   # v2 -- this site's accent
    bad="#ff6b5e",
    font_display="Inter",
    font_body="Inter",
    font_mono="IBM Plex Mono",
    grid_line="#1c1730",
)

UNION = dict(
    site_name="union.ai",
    site_label="Union",
    site_tagline="Managed platform",
    home_url="https://www.union.ai",
    benchmarks_url="https://claude.ai/code/artifact/8725c417-889b-4364-adb5-6c21a931f094",
    devbox_url="https://www.union.ai/get-devbox",
    bg="#0d0f12",
    bg_elev="#15181b",
    bg_elev2="#1d2125",
    border="#2b3035",
    border_soft="#1d2226",
    ink="#eef2f5",
    ink_dim="#9aa3ab",
    ink_faint="#6c757d",
    accent="#3378f5",
    accent_2="#1648b8",
    accent_ink="#ffffff",
    spark="#fcb51f",
    series_a="#a78bfa",   # "Flyte (OSS)" -- shared throughline color
    series_b="#fcb51f",   # Union -- this site's real brand gold
    bad="#ef5757",
    font_display="Manrope",
    font_body="Manrope",
    font_mono="IBM Plex Mono",
    grid_line="#1d2226",
)
