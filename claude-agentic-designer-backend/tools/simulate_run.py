#!/usr/bin/env python3
"""simulate_run.py — Emit a realistic, verbose event stream end-to-end.

Use this to demo / smoke-test the companion UI without running the full Claude
skill. It walks every agent through the Generate -> Reflect -> Evaluate loop with
two iterations, producing the kind of verbose thinking + tool-use logs the real
skill emits so each agent node lights up in sequence.

Usage:
  python tools/simulate_run.py [--run RUN_ID] [--doc-type slides] [--speed 0.25]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common.events import emit  # noqa: E402


def step(run: str, delay: float, *args, **kwargs):
    emit(run, *args, **kwargs)
    time.sleep(delay)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run", default=f"run-sim-{int(time.time())}")
    p.add_argument("--doc-type", default="slides",
                   choices=["slides", "one_pager", "white_paper"])
    p.add_argument("--speed", type=float, default=0.25)
    args = p.parse_args()
    run, d, doc = args.run, args.speed, args.doc_type

    step(run, d, "run_start", agent="orchestrator",
         message=f"Starting {doc} generation for 'Q3 Platform Strategy'",
         data={"doc_type": doc, "references": ["master-brand.pptx", "example-onepager.pptx"]})

    step(run, d, "agent_start", agent="orchestrator",
         message="Planning the job and selecting the rubric")
    step(run, d, "agent_thinking", agent="orchestrator", level="debug",
         message="Audience=executives; key message=consolidate to one platform; "
                 "budget=3 iterations; rubric=slides.rubric.v1")
    step(run, d, "agent_end", agent="orchestrator", message="Plan ready; routing to Design-System")

    step(run, d, "agent_start", agent="design_system",
         message="Grounding the run in the master deck")
    step(run, d, "tool_call", agent="design_system", message="extract_tokens",
         data={"master": "master-brand.pptx"})
    step(run, d, "tool_result", agent="design_system",
         message="Extracted 14 layouts, 12 theme colors, fonts: Optum Sans / Arial")
    step(run, d, "agent_thinking", agent="design_system", level="debug",
         message="Style fingerprint: navy+orange accents, generous whitespace, "
                 "1 idea/slide, layout #3='Section Header', #7='Stat Callout'")
    step(run, d, "agent_end", agent="design_system", message="Design contract ready")

    step(run, d, "agent_start", agent="content", message="Drafting narrative")
    step(run, d, "agent_thinking", agent="content", level="debug",
         message="Cut 2 of 6 proof points to respect density; lead with cost takeout stat")
    step(run, d, "agent_end", agent="content", message="Content map ready (6 sections)")

    step(run, d, "agent_start", agent="structure", message="Building slide skeleton")
    step(run, d, "agent_thinking", agent="structure", level="debug",
         message="Arc: title -> context -> problem -> solution -> proof -> ask -> closing")
    step(run, d, "agent_end", agent="structure", message="8-slide skeleton ordered")

    step(run, d, "agent_start", agent="layout", message="Mapping blocks to master layouts")
    for i, (block, lay) in enumerate([
        ("title", "Title Slide"), ("context", "Section Header"),
        ("problem", "Two Content"), ("solution", "Stat Callout"),
        ("proof", "Quote"), ("ask", "Closing"),
    ]):
        step(run, d * 0.6, "agent_thinking", agent="layout", level="debug",
             message=f"Block '{block}' -> layout '{lay}' (best placeholder fit)")
    step(run, d, "agent_end", agent="layout", message="Layout assignments complete")

    def build_eval(iteration: int, passed: bool, score: float):
        step(run, d, "agent_start", agent="builder",
             message=f"[iter {iteration}] Writing slide_plan.json and building .pptx")
        step(run, d, "tool_call", agent="builder", message="build_pptx",
             data={"doc_type": doc, "slides": 8})
        step(run, d, "artifact", agent="builder", message="Generated 8 slide(s)",
             data={"kind": "pptx", "out": "output.pptx"})
        step(run, d, "tool_call", agent="reflection", message="render_pptx")
        step(run, d, "tool_result", agent="reflection",
             message="Rendered 8 slide image(s)",
             data={"renders": [f"slide-{i}.png" for i in range(1, 9)]})
        step(run, d, "agent_start", agent="reflection", message="Self-critique on renders")
        if not passed:
            step(run, d, "agent_thinking", agent="reflection", level="warn",
                 message="Slide 4 over-dense (8 bullets); title not dominant on slide 2")
        else:
            step(run, d, "agent_thinking", agent="reflection", level="debug",
                 message="No structural defects; alignment and density look clean")
        step(run, d, "agent_end", agent="reflection", message="Reflection pass done")

        step(run, d, "agent_start", agent="evaluator", message="Independent rubric scoring")
        step(run, d, "tool_call", agent="evaluator", message="evaluate")
        step(run, d, "evaluation", agent="evaluator",
             level="info" if passed else "warn",
             message=f"Score {score:.2f} / threshold 0.80 — {'PASS' if passed else 'REVISE'}",
             data={"weighted_score": score, "threshold": 0.8, "passed": passed,
                   "hard_fail": not passed})
        step(run, d, "agent_end", agent="evaluator", message="Evaluation complete")

    build_eval(1, passed=False, score=0.71)
    step(run, d, "iteration", agent="orchestrator",
         message="Iteration 1 failed gate; feeding fixes back to Layout/Builder",
         data={"iteration": 2})
    step(run, d, "agent_thinking", agent="layout", level="debug",
         message="Split dense slide 4 into two; promote title size on slide 2")
    build_eval(2, passed=True, score=0.88)

    step(run, d, "artifact", agent="orchestrator", message="Final artifact ready",
         data={"kind": "pptx", "out": "output.pptx",
               "renders": [f"slide-{i}.png" for i in range(1, 9)]})
    step(run, d, "run_end", agent="orchestrator",
         message="Done. Score 0.88 after 2 iterations. On-brand; review slide 5 quote.",
         data={"status": "passed", "score": 0.88, "iterations": 2})
    print(f"Simulated run complete: {run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
