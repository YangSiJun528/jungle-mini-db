#!/usr/bin/env python3
"""Generate a glass-style HTML report for the B-tree library benchmark lab."""

from __future__ import annotations

import argparse
import html
import json
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reum-koo" / "docs" / "reum-010-btree-library-benchmark-compare.html"

LIBRARY_STYLES = {
    "reum memory_bptree": {
        "slug": "reum",
        "label": "reum",
        "family": "B+ tree",
        "tone": "프로젝트 내부 기준선",
    },
    "Kronuz/cpp-btree": {
        "slug": "kronuz",
        "label": "kronuz",
        "family": "B-tree",
        "tone": "dense key 강자",
    },
    "frozenca/BTree": {
        "slug": "frozenca",
        "label": "frozenca",
        "family": "B-tree",
        "tone": "hot-spot lookup 강자",
    },
    "habedi/bptree": {
        "slug": "habedi",
        "label": "habedi",
        "family": "B+ tree",
        "tone": "꾸준한 lookup",
    },
    "tidwall/btree.c": {
        "slug": "tidwall",
        "label": "tidwall",
        "family": "B-tree",
        "tone": "C 단일 파일 구현",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, help="path to latest_results.json")
    parser.add_argument("--report", required=True, help="path to latest_detailed_report.md")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="output HTML path")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_section_lines(markdown: str, heading: str) -> list[str]:
    lines = markdown.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            break
    if start is None:
        return []

    collected: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        collected.append(line)
    return collected


def extract_numbered_items(markdown: str, heading: str) -> list[str]:
    items = []
    for line in extract_section_lines(markdown, heading):
        stripped = line.strip()
        if stripped and stripped[0].isdigit() and ". " in stripped:
            items.append(stripped.split(". ", 1)[1])
    return items


def extract_bullets(markdown: str, heading: str) -> list[str]:
    items = []
    for line in extract_section_lines(markdown, heading):
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:])
    return items


def extract_scenario_descriptions(markdown: str) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for line in extract_section_lines(markdown, "## 3. Scenario Matrix"):
        stripped = line.strip()
        if stripped.startswith("| `") and stripped.count("|") >= 3:
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) >= 2:
                scenario_id = cells[0].strip("`")
                descriptions[scenario_id] = cells[1]
    return descriptions


def format_number(value: float) -> str:
    return f"{value:,.2f}"


def format_int(value: int) -> str:
    return f"{value:,}"


def group_results(results: list[dict[str, object]]) -> dict[int, dict[str, list[dict[str, object]]]]:
    grouped: dict[int, dict[str, list[dict[str, object]]]] = defaultdict(lambda: defaultdict(list))
    for row in results:
        grouped[int(row["records"])][str(row["scenario_id"])].append(row)
    return grouped


def rank_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (row["lookup_ops_per_second"], row["insert_ops_per_second"]),
        reverse=True,
    )


def compute_win_counts(results: list[dict[str, object]]) -> tuple[dict[str, int], dict[str, int]]:
    lookup_wins: dict[str, int] = defaultdict(int)
    insert_wins: dict[str, int] = defaultdict(int)
    for scenarios in group_results(results).values():
        for rows in scenarios.values():
            lookup_winner = max(rows, key=lambda row: row["lookup_ops_per_second"])
            insert_winner = max(rows, key=lambda row: row["insert_ops_per_second"])
            lookup_wins[str(lookup_winner["library_name"])] += 1
            insert_wins[str(insert_winner["library_name"])] += 1
    return dict(lookup_wins), dict(insert_wins)


def compute_average_lookup_rank(results: list[dict[str, object]]) -> dict[str, float]:
    ranks: dict[str, list[int]] = defaultdict(list)
    for scenarios in group_results(results).values():
        for rows in scenarios.values():
            for rank, row in enumerate(rank_rows(rows), start=1):
                ranks[str(row["library_name"])].append(rank)
    return {library: statistics.mean(values) for library, values in ranks.items()}


def compute_library_profiles(
    results: list[dict[str, object]],
    lookup_wins: dict[str, int],
    insert_wins: dict[str, int],
) -> list[dict[str, object]]:
    avg_lookup_rank = compute_average_lookup_rank(results)
    profiles = []
    libraries = sorted({str(row["library_name"]) for row in results})
    for library in libraries:
        rows = [row for row in results if row["library_name"] == library]
        best_lookup = max(rows, key=lambda row: row["lookup_ops_per_second"])
        best_insert = max(rows, key=lambda row: row["insert_ops_per_second"])
        profiles.append(
            {
                "name": library,
                "slug": LIBRARY_STYLES[library]["slug"],
                "family": rows[0]["family"],
                "tone": LIBRARY_STYLES[library]["tone"],
                "lookup_wins": lookup_wins.get(library, 0),
                "insert_wins": insert_wins.get(library, 0),
                "avg_lookup_rank": avg_lookup_rank[library],
                "best_lookup": best_lookup,
                "best_insert": best_insert,
            }
        )
    return profiles


def compute_size_lookup_wins(
    grouped: dict[int, dict[str, list[dict[str, object]]]]
) -> dict[int, dict[str, int]]:
    by_size: dict[int, dict[str, int]] = {}
    for record_count, scenarios in grouped.items():
        wins: dict[str, int] = defaultdict(int)
        for rows in scenarios.values():
            winner = max(rows, key=lambda row: row["lookup_ops_per_second"])
            wins[str(winner["library_name"])] += 1
        by_size[record_count] = dict(wins)
    return by_size


def metric_bar(value: float, maximum: float, library_slug: str) -> str:
    width = 12 if maximum <= 0 else max(12.0, (value / maximum) * 100.0)
    return (
        f'<div class="metric-bar">'
        f'<span class="metric-fill {library_slug}" style="width: {width:.2f}%"></span>'
        f"<em>{format_number(value)}</em>"
        f"</div>"
    )


def render_ranking_table(rows: list[dict[str, object]]) -> str:
    ranked = rank_rows(rows)
    max_insert = max(float(row["insert_ops_per_second"]) for row in ranked)
    max_lookup = max(float(row["lookup_ops_per_second"]) for row in ranked)
    body = []
    for rank, row in enumerate(ranked, start=1):
        library = str(row["library_name"])
        slug = LIBRARY_STYLES[library]["slug"]
        winner_class = " winner" if rank == 1 else ""
        body.append(
            "<tr class='library-row {winner}'>"
            "<td><span class='rank-pill'>{rank}</span></td>"
            "<td><span class='library-pill {slug}'>{name}</span></td>"
            "<td>{family}</td>"
            "<td>{insert_bar}</td>"
            "<td>{lookup_bar}</td>"
            "<td>{insert_seconds:.6f}</td>"
            "<td>{lookup_seconds:.6f}</td>"
            "</tr>".format(
                winner=winner_class.strip(),
                rank=rank,
                slug=slug,
                name=html.escape(library),
                family=html.escape(str(row["family"])),
                insert_bar=metric_bar(float(row["insert_ops_per_second"]), max_insert, slug),
                lookup_bar=metric_bar(float(row["lookup_ops_per_second"]), max_lookup, slug),
                insert_seconds=float(row["insert_seconds"]),
                lookup_seconds=float(row["lookup_seconds"]),
            )
        )

    return """
    <table class="ranking-table">
      <thead>
        <tr>
          <th>Rank</th>
          <th>Library</th>
          <th>Family</th>
          <th>Insert ops/s</th>
          <th>Lookup ops/s</th>
          <th>Insert sec</th>
          <th>Lookup sec</th>
        </tr>
      </thead>
      <tbody>
        {body}
      </tbody>
    </table>
    """.format(body="\n".join(body))


def render_library_legend(libraries: list[str]) -> str:
    chips = []
    for library in libraries:
        style = LIBRARY_STYLES[library]
        chips.append(
            "<span class='glass-chip'><span class='legend-dot {slug}'></span>{label} · {family}</span>".format(
                slug=style["slug"],
                label=html.escape(library),
                family=html.escape(style["family"]),
            )
        )
    return "".join(chips)


def render_profile_cards(profiles: list[dict[str, object]], max_lookup_wins: int, max_insert_wins: int) -> str:
    cards = []
    for profile in profiles:
        slug = profile["slug"]
        lookup_width = 0 if max_lookup_wins == 0 else (profile["lookup_wins"] / max_lookup_wins) * 100
        insert_width = 0 if max_insert_wins == 0 else (profile["insert_wins"] / max_insert_wins) * 100
        cards.append(
            """
            <article class="glass-card profile-card">
              <div class="card-topline">Library Profile</div>
              <h3><span class="library-pill {slug}">{name}</span></h3>
              <p class="muted">{tone}</p>
              <div class="profile-meta">
                <span class="mini-stat">avg lookup rank <strong>{avg_rank:.2f}</strong></span>
                <span class="mini-stat">family <strong>{family}</strong></span>
              </div>
              <div class="bar-label">Lookup wins <strong>{lookup_wins}</strong></div>
              <div class="metric-bar large"><span class="metric-fill {slug}" style="width: {lookup_width:.2f}%"></span></div>
              <div class="bar-label">Insert wins <strong>{insert_wins}</strong></div>
              <div class="metric-bar large"><span class="metric-fill {slug}" style="width: {insert_width:.2f}%"></span></div>
              <div class="profile-grid">
                <div class="mini-panel">
                  <strong>Best Lookup</strong>
                  <span>{lookup_case}</span>
                  <em>{lookup_value}</em>
                </div>
                <div class="mini-panel">
                  <strong>Best Insert</strong>
                  <span>{insert_case}</span>
                  <em>{insert_value}</em>
                </div>
              </div>
            </article>
            """.format(
                slug=slug,
                name=html.escape(str(profile["name"])),
                tone=html.escape(str(profile["tone"])),
                avg_rank=float(profile["avg_lookup_rank"]),
                family=html.escape(str(profile["family"])),
                lookup_wins=int(profile["lookup_wins"]),
                lookup_width=lookup_width,
                insert_wins=int(profile["insert_wins"]),
                insert_width=insert_width,
                lookup_case=html.escape(
                    f"{int(profile['best_lookup']['records']):,} · {profile['best_lookup']['scenario_name']}"
                ),
                lookup_value=html.escape(f"{format_number(float(profile['best_lookup']['lookup_ops_per_second']))} ops/s"),
                insert_case=html.escape(
                    f"{int(profile['best_insert']['records']):,} · {profile['best_insert']['scenario_name']}"
                ),
                insert_value=html.escape(f"{format_number(float(profile['best_insert']['insert_ops_per_second']))} ops/s"),
            )
        )
    return "\n".join(cards)


def render_dataset_sections(
    record_counts: list[int],
    scenario_order: list[str],
    scenario_name_map: dict[str, str],
    scenario_descriptions: dict[str, str],
    grouped: dict[int, dict[str, list[dict[str, object]]]],
    size_lookup_wins: dict[int, dict[str, int]],
) -> str:
    sections = []
    for index, record_count in enumerate(record_counts, start=1):
        winner_chips = []
        for library, wins in sorted(size_lookup_wins[record_count].items(), key=lambda item: (-item[1], item[0])):
            if wins <= 0:
                continue
            slug = LIBRARY_STYLES[library]["slug"]
            winner_chips.append(
                f"<span class='glass-chip'><span class='legend-dot {slug}'></span>{html.escape(library)} · lookup wins {wins}</span>"
            )

        scenario_cards = []
        for scenario_id in scenario_order:
            rows = grouped[record_count][scenario_id]
            scenario_cards.append(
                """
                <article class="glass-card scenario-card">
                  <div class="card-topline">{scenario_id}</div>
                  <h4>{scenario_name}</h4>
                  <p class="muted">{scenario_desc}</p>
                  {table}
                </article>
                """.format(
                    scenario_id=html.escape(scenario_id),
                    scenario_name=html.escape(scenario_name_map[scenario_id]),
                    scenario_desc=html.escape(scenario_descriptions.get(scenario_id, "")),
                    table=render_ranking_table(rows),
                )
            )

        sections.append(
            """
            <details class="glass-section" {open_attr} id="dataset-{index}">
              <summary>
                <div class="summary-left">
                  <span class="summary-tag">Dataset {index}</span>
                  <span class="summary-title">{record_count} records</span>
                  <span class="summary-sub">같은 6개 시나리오를 이 데이터 크기에서 다시 비교한 결과</span>
                </div>
                <span class="summary-toggle">펼치기</span>
              </summary>
              <div class="section-content">
                <div class="content-grid two">
                  <div class="glass-card">
                    <div class="card-topline">Lookup Winners At This Size</div>
                    <div class="chips-wrap">{winner_chips}</div>
                  </div>
                  <div class="glass-card">
                    <div class="card-topline">Reading Tip</div>
                    <p class="muted">10,000건은 아주 빠른 구간이라 수치가 조금 흔들릴 수 있습니다. 실제 결론은 100,000건과 1,000,000건 쪽에 더 무게를 두고 읽는 것이 안전합니다.</p>
                  </div>
                </div>
                <div class="content-grid one">
                  {scenario_cards}
                </div>
              </div>
            </details>
            """.format(
                open_attr="open" if record_count in {100000, 1000000} else "",
                index=index,
                record_count=format_int(record_count),
                winner_chips="".join(winner_chips),
                scenario_cards="\n".join(scenario_cards),
            )
        )
    return "\n".join(sections)


def render_html(
    data: dict[str, object],
    report_text: str,
    output_path: Path,
    results_path: Path,
    report_path: Path,
) -> str:
    results = list(data["results"])
    record_counts = sorted(int(count) for count in data["record_counts"])
    scenario_order = list(data["scenario_ids"])
    grouped = group_results(results)
    lookup_wins, insert_wins = compute_win_counts(results)
    profiles = compute_library_profiles(results, lookup_wins, insert_wins)
    size_lookup_wins = compute_size_lookup_wins(grouped)
    scenario_descriptions = extract_scenario_descriptions(report_text)
    incidents = extract_numbered_items(report_text, "## 4. What Happened During The Work")
    findings = extract_bullets(report_text, "## 5. High-Level Findings")

    libraries = sorted({str(row["library_name"]) for row in results})
    scenario_name_map = {
        str(row["scenario_id"]): str(row["scenario_name"])
        for row in results
    }
    max_lookup_wins = max(lookup_wins.values())
    max_insert_wins = max(insert_wins.values())
    top_lookup = max(results, key=lambda row: row["lookup_ops_per_second"])
    top_insert = max(results, key=lambda row: row["insert_ops_per_second"])
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    return """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>reum-010 B-tree 라이브러리 비교 실험 리포트</title>
  <style>
    :root {{
      --bg-top: #e9eef5;
      --bg-mid: #cfd9e6;
      --bg-bottom: #d7c7ba;
      --glass: rgba(255, 255, 255, 0.22);
      --glass-strong: rgba(255, 255, 255, 0.38);
      --glass-soft: rgba(255, 255, 255, 0.15);
      --line: rgba(255, 255, 255, 0.50);
      --line-soft: rgba(255, 255, 255, 0.22);
      --ink: #18212c;
      --muted: rgba(24, 33, 44, 0.74);
      --shadow: 0 24px 60px rgba(28, 39, 54, 0.15);
      --reum: #2f7b73;
      --kronuz: #6a5d92;
      --frozenca: #a07a3e;
      --habedi: #4b8b68;
      --tidwall: #8b6c56;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", sans-serif;
      line-height: 1.6;
      background:
        radial-gradient(circle at 10% 10%, rgba(255,255,255,0.64), transparent 24rem),
        radial-gradient(circle at 84% 16%, rgba(47,123,115,0.14), transparent 20rem),
        radial-gradient(circle at 78% 76%, rgba(106,93,146,0.10), transparent 18rem),
        radial-gradient(circle at 20% 82%, rgba(160,122,62,0.12), transparent 16rem),
        linear-gradient(135deg, var(--bg-top), var(--bg-mid) 52%, var(--bg-bottom));
      min-height: 100vh;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(120deg, rgba(255,255,255,0.32), transparent 30%, rgba(255,255,255,0.16) 52%, transparent 70%),
        radial-gradient(circle at top, rgba(255,255,255,0.16), transparent 38%);
      mix-blend-mode: screen;
      opacity: 0.75;
    }}
    .page {{
      width: min(1500px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 64px;
    }}
    .hero, .legend, .glass-section {{
      background: linear-gradient(180deg, rgba(255,255,255,0.22), rgba(255,255,255,0.12));
      border: 1px solid var(--line);
      border-radius: 28px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(24px) saturate(150%);
      -webkit-backdrop-filter: blur(24px) saturate(150%);
      margin-bottom: 20px;
      position: relative;
      overflow: hidden;
    }}
    .hero::before, .legend::before, .glass-section::before {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(135deg, rgba(255,255,255,0.28), transparent 40%, rgba(255,255,255,0.12) 70%, transparent);
      pointer-events: none;
    }}
    .hero, .legend {{ padding: 26px; }}
    .hero h1 {{
      margin: 0 0 10px;
      font-size: clamp(2rem, 2vw, 2.8rem);
      line-height: 1.14;
      letter-spacing: -0.04em;
    }}
    .hero p, .muted {{
      margin: 0;
      color: var(--muted);
    }}
    .hero p + p {{ margin-top: 10px; }}
    .meta-grid, .content-grid.two, .content-grid.three {{
      display: grid;
      gap: 14px;
    }}
    .meta-grid {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-top: 18px; }}
    .content-grid.two {{ grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
    .content-grid.three {{ grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
    .content-grid.one {{ display: grid; gap: 14px; margin-top: 14px; }}
    .meta-card, .glass-card {{
      background: var(--glass-strong);
      border: 1px solid var(--line-soft);
      border-radius: 22px;
      padding: 16px 18px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }}
    .meta-card strong, .card-topline {{
      display: block;
      margin-bottom: 4px;
      font-size: 0.78rem;
      color: rgba(45, 78, 104, 0.88);
      text-transform: uppercase;
      letter-spacing: 0.10em;
      font-weight: 800;
    }}
    .meta-card span {{
      font-weight: 800;
      font-size: 1.02rem;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}
    .glass-button {{
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.24);
      color: var(--ink);
      border-radius: 999px;
      padding: 10px 14px;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
    }}
    .toc {{
      margin: 18px 0 0;
      padding: 0;
      list-style: none;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 10px;
    }}
    .toc a {{
      display: block;
      text-decoration: none;
      color: inherit;
      padding: 12px 14px;
      border-radius: 18px;
      background: rgba(255,255,255,0.22);
      border: 1px solid var(--line-soft);
      font-weight: 700;
    }}
    .legend h2 {{ margin: 0 0 12px; }}
    .glass-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin: 6px 8px 0 0;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.24);
      border: 1px solid var(--line-soft);
      font-size: 0.92rem;
      font-weight: 700;
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }}
    .legend-dot {{
      width: 12px;
      height: 12px;
      border-radius: 999px;
      display: inline-block;
    }}
    .reum {{ background: var(--reum); }}
    .kronuz {{ background: var(--kronuz); }}
    .frozenca {{ background: var(--frozenca); }}
    .habedi {{ background: var(--habedi); }}
    .tidwall {{ background: var(--tidwall); }}
    details.glass-section > summary {{
      list-style: none;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      padding: 22px 24px;
      position: relative;
      z-index: 1;
    }}
    details.glass-section > summary::-webkit-details-marker {{ display: none; }}
    .summary-left {{
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }}
    .summary-tag {{
      display: inline-block;
      font-size: 0.76rem;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(45, 78, 104, 0.88);
    }}
    .summary-title {{
      font-size: clamp(1.2rem, 1.4vw, 1.55rem);
      font-weight: 800;
      letter-spacing: -0.02em;
    }}
    .summary-sub {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .summary-toggle {{
      flex: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 0.9rem;
      font-weight: 700;
      color: var(--muted);
    }}
    .summary-toggle::before {{
      content: "▾";
      transition: transform 180ms ease;
    }}
    details.glass-section:not([open]) .summary-toggle::before {{
      transform: rotate(-90deg);
    }}
    .section-content {{
      position: relative;
      z-index: 1;
      padding: 0 24px 24px;
    }}
    .chips-wrap {{ margin-top: 8px; }}
    .diagram-board {{
      display: grid;
      gap: 12px;
      margin-top: 14px;
    }}
    .diagram-row {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      align-items: stretch;
    }}
    .diagram-node {{
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.22);
      border: 1px solid var(--line-soft);
      min-height: 100px;
    }}
    .diagram-node strong {{ display: block; margin-bottom: 6px; }}
    .timeline {{
      display: grid;
      gap: 12px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}
    .timeline li {{
      display: grid;
      grid-template-columns: 42px 1fr;
      gap: 12px;
      align-items: start;
      padding: 14px 16px;
      background: rgba(255,255,255,0.22);
      border-radius: 18px;
      border: 1px solid var(--line-soft);
    }}
    .timeline .step {{
      width: 42px;
      height: 42px;
      border-radius: 14px;
      background: rgba(255,255,255,0.45);
      display: grid;
      place-items: center;
      font-weight: 800;
    }}
    .library-pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      color: white;
      font-weight: 800;
      font-size: 0.9rem;
    }}
    .library-pill.reum {{ background: linear-gradient(135deg, #2f7b73, #4f9e94); }}
    .library-pill.kronuz {{ background: linear-gradient(135deg, #6a5d92, #8f84b9); }}
    .library-pill.frozenca {{ background: linear-gradient(135deg, #a07a3e, #c59d56); }}
    .library-pill.habedi {{ background: linear-gradient(135deg, #4b8b68, #69aa82); }}
    .library-pill.tidwall {{ background: linear-gradient(135deg, #8b6c56, #b08b70); }}
    .profile-card h3, .scenario-card h4 {{ margin: 0 0 8px; }}
    .profile-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 10px 0 16px;
    }}
    .mini-stat, .mini-panel {{
      display: block;
      padding: 10px 12px;
      border-radius: 16px;
      background: rgba(255,255,255,0.22);
      border: 1px solid var(--line-soft);
    }}
    .mini-panel strong, .mini-panel span, .mini-panel em {{
      display: block;
    }}
    .mini-panel em {{
      font-style: normal;
      font-weight: 800;
      margin-top: 4px;
    }}
    .profile-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      margin-top: 14px;
    }}
    .bar-label {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      font-size: 0.92rem;
      margin: 10px 0 6px;
      color: var(--muted);
    }}
    .metric-bar {{
      position: relative;
      background: rgba(255,255,255,0.22);
      border: 1px solid var(--line-soft);
      border-radius: 999px;
      height: 32px;
      overflow: hidden;
      min-width: 210px;
    }}
    .metric-bar.large {{ height: 18px; min-width: auto; }}
    .metric-fill {{
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      border-radius: inherit;
      opacity: 0.92;
    }}
    .metric-fill.reum {{ background: linear-gradient(90deg, rgba(47,123,115,0.84), rgba(79,158,148,0.98)); }}
    .metric-fill.kronuz {{ background: linear-gradient(90deg, rgba(106,93,146,0.84), rgba(143,132,185,0.98)); }}
    .metric-fill.frozenca {{ background: linear-gradient(90deg, rgba(160,122,62,0.84), rgba(197,157,86,0.98)); }}
    .metric-fill.habedi {{ background: linear-gradient(90deg, rgba(75,139,104,0.84), rgba(105,170,130,0.98)); }}
    .metric-fill.tidwall {{ background: linear-gradient(90deg, rgba(139,108,86,0.84), rgba(176,139,112,0.98)); }}
    .metric-bar em {{
      position: relative;
      z-index: 1;
      display: inline-flex;
      align-items: center;
      height: 100%;
      padding: 0 10px;
      font-style: normal;
      font-weight: 700;
      color: rgba(24,33,44,0.88);
    }}
    .ranking-table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0 10px;
      margin-top: 12px;
      font-size: 0.95rem;
    }}
    .ranking-table th {{
      text-align: left;
      padding: 0 10px 6px;
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .ranking-table td {{
      padding: 10px;
      background: rgba(255,255,255,0.20);
      border-top: 1px solid var(--line-soft);
      border-bottom: 1px solid var(--line-soft);
      vertical-align: middle;
    }}
    .ranking-table td:first-child {{
      border-left: 1px solid var(--line-soft);
      border-top-left-radius: 16px;
      border-bottom-left-radius: 16px;
    }}
    .ranking-table td:last-child {{
      border-right: 1px solid var(--line-soft);
      border-top-right-radius: 16px;
      border-bottom-right-radius: 16px;
    }}
    .ranking-table tr.winner td {{
      background: rgba(255,255,255,0.32);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
    }}
    .rank-pill {{
      display: inline-grid;
      place-items: center;
      width: 32px;
      height: 32px;
      border-radius: 999px;
      font-weight: 800;
      background: rgba(255,255,255,0.42);
    }}
    .findings-list {{
      margin: 0;
      padding-left: 18px;
    }}
    .findings-list li + li {{ margin-top: 8px; }}
    code {{
      background: rgba(255,255,255,0.25);
      border-radius: 8px;
      padding: 2px 6px;
      font-size: 0.92em;
    }}
    @media (max-width: 920px) {{
      .ranking-table {{
        display: block;
        overflow-x: auto;
      }}
      .metric-bar {{ min-width: 170px; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>reum-010 B-tree 라이브러리 비교 실험 리포트</h1>
      <p>이번 HTML은 <code>reum-008</code>처럼 읽기 편한 구조로, 다섯 가지 B-tree/B+tree 구현을 같은 규칙으로 비교한 결과를 한 화면에 모아 보여줍니다.</p>
      <p>코드 diff 대신 이번엔 실험 구조, 시나리오, 중간에 생긴 일, 라이브러리별 성향, 데이터셋 크기별 순위 변화를 따라가며 읽도록 구성했습니다.</p>
      <div class="meta-grid">
        <div class="meta-card"><strong>Compared Libraries</strong><span>{library_count}</span></div>
        <div class="meta-card"><strong>Dataset Sizes</strong><span>{record_counts}</span></div>
        <div class="meta-card"><strong>Scenario Count</strong><span>{scenario_count}</span></div>
        <div class="meta-card"><strong>Total Measured Cases</strong><span>{case_count}</span></div>
        <div class="meta-card"><strong>Best Lookup Peak</strong><span>{best_lookup}</span></div>
        <div class="meta-card"><strong>Best Insert Peak</strong><span>{best_insert}</span></div>
      </div>
      <div class="toolbar">
        <button class="glass-button" onclick="toggleAll(true)">모두 펼치기</button>
        <button class="glass-button" onclick="toggleAll(false)">모두 접기</button>
        <button class="glass-button" onclick="openDatasets()">데이터셋 섹션만 펼치기</button>
      </div>
      <ul class="toc">
        <li><a href="#overview">실험 개요</a></li>
        <li><a href="#journey">중간에 생긴 일</a></li>
        <li><a href="#profiles">라이브러리별 성향</a></li>
        <li><a href="#dataset-1">10,000건 결과</a></li>
        <li><a href="#dataset-2">100,000건 결과</a></li>
        <li><a href="#dataset-3">1,000,000건 결과</a></li>
      </ul>
    </section>

    <section class="legend">
      <h2>Legend</h2>
      <p class="muted">색은 라이브러리별 식별용이고, 순위는 기본적으로 <strong>lookup ops/s</strong> 우선, 동률이면 <strong>insert ops/s</strong> 순으로 정렬했습니다.</p>
      <div class="chips-wrap">{legend_chips}</div>
    </section>

    <details class="glass-section" id="overview" open>
      <summary>
        <div class="summary-left">
          <span class="summary-tag">Overview</span>
          <span class="summary-title">실험 구조와 읽는 법</span>
          <span class="summary-sub">브랜치, 폴더 구조, 공통 실행기, 어댑터 방식, 시나리오 설계를 한 번에 훑습니다.</span>
        </div>
        <span class="summary-toggle">펼치기</span>
      </summary>
      <div class="section-content">
        <div class="content-grid two">
          <div class="glass-card">
            <div class="card-topline">Experiment Architecture</div>
            <div class="diagram-board">
              <div class="diagram-row">
                <div class="diagram-node">
                  <strong>separate branch</strong>
                  <span>기존 작업 트리를 건드리지 않기 위해 <code>btree-library-benchmark</code> worktree에서 실험</span>
                </div>
                <div class="diagram-node">
                  <strong>common runner</strong>
                  <span>같은 데이터 생성, 같은 정답 검증, 같은 출력 형식을 유지</span>
                </div>
                <div class="diagram-node">
                  <strong>adapter layer</strong>
                  <span><code>create / insert / get / destroy</code> 네 함수만 통일</span>
                </div>
              </div>
              <div class="diagram-row">
                <div class="diagram-node">
                  <strong>third-party libs</strong>
                  <span>reum, Kronuz, frozenca, habedi, tidwall 다섯 구현을 같은 시험장에 올림</span>
                </div>
                <div class="diagram-node">
                  <strong>results</strong>
                  <span><code>latest_results.json</code>, <code>latest_summary.md</code>, <code>latest_detailed_report.md</code> 생성</span>
                </div>
                <div class="diagram-node">
                  <strong>cleanup rule</strong>
                  <span>실행마다 <code>build/</code> 와 <code>results/runtime/</code> 초기화</span>
                </div>
              </div>
            </div>
          </div>
          <div class="glass-card">
            <div class="card-topline">Scenario Matrix</div>
            <div class="diagram-board">
              <div class="diagram-row">
                <div class="diagram-node"><strong>dense_seq_build_rand_get</strong><span>{scenario_a}</span></div>
                <div class="diagram-node"><strong>dense_rand_build_rand_get</strong><span>{scenario_b}</span></div>
                <div class="diagram-node"><strong>dense_rev_build_rand_get</strong><span>{scenario_c}</span></div>
              </div>
              <div class="diagram-row">
                <div class="diagram-node"><strong>dense_seq_build_seq_get</strong><span>{scenario_d}</span></div>
                <div class="diagram-node"><strong>dense_rand_build_hot_get</strong><span>{scenario_e}</span></div>
                <div class="diagram-node"><strong>sparse_rand_build_rand_get</strong><span>{scenario_f}</span></div>
              </div>
            </div>
          </div>
        </div>
        <div class="content-grid two" style="margin-top: 14px;">
          <div class="glass-card">
            <div class="card-topline">Source Snapshot</div>
            <p class="muted">결과 JSON: <code>{results_path}</code></p>
            <p class="muted">상세 리포트: <code>{report_path}</code></p>
            <p class="muted">HTML 생성 시각: <code>{generated_at}</code></p>
          </div>
          <div class="glass-card">
            <div class="card-topline">Fast Reading Tip</div>
            <p class="muted"><strong>큰 결론</strong>은 상단의 Winner Count와 Library Profile에서, <strong>구체적 차이</strong>는 각 데이터셋 섹션의 시나리오 카드에서 읽으면 가장 빠릅니다.</p>
          </div>
        </div>
      </div>
    </details>

    <details class="glass-section" id="journey" open>
      <summary>
        <div class="summary-left">
          <span class="summary-tag">Journey</span>
          <span class="summary-title">중간에 생긴 일과 해석 포인트</span>
          <span class="summary-sub">단순 결과표가 아니라, 실험 도중 구조가 어떻게 커지고 무엇이 탈락했는지도 같이 남겼습니다.</span>
        </div>
        <span class="summary-toggle">펼치기</span>
      </summary>
      <div class="section-content">
        <div class="content-grid two">
          <div class="glass-card">
            <div class="card-topline">What Happened During The Work</div>
            <ol class="timeline">
              {incident_items}
            </ol>
          </div>
          <div class="glass-card">
            <div class="card-topline">High-Level Findings</div>
            <ul class="findings-list">
              {finding_items}
            </ul>
          </div>
        </div>
      </div>
    </details>

    <details class="glass-section" id="profiles" open>
      <summary>
        <div class="summary-left">
          <span class="summary-tag">Profiles</span>
          <span class="summary-title">라이브러리별 성향 요약</span>
          <span class="summary-sub">우승 횟수, 평균 lookup 순위, 가장 잘 나온 케이스를 카드 형태로 모았습니다.</span>
        </div>
        <span class="summary-toggle">펼치기</span>
      </summary>
      <div class="section-content">
        <div class="content-grid three">
          {profile_cards}
        </div>
      </div>
    </details>

    {dataset_sections}
  </div>

  <script>
    function toggleAll(open) {{
      document.querySelectorAll('details.glass-section').forEach((detail) => {{
        detail.open = open;
      }});
    }}
    function openDatasets() {{
      document.querySelectorAll('details.glass-section').forEach((detail) => {{
        detail.open = detail.id.startsWith('dataset-');
      }});
    }}
  </script>
</body>
</html>
""".format(
        library_count=len(libraries),
        record_counts=", ".join(format_int(count) for count in record_counts),
        scenario_count=len(scenario_order),
        case_count=format_int(len(results)),
        best_lookup=html.escape(
            f"{top_lookup['library_name']} · {format_number(float(top_lookup['lookup_ops_per_second']))} ops/s"
        ),
        best_insert=html.escape(
            f"{top_insert['library_name']} · {format_number(float(top_insert['insert_ops_per_second']))} ops/s"
        ),
        legend_chips=render_library_legend(libraries),
        scenario_a=html.escape(scenario_descriptions.get("dense_seq_build_rand_get", "")),
        scenario_b=html.escape(scenario_descriptions.get("dense_rand_build_rand_get", "")),
        scenario_c=html.escape(scenario_descriptions.get("dense_rev_build_rand_get", "")),
        scenario_d=html.escape(scenario_descriptions.get("dense_seq_build_seq_get", "")),
        scenario_e=html.escape(scenario_descriptions.get("dense_rand_build_hot_get", "")),
        scenario_f=html.escape(scenario_descriptions.get("sparse_rand_build_rand_get", "")),
        results_path=html.escape(str(results_path)),
        report_path=html.escape(str(report_path)),
        generated_at=html.escape(generated_at),
        incident_items="".join(
            f"<li><span class='step'>{index}</span><div>{html.escape(item)}</div></li>"
            for index, item in enumerate(incidents, start=1)
        ),
        finding_items="".join(f"<li>{html.escape(item)}</li>" for item in findings),
        profile_cards=render_profile_cards(profiles, max_lookup_wins, max_insert_wins),
        dataset_sections=render_dataset_sections(
            record_counts,
            scenario_order,
            scenario_name_map,
            scenario_descriptions,
            grouped,
            size_lookup_wins,
        ),
    )


def main() -> int:
    args = parse_args()
    results_path = Path(args.results).resolve()
    report_path = Path(args.report).resolve()
    output_path = Path(args.output).resolve()

    data = load_json(results_path)
    report_text = read_text(report_path)
    html_text = render_html(data, report_text, output_path, results_path, report_path)
    output_path.write_text(html_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
