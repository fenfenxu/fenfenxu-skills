#!/usr/bin/env python3
"""Initialize discovery/ scaffolding next to a target skill."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-dir", type=Path, required=True, help="path to skills/<name>/")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--from-queries", type=Path, default=None, help="optional existing queries.json")
    parser.add_argument("--template", type=Path, default=None)
    args = parser.parse_args()

    skill_dir = args.skill_dir.resolve()
    if not (skill_dir / "SKILL.md").exists():
        raise SystemExit(f"SKILL.md not found in {skill_dir}")

    name = skill_dir.name
    discovery = skill_dir / "discovery"
    iterations = discovery / "iterations"
    discovery.mkdir(exist_ok=True)
    iterations.mkdir(exist_ok=True)

    queries_path = discovery / "queries.json"
    if args.from_queries:
        shutil.copy(args.from_queries, queries_path)
        data = json.loads(queries_path.read_text())
        data["target"] = {"owner": args.owner, "repo": args.repo, "skill": name}
        queries_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    elif not queries_path.exists():
        template = args.template
        if template is None:
            template = Path(__file__).resolve().parents[1] / "assets" / "queries.template.json"
        data = json.loads(template.read_text())
        data["target"] = {"owner": args.owner, "repo": args.repo, "skill": name}
        for case in data["cases"]:
            if case.get("query") == "skill-name":
                case["query"] = name
            if case.get("query") == "skill name phrase":
                case["query"] = name.replace("-", " ")
        data["pass"] = f"result id contains {args.owner} and {name}"
        queries_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    changelog = iterations / "CHANGELOG.md"
    if not changelog.exists():
        changelog.write_text(
            f"# Discovery iterations — {name}\n\n"
            "Append one section per loop. Keep queries.json frozen within a campaign.\n"
        )

    print(f"initialized {discovery}")
    print(f"queries: {queries_path}")
    print(f"iterations: {iterations}")


if __name__ == "__main__":
    main()
