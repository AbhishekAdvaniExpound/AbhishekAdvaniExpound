#!/usr/bin/env python3
"""Render the profile's self-contained SVG card system from verified JSON data."""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "contributions.json"
CARDS_DIR = ROOT / "cards"
STATIC = os.environ.get("STATIC") == "1"

C = {
    "bg": "#07111f", "panel": "#0b1728", "panel2": "#0e1d31", "line": "#20344d",
    "text": "#f3f8ff", "muted": "#91a4bd", "blue": "#3b82f6", "cyan": "#22d3ee",
    "blue2": "#1d4ed8", "quiet": "#12243a",
}


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def style(extra: str = "") -> str:
    animation = "" if STATIC else """
      .reveal{opacity:0;transform:translateY(10px);animation:rise .65s cubic-bezier(.2,.75,.25,1) forwards}
      .pulse{animation:pulse 4s ease-in-out infinite}.dash{animation:dash 8s linear infinite}
      @keyframes rise{to{opacity:1;transform:translateY(0)}}
      @keyframes pulse{0%,100%{opacity:.35}50%{opacity:.85}}
      @keyframes dash{to{stroke-dashoffset:-80}}
    """
    return f"""<style>
      text{{font-family:Inter,Geist,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
      .mono{{font-family:'SFMono-Regular',Consolas,'Liberation Mono',monospace}}
      .title{{fill:{C['text']};font-weight:650;letter-spacing:-.02em}}
      .body{{fill:{C['muted']}}}.label{{fill:{C['cyan']};font-weight:650;letter-spacing:.13em}}
      .chip{{fill:{C['text']};font-size:15px}}.hair{{stroke:{C['line']};stroke-width:1}}
      {animation}{extra}
      @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.reveal,.cell{{opacity:1!important;transform:none!important}}.bar,.best{{transform:none!important}}}}
    </style>"""


def svg_shell(name: str, width: int, height: int, body: str, *, extra_style: str = "", desc: str = "") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{esc(name)}</title><desc id="desc">{esc(desc or name)}</desc>
  <defs>
    <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{C['panel2']}"/><stop offset="1" stop-color="{C['bg']}"/></linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{C['blue']}"/><stop offset="1" stop-color="{C['cyan']}"/></linearGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>{style(extra_style)}
  <rect width="{width}" height="{height}" rx="22" fill="url(#panel)"/>
  <rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="21.5" fill="none" stroke="{C['line']}"/>
  {body}
</svg>
"""


def delay(index: int, step: float = 0.09) -> str:
    return "" if STATIC else f' style="animation-delay:{index * step:.2f}s"'


def chip(x: int, y: int, text: str, width: int | None = None) -> str:
    width = width or max(92, len(text) * 9 + 30)
    return f'<g><rect x="{x}" y="{y}" width="{width}" height="34" rx="17" fill="{C["quiet"]}" stroke="{C["line"]}"/><text x="{x + 15}" y="{y + 22}" class="chip mono">{esc(text)}</text></g>'


def hero() -> str:
    grid = "".join(f'<path d="M {x} 0 V 360" class="hair" opacity=".16"/>' for x in range(40, 1200, 80))
    grid += "".join(f'<path d="M 0 {y} H 1200" class="hair" opacity=".16"/>' for y in range(40, 360, 80))
    smil = "" if STATIC else '<animate attributeName="gradientTransform" values="translate(-1 0);translate(1 0);translate(-1 0)" dur="8s" repeatCount="indefinite"/>'
    body = f"""
    <defs><linearGradient id="heroText" x1="0" y1="0" x2="1" y2="0" gradientTransform="translate(-1 0)"><stop stop-color="{C['text']}"/><stop offset=".48" stop-color="{C['text']}"/><stop offset=".55" stop-color="{C['cyan']}"/><stop offset=".62" stop-color="{C['text']}"/>{smil}</linearGradient></defs>
    {grid}<circle cx="1050" cy="75" r="180" fill="{C['blue']}" opacity=".08" filter="url(#glow)"/>
    <path d="M920 70a150 150 0 1 0 210 214" fill="none" stroke="url(#accent)" stroke-width="2" stroke-dasharray="8 14" opacity=".45" class="dash"/>
    <g class="reveal"{delay(0)}><rect x="54" y="45" width="10" height="10" rx="3" fill="{C['cyan']}"/><text x="78" y="55" class="label mono" font-size="14">ENGINEERING / ENTERPRISE / CLOUD</text></g>
    <text x="54" y="124" class="title reveal"{delay(1)} font-size="48" fill="url(#heroText)">Abhishek Advani</text>
    <text x="54" y="181" class="title reveal"{delay(2)} font-size="34">Building Enterprise Applications That Scale.</text>
    <text x="56" y="226" class="body reveal"{delay(3)} font-size="17">SAP Technical Lead · SAP BTP Engineer · Full-Stack Developer · Emerging Solution Architect</text>
    <g class="reveal"{delay(4)}>{chip(54, 267, 'SAP BTP + CAP', 150)}{chip(216, 267, 'ABAP RAP + Fiori', 174)}{chip(402, 267, 'React + Node.js', 154)}{chip(568, 267, 'Cloud Architecture', 176)}</g>
    <g transform="translate(1012 160)"><circle r="52" fill="none" stroke="{C['line']}"/><circle r="29" fill="none" stroke="{C['blue']}" opacity=".65"/><circle r="7" fill="{C['cyan']}" class="pulse"/><path d="M-72 0H72M0-72V72" stroke="{C['line']}" opacity=".7"/></g>
    """
    return svg_shell("Abhishek Advani — enterprise engineering portfolio", 1200, 360, body, desc="SAP Technical Lead, SAP BTP Engineer, Full-Stack Developer and emerging Solution Architect.")


SPECIALIZATIONS = [
    ("01", "SAP Engineering", "Enterprise application engineering across SAP's modern stack.", ["SAP BTP", "CAP", "ABAP RAP", "SAPUI5", "Fiori", "OData V2/V4"]),
    ("02", "Full-Stack Engineering", "Product-focused interfaces and dependable service layers.", ["React.js", "Node.js", "Express", "JavaScript", "REST APIs"]),
    ("03", "Cloud & Architecture", "Delivery foundations for integrated, tenant-aware cloud systems.", ["Cloud Foundry", "Integrations", "CI/CD", "Multi-tenant SaaS", "Technical Delivery"]),
]


def specialization(number: str, title: str, summary: str, skills: list[str]) -> str:
    items, x = [], 525
    for text in skills:
        width = max(104, len(text) * 9 + 32)
        if x + width > 1140:
            x = 525
            y = 126
        else:
            y = 78
        items.append(chip(x, y, text, width)); x += width + 12
    body = f"""
      <text x="48" y="58" class="label mono reveal"{delay(0)} font-size="14">SPECIALIZATION {number}</text>
      <text x="48" y="107" class="title reveal"{delay(1)} font-size="32">{esc(title)}</text>
      <text x="48" y="145" class="body reveal"{delay(2)} font-size="17">{esc(summary)}</text>
      <path d="M478 42V158" class="hair"/><g class="reveal"{delay(3)}>{''.join(items)}</g>
      <circle cx="1145" cy="44" r="8" fill="{C['cyan']}" opacity=".7" class="pulse"/>
    """
    return svg_shell(title, 1200, 200, body, desc=summary + " " + ", ".join(skills))


def stack_card() -> str:
    groups = [
        ("SAP APPLICATION", "CAP · ABAP RAP · SAPUI5 · Fiori · OData V2/V4"),
        ("FULL-STACK", "React.js · Node.js · Express · JavaScript · REST APIs"),
        ("CLOUD DELIVERY", "SAP BTP · Cloud Foundry · Integrations · CI/CD · Multi-tenant SaaS"),
    ]
    rows = []
    for i, (label, values) in enumerate(groups):
        y = 112 + i * 82
        rows.append(f'<g class="reveal"{delay(i + 1)}><text x="55" y="{y}" class="label mono" font-size="13">{label}</text><text x="310" y="{y}" class="title" font-size="22">{values}</text><path d="M55 {y + 27}H1145" class="hair"/></g>')
    body = f'<text x="55" y="55" class="title reveal"{delay(0)} font-size="28">Technology stack <tspan class="body" font-size="15" font-weight="400">/ grouped by delivery domain</tspan></text>{"".join(rows)}'
    return svg_shell("Technology stack", 1200, 365, body, desc="SAP application, full-stack and cloud delivery technologies.")


def heatmap_card(data: dict[str, Any]) -> str:
    days = data["days"]
    start = date.fromisoformat(days[0]["date"])
    first_sunday = start
    while first_sunday.weekday() != 6:
        first_sunday -= date.resolution
    colors = [C["quiet"], "#12366b", "#1859a9", C["blue"], C["cyan"]]
    cells, month_labels, seen = [], [], set()
    for i, item in enumerate(days):
        day = date.fromisoformat(item["date"])
        week = (day - first_sunday).days // 7
        weekday = (day.weekday() + 1) % 7
        x, y = 186 + week * 17, 116 + weekday * 17
        delay_value = "" if STATIC else f' style="animation-delay:{.25 + week * .018:.3f}s"'
        cells.append(f'<rect class="cell"{delay_value} x="{x}" y="{y}" width="12" height="12" rx="3" fill="{colors[item["level"]]}"><title>{item["count"]} contributions on {item["date"]}</title></rect>')
        key = item["date"][:7]
        if day.day <= 7 and key not in seen:
            seen.add(key); month_labels.append(f'<text x="{x}" y="96" class="body mono" font-size="11">{day.strftime("%b")}</text>')
    s = data["summary"]
    extra = "" if STATIC else "@keyframes cell{to{opacity:1;transform:scale(1)}}.cell{opacity:0;transform:scale(.25);transform-box:fill-box;transform-origin:center;animation:cell .3s ease-out forwards}"
    body = f"""
      <text x="50" y="54" class="title reveal"{delay(0)} font-size="28">Contribution signal</text>
      <text x="50" y="81" class="body mono reveal"{delay(1)} font-size="13">{esc(data['period']['from'])} → {esc(data['period']['to'])} · PUBLIC GITHUB ACTIVITY</text>
      <text x="50" y="140" class="title" font-size="40">{s['total']}</text><text x="50" y="164" class="body" font-size="14">contributions</text>
      <text x="50" y="210" class="title" font-size="25">{s['active_days']}</text><text x="50" y="231" class="body" font-size="13">active days</text>
      <text x="50" y="266" class="title" font-size="25">{s['longest_streak']}</text><text x="50" y="287" class="body" font-size="13">longest streak</text>
      {''.join(month_labels)}{''.join(cells)}
      <text x="150" y="145" class="body mono" font-size="10">MON</text><text x="150" y="179" class="body mono" font-size="10">WED</text><text x="150" y="213" class="body mono" font-size="10">FRI</text>
      <g transform="translate(1046 274)"><text x="0" y="10" class="body mono" font-size="10">LESS</text>{''.join(f'<rect x="{36 + i*18}" width="12" height="12" rx="3" fill="{color}"/>' for i,color in enumerate(colors))}</g>
    """
    return svg_shell("Verified GitHub contribution heatmap", 1200, 320, body, extra_style=extra, desc=f"{s['total']} public contributions across the displayed rolling year.")


def monthly_card(data: dict[str, Any]) -> str:
    months = data["months"]
    maximum = max((m["count"] for m in months), default=0)
    bars = []
    width = 1020 / max(1, len(months))
    for i, item in enumerate(months):
        height = 150 * item["count"] / max(1, maximum)
        x, y = 95 + i * width, 246 - height
        cls = "best" if item["count"] == maximum and maximum else "bar"
        anim = "" if STATIC else f' style="animation-delay:{.2+i*.05:.2f}s"'
        label = datetime.strptime(item["month"], "%Y-%m").strftime("%b")
        bars.append(f'<g><rect class="{cls}"{anim} x="{x:.1f}" y="{y:.1f}" width="{max(12,width-18):.1f}" height="{max(2,height):.1f}" rx="6" fill="{C["cyan"] if cls == "best" else C["blue"]}" opacity="{1 if cls == "best" else .72}"/><text x="{x+max(12,width-18)/2:.1f}" y="{y-9:.1f}" text-anchor="middle" class="body mono" font-size="11">{item["count"]}</text><text x="{x+max(12,width-18)/2:.1f}" y="276" text-anchor="middle" class="body mono" font-size="11">{label}</text></g>')
    extra = "" if STATIC else "@keyframes grow{to{transform:scaleY(1)}}.bar,.best{transform:scaleY(0);transform-box:fill-box;transform-origin:bottom;animation:grow .55s cubic-bezier(.2,.8,.2,1) forwards}"
    body = f'<text x="50" y="54" class="title reveal"{delay(0)} font-size="28">Monthly contribution cadence</text><text x="50" y="82" class="body mono" font-size="13">VERIFIED COUNTS · ROLLING 12 MONTHS</text><path d="M80 247H1150" class="hair"/>{"".join(bars)}'
    return svg_shell("Monthly GitHub contribution chart", 1200, 310, body, extra_style=extra, desc="Monthly counts calculated from verified public GitHub contribution data.")


def projects_card() -> str:
    projects = [
        ("SAP Fiori Point of Sale", "Material catalog · pricing · stock availability · sales order integration", "SAP / FIORI"),
        ("Enterprise Label Printing", "SAP document APIs · QR labels · PDF generation · bulk printing", "DOCUMENT AUTOMATION"),
        ("SAP Procurement KPI Dashboards", "Procurement analytics · performance indicators · quality monitoring", "ANALYTICS"),
        ("Multi-Tenant SaaS", "React and Node.js architecture · tenant-aware backend services", "CLOUD ARCHITECTURE"),
    ]
    rows = []
    for i, (name, details, domain) in enumerate(projects):
        y = 102 + i * 118
        rows.append(f"""<g class="reveal"{delay(i + 1)}><rect x="48" y="{y-30}" width="1104" height="94" rx="14" fill="{C['panel2']}" stroke="{C['line']}"/><text x="74" y="{y}" class="label mono" font-size="11">{domain}</text><text x="74" y="{y+33}" class="title" font-size="22">{esc(name)}</text><text x="455" y="{y+32}" class="body" font-size="14">{esc(details)}</text><path d="M1122 {y+15}l8 8-8 8" fill="none" stroke="{C['cyan']}" stroke-width="2"/></g>""")
    body = f'<text x="50" y="48" class="title reveal"{delay(0)} font-size="28">Selected engineering systems</text><text x="1150" y="48" text-anchor="end" class="body mono" font-size="12">SANITIZED PORTFOLIO THEMES · NO CLIENT DATA</text>{"".join(rows)}'
    return svg_shell("Selected engineering systems", 1200, 570, body, desc="Sanitized project themes with no confidential client details or source links.")


def activity_card(data: dict[str, Any]) -> str:
    repos = [repo for repo in data.get("repositories", []) if not repo["fork"] and not repo["archived"]]
    events = data.get("recent_activity", [])[:3]
    rows = []
    for i, event in enumerate(events):
        when = (event.get("created_at") or "")[:10] or "—"
        kind = event.get("type", "Activity").replace("Event", "")
        rows.append(f'<g class="reveal"{delay(i+1)}><circle cx="68" cy="{130+i*55}" r="5" fill="{C["cyan"]}"/><text x="90" y="{136+i*55}" class="title" font-size="16">{esc(kind)}</text><text x="230" y="{136+i*55}" class="body mono" font-size="13">{esc(event.get("repository") or "GitHub")}</text><text x="565" y="{136+i*55}" class="body mono" font-size="12">{esc(when)}</text></g>')
    if not rows:
        rows.append(f'<text x="68" y="150" class="body" font-size="16">No recent public events returned by GitHub.</text>')
    repo = repos[0] if repos else None
    repo_block = f'<text x="720" y="142" class="title" font-size="22">{esc(repo["name"])}</text><text x="720" y="175" class="body" font-size="14">{esc(repo.get("description") or "Source for this generated profile portfolio")}</text><text x="720" y="218" class="label mono" font-size="11">{repo["stars"]} STARS · {esc(repo.get("language") or "PROFILE README")}</text>' if repo else '<text x="720" y="150" class="body">No public repository selected.</text>'
    body = f"""
      <text x="50" y="53" class="title reveal"{delay(0)} font-size="28">GitHub activity</text><text x="1150" y="52" text-anchor="end" class="body mono" font-size="12">PUBLIC DATA · {data['summary']['public_repositories']} REPOSITORY</text>
      <path d="M660 90V280" class="hair"/><text x="68" y="92" class="label mono" font-size="11">RECENT PUBLIC EVENTS</text>{''.join(rows)}
      <text x="720" y="92" class="label mono" font-size="11">VERIFIED PUBLIC REPOSITORY</text><g class="reveal"{delay(2)}>{repo_block}<path d="M720 246H1110" stroke="url(#accent)" stroke-width="2"/></g>
    """
    return svg_shell("GitHub activity and repository", 1200, 320, body, desc="Recent public GitHub activity and a verified public repository.")


def footer_card(data: dict[str, Any]) -> str:
    body = f"""
      <text x="48" y="52" class="label mono" font-size="12">CONNECT</text><text x="48" y="94" class="title" font-size="25">github.com/{esc(data['username'])}</text>
      <text x="1152" y="62" text-anchor="end" class="body" font-size="15">SAP engineering · Full-stack delivery · Cloud architecture</text>
      <text x="1152" y="95" text-anchor="end" class="body mono" font-size="11">PROFILE CARDS GENERATED FROM VERSIONED SOURCE</text><circle cx="1128" cy="124" r="4" fill="{C['cyan']}" class="pulse"/>
    """
    return svg_shell("Contact Abhishek Advani", 1200, 145, body, desc=f"Connect on GitHub at {data['profile_url']}.")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_name = handle.name
    os.replace(temp_name, path)


def validate(data: dict[str, Any]) -> None:
    required = {"username", "period", "summary", "months", "days", "repositories"}
    if not required.issubset(data) or len(data["days"]) != 365:
        raise ValueError("contributions.json does not match schema version 1")
    if data["summary"]["total"] != sum(day["count"] for day in data["days"]):
        raise ValueError("contribution total does not match daily data")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--output", type=Path, default=CARDS_DIR)
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8")); validate(data)
    cards = {
        "hero.svg": hero(),
        "specialization-sap.svg": specialization(*SPECIALIZATIONS[0]),
        "specialization-fullstack.svg": specialization(*SPECIALIZATIONS[1]),
        "specialization-cloud.svg": specialization(*SPECIALIZATIONS[2]),
        "stack.svg": stack_card(), "contributions.svg": heatmap_card(data),
        "monthly.svg": monthly_card(data), "projects.svg": projects_card(),
        "activity.svg": activity_card(data), "footer.svg": footer_card(data),
    }
    for name, content in cards.items():
        atomic_write(args.output / name, content)
    print(f"Rendered {len(cards)} {'static ' if STATIC else ''}SVG cards in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
