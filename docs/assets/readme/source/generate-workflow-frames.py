#!/usr/bin/env python3
"""Generate deterministic SVG keyframes for the README workflow animation."""

from pathlib import Path
import sys


def card(x, y, w, h, fill, rid, name):
    return f'''<g><rect x="{x+10}" y="{y+10}" width="{w}" height="{h}" fill="#111"/><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{fill}" stroke="#111" stroke-width="3"/><text x="{x+20}" y="{y+39}" class="id">{rid}</text><text x="{x+20}" y="{y+74}" class="nm">{name}</text></g>'''


def frame(step):
    terminal_lines = [
        ('Found', 'SMP-2026-0024', 'cultured cells'),
        ('Found', 'RGT-0018', 'treatment reagent'),
        ('Loaded', 'SOP-0007', 'treatment protocol'),
        ('Created', 'EXP-2026-07-14-01', ''),
        ('Registered', 'SMP-2026-0031', 'extracted RNA'),
        ('Registered', 'DAT-2026-0012', 'sequencing data'),
    ]
    lines = ''
    shown = max(0, min(len(terminal_lines), step - 1))
    for i, (verb, rid, tail) in enumerate(terminal_lines[:shown]):
        y = 558 + i * 42
        lines += f'<text x="120" y="{y}" class="term"><tspan fill="#a8f0a8">◇</tspan> {verb} <tspan fill="#ff7dc1">{rid}</tspan> {tail}</text>'

    graph = ''
    if step >= 3:
        graph += card(910, 438, 300, 105, '#ff7dc1', 'EXP-2026-07-14-01', 'treatment experiment')
    if step >= 2:
        graph += card(775, 300, 225, 92, '#a8f0a8', 'SMP-2026-0024', 'cultured cells')
        graph += card(1035, 300, 205, 92, '#a8f0a8', 'RGT-0018', 'reagent')
        graph += card(1270, 300, 205, 92, '#96f19b', 'SOP-0007', 'protocol')
    if step >= 4:
        graph += card(850, 635, 250, 92, '#a8f0a8', 'SMP-2026-0031', 'extracted RNA')
    if step >= 5:
        graph += card(1170, 635, 250, 92, '#a8e0f0', 'DAT-2026-0012', 'sequencing data')
    if step >= 3:
        graph += '<path class="line" d="M888 392L980 438M1138 392L1085 438M1372 392L1180 438"/>'
    if step >= 4:
        graph += '<path class="line" d="M1005 543L975 635"/>'
    if step >= 5:
        graph += '<path class="line" d="M1120 543L1295 635"/>'

    final = ''
    if step >= 6:
        final = '<rect x="842" y="764" width="612" height="72" fill="#111"/><text x="1148" y="811" class="final" text-anchor="middle">EVERY RESULT — TRACEABLE.</text>'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
<defs><pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.2" fill="#111" opacity=".12"/></pattern><style>.s{{font-family:Inter,Arial,sans-serif}}.m{{font-family:"JetBrains Mono",Menlo,monospace}}.id{{font-family:"JetBrains Mono",Menlo,monospace;font-weight:800;font-size:21px}}.nm{{font-family:Inter,Arial,sans-serif;font-weight:800;font-size:21px}}.term{{font-family:"JetBrains Mono",Menlo,monospace;font-weight:500;font-size:22px;fill:#e8e6dc}}.line{{stroke:#111;stroke-width:5;fill:none}}.final{{font-family:Inter,Arial,sans-serif;font-weight:900;font-size:29px;fill:#a8f0a8;letter-spacing:2px}}</style></defs>
<rect width="1600" height="900" fill="#f7f5ec"/><rect x="34" y="34" width="1532" height="832" fill="url(#dots)" stroke="#111" stroke-width="3"/>
<rect x="76" y="70" width="360" height="58" fill="#ff7dc1" stroke="#111" stroke-width="3"/><text x="101" y="109" class="s" font-size="23" font-weight="900" letter-spacing="2">YOU DESCRIBE · AGENT ORGANIZES</text>
<text x="76" y="205" class="s" font-size="62" font-weight="900">One sentence becomes</text><rect x="76" y="228" width="580" height="86" fill="#a8f0a8" stroke="#111" stroke-width="3"/><text x="102" y="291" class="s" font-size="59" font-weight="900">a traceable experiment.</text>
<rect x="76" y="358" width="650" height="478" fill="#1c1c1e" stroke="#111" stroke-width="3"/><rect x="76" y="358" width="650" height="62" fill="#a8f0a8" stroke="#111" stroke-width="3"/><circle cx="105" cy="389" r="9" fill="#ff5f57" stroke="#111" stroke-width="2"/><circle cx="132" cy="389" r="9" fill="#febc2e" stroke="#111" stroke-width="2"/><circle cx="159" cy="389" r="9" fill="#28c840" stroke="#111" stroke-width="2"/><text x="190" y="398" class="m" font-size="22" font-weight="800">agent-eln · experiment</text>
<text x="112" y="466" class="term" fill="#f7f5ec">&gt; “Treat SMP-2026-0024 with RGT-0018</text><text x="137" y="500" class="term" fill="#f7f5ec">using SOP-0007; collect RNA for sequencing.”</text>{lines}{graph}{final}</svg>'''


out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
for step in range(1, 7):
    (out / f"workflow-{step}.svg").write_text(frame(step))
