"""Baseline availability for the Case 01 scenarios using the organizers' geometry.py.

Usage: python tools/case01_baseline.py [scenario.json ...]
Computes, per client site: share of steps with a visible satellite, share of steps
with an end-to-end path to a gateway, the longest gap, mean hop count, and the
reason for each no-path step (no visible satellite / ISL disconnected / no gateway
contact). Routing is a plain BFS over the organizers' snapshot edges (min hops).
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cases" / "case01" / "calc"))
import geometry as g  # noqa: E402


def analyze(path):
    s = g.load(path)
    e = s["environment"]
    clients = [x["id"] for x in s["ground_sites"] if x["role"] == "client"]
    gws = [x["id"] for x in s["ground_sites"] if x["role"] == "gateway"]
    steps = range(0, e["horizon_s"], e["step_s"])
    stats = {c: dict(vis=0, path=0, gaps=[], hops=[]) for c in clients}
    reasons = {c: collections.Counter() for c in clients}
    for t in steps:
        snap = g.snapshot(s, t)
        adj = collections.defaultdict(set)
        for a, b, _ in snap["edges"]:
            adj[a].add(b)
            adj[b].add(a)
        active = {x["id"] for x in snap["satellites"] if x["active"]}
        for c in clients:
            vis = len(adj[c]) > 0
            stats[c]["vis"] += vis
            found = None
            if vis:
                prev = {c: None}
                q = collections.deque([c])
                while q and not found:
                    u = q.popleft()
                    for v in adj[u]:
                        if v in prev:
                            continue
                        if v in gws and u != c:
                            prev[v] = u
                            found = v
                            break
                        if v in active:
                            prev[v] = u
                            q.append(v)
            if found:
                stats[c]["path"] += 1
                n, x = 0, found
                while x is not None:
                    n += 1
                    x = prev[x]
                stats[c]["hops"].append(n - 1)
                stats[c]["gaps"].append(0)
            else:
                stats[c]["gaps"].append(1)
                if not vis:
                    reasons[c]["no_visible_sat"] += 1
                elif not any(adj[gw] for gw in gws):
                    reasons[c]["gateway_no_contact"] += 1
                else:
                    reasons[c]["isl_disconnected"] += 1
    n = len(steps)
    print("==", s["meta"]["title"], f"({path})")
    for c in clients:
        mx = cur = 0
        for v in stats[c]["gaps"]:
            cur = cur + 1 if v else 0
            mx = max(mx, cur)
        h = stats[c]["hops"]
        print(
            f"  {c}: visible {stats[c]['vis']/n:.1%}  path {stats[c]['path']/n:.1%}  "
            f"max gap {mx*e['step_s']/60:.0f} min  hops avg {sum(h)/len(h) if h else 0:.1f}  "
            f"no-path reasons {dict(reasons[c])}"
        )


if __name__ == "__main__":
    files = sys.argv[1:] or sorted(
        str(p) for p in (Path(__file__).resolve().parents[1] / "cases" / "case01" / "data").glob("*.json")
    )
    for f in files:
        analyze(f)
