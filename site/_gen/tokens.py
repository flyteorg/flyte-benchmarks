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
  font-family: 'Instrument Sans';
  font-weight: 400 700;
  font-style: normal;
  font-display: swap;
  src: url(data:font/ttf;base64,{instrument}) format('truetype');
}}
@font-face {{
  font-family: 'Instrument Sans';
  font-weight: 400 700;
  font-style: italic;
  font-display: swap;
  src: url(data:font/ttf;base64,{instrument_italic}) format('truetype');
}}
@font-face {{
  font-family: 'Yellix';
  font-weight: 400;
  font-style: normal;
  font-display: swap;
  src: url(data:font/otf;base64,{yellix_regular}) format('opentype');
}}
@font-face {{
  font-family: 'Yellix';
  font-weight: 500;
  font-style: normal;
  font-display: swap;
  src: url(data:font/otf;base64,{yellix_medium}) format('opentype');
}}
@font-face {{
  font-family: 'Yellix';
  font-weight: 600 700;
  font-style: normal;
  font-display: swap;
  src: url(data:font/otf;base64,{yellix_semibold}) format('opentype');
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
    instrument=load_b64("instrument-sans"),
    instrument_italic=load_b64("instrument-sans-italic"),
    yellix_regular=load_b64("yellix-regular"),
    yellix_medium=load_b64("yellix-medium"),
    yellix_semibold=load_b64("yellix-semibold"),
    plexmono400=load_b64("plexmono-400"),
    plexmono600=load_b64("plexmono-600"),
)


FLYTE = dict(
    site_name="flyte.org",
    site_label="Flyte",
    landing_sub="Learn why Flyte 2 scales better, performs faster, and lets your Agents do more with less.",
    home_url="https://flyte.org",
    devbox_url="https://flyte.org/devbox",
    # flyte.org's 2026 redesign is light-mode-primary (white pages, a dark
    # violet band for its "Introducing Flyte 2" section) -- matched here from
    # the live site's Webflow custom properties, not guessed.
    bg="#ffffff",
    bg_elev="#f6f5fb",
    bg_elev2="#ece9f5",
    border="#e3e0ee",
    border_soft="#ece9f5",
    ink="#15141d",
    ink_dim="#4b4760",
    ink_faint="#83818c",
    accent="#6f2aef",
    accent_2="#8c4fff",
    accent_ink="#ffffff",
    spark="#ffbc1d",
    series_a="#9c85d6",   # "Flyte" / v1 -- shared throughline color, deepened for a white ground
    series_b="#6f2aef",   # v2 -- this site's real brand purple
    bad="#d33c2f",
    font_display="Instrument Sans",
    font_body="Instrument Sans",
    font_mono="IBM Plex Mono",
    grid_line="#efedf7",
    # flyte.org alternates light sections with a solid near-black violet band
    # (its "Introducing Flyte 2" section) -- used for the CTA band here.
    dark_band_bg="#050310",
    dark_band_ink="#ffffff",
    dark_band_ink_dim="#b9b3d6",
)

UNION = dict(
    site_name="union.ai",
    site_label="Union",
    landing_sub="Learn how Union scales with virtually no limit and enables you to saturate your compute.",
    home_url="https://www.union.ai",
    devbox_url="https://www.union.ai/get-devbox",
    bg="#18191a",
    bg_elev="#202226",
    bg_elev2="#2a2c31",
    border="#34373c",
    border_soft="#26282c",
    ink="#f2f3f5",
    ink_dim="#a3a8ae",
    ink_faint="#75797f",
    accent="#fcb51f",     # union.ai's real CTA is a solid gold pill, not blue
    accent_2="#e8a30f",
    accent_ink="#15130a",
    spark="#3378f5",
    series_a="#a78bfa",   # "Flyte (OSS)" -- shared throughline color
    series_b="#fcb51f",   # Union -- this site's real brand gold
    bad="#ef5757",
    font_display="Yellix",
    font_body="Yellix",
    font_mono="IBM Plex Mono",
    grid_line="#26282c",
    # union.ai is already dark end-to-end -- the "band" is the same surface.
    dark_band_bg="#18191a",
    dark_band_ink="#f2f3f5",
    dark_band_ink_dim="#a3a8ae",
)
