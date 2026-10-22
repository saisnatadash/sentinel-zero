"""SYNTHETIC drinking-water network: where does current evidence leave a blind spot?

Stages: source -> treatment plant -> storage tanks -> distribution points (each serves people).
Every number is invented for demonstration. The hidden contamination set is used only to
score planning strategies. It is never shown as a finding.
"""
import copy
import math
import random
from dataclasses import dataclass, field

TAU_DAYS = 3.0  # evidence loses most of its value after about a week


@dataclass
class Node:
    id: str
    kind: str
    name: str
    population: int
    last_test_days: float | None  # None = never tested
    last_result: str | None  # "ok", "fail" or None
    disrupted: bool = False
    recent_reports: int = 0
    test_cost: float = 1.0
    x: int = 0
    y: int = 0


@dataclass
class Network:
    nodes: dict
    edges: list  # (upstream, downstream)
    hidden_contaminated: set = field(default_factory=set)


def parents(net: Network, nid: str) -> list:
    return [u for u, v in net.edges if v == nid]


def children(net: Network, nid: str) -> list:
    return [v for u, v in net.edges if u == nid]


def ancestors(net: Network, nid: str) -> set:
    seen: set = set()
    stack = list(parents(net, nid))
    while stack:
        u = stack.pop()
        if u not in seen:
            seen.add(u)
            stack.extend(parents(net, u))
    return seen


def downstream_hops(net: Network, nid: str) -> dict:
    """Map each downstream node to the number of stages between it and nid."""
    hops: dict = {}
    seen = {nid}
    frontier = [nid]
    depth = 0
    while frontier:
        depth += 1
        nxt = []
        for u in frontier:
            for v in children(net, u):
                if v not in seen:
                    seen.add(v)
                    hops[v] = depth
                    nxt.append(v)
        frontier = nxt
    return hops


def uncertainty(node: Node) -> float:
    if node.last_test_days is None:
        return 1.0
    if node.last_result == "fail":
        return 0.2  # a failed test is already evidence, though it still needs confirming
    return round(1 - math.exp(-node.last_test_days / TAU_DAYS), 3)


def hazard(node: Node) -> float:
    h = 0.2
    if node.disrupted:
        h += 0.4
    h += min(0.3, 0.05 * node.recent_reports)
    if node.last_result == "fail":
        h += 0.5
    return min(1.0, round(h, 3))


def exposure(net: Network, nid: str) -> float:
    values = [0.6 * hazard(net.nodes[u]) for u in ancestors(net, nid) if net.nodes[u].disrupted]
    return round(max(values), 3) if values else 0.0


def risk(net: Network, nid: str) -> float:
    return round(max(hazard(net.nodes[nid]), exposure(net, nid)), 3)


def pop_weight(net: Network, nid: str) -> float:
    biggest = max(n.population for n in net.nodes.values())
    return round(math.log1p(net.nodes[nid].population) / math.log1p(biggest), 3)


def value(net: Network, nid: str) -> float:
    node = net.nodes[nid]
    return risk(net, nid) * uncertainty(node) * pop_weight(net, nid) / node.test_cost


def reasons(net: Network, nid: str) -> list:
    node = net.nodes[nid]
    out = []
    if node.disrupted:
        out.append("supply interrupted")
    if exposure(net, nid) > hazard(node):
        out.append("downstream of a disrupted stage")
    if node.recent_reports >= 3:
        out.append(f"{node.recent_reports} recent community reports")
    if node.last_result == "fail":
        out.append("last test failed")
    if node.last_test_days is None:
        out.append("never tested")
    elif node.last_test_days >= 7:
        out.append(f"last tested {int(node.last_test_days)} days ago")
    return out or ["no strong signal"]


def failure_path(net: Network, nid: str) -> list:
    """If this stage fails, which downstream places are affected, and how many stages away?"""
    rows = [
        {"id": v, "name": net.nodes[v].name, "stages_away": hops, "population": net.nodes[v].population}
        for v, hops in downstream_hops(net, nid).items()
    ]
    return sorted(rows, key=lambda r: (r["stages_away"], r["id"]))


def invisible_risks(net: Network) -> list:
    """Places where the risk is meaningful but the latest evidence is stale, missing or weak."""
    rows = []
    for nid, node in net.nodes.items():
        r, u = risk(net, nid), uncertainty(node)
        if r >= 0.3 and u >= 0.5:
            rows.append({"id": nid, "name": node.name, "risk": r, "uncertainty": u,
                         "population": node.population, "reasons": reasons(net, nid)})
    return sorted(rows, key=lambda x: x["risk"] * x["uncertainty"] * x["population"], reverse=True)


def next_best_tests(net: Network, budget: float) -> list:
    """Greedy plan: repeatedly test the place that most reduces risk-weighted uncertainty per cost.

    Planning works on a copy. After each pick, that place is treated as freshly tested, so it
    is not chosen twice. Test results are not assumed.
    """
    working = copy.deepcopy(net)
    spent = 0.0
    picks = []
    while True:
        options = [
            (value(working, nid), nid) for nid, node in working.nodes.items()
            if node.last_test_days != 0.0 and spent + node.test_cost <= budget and value(working, nid) > 0
        ]
        if not options:
            break
        best_value, nid = max(options)
        node = working.nodes[nid]
        spent += node.test_cost
        picks.append({"id": nid, "name": node.name, "value": round(best_value, 3),
                      "population": node.population, "cost": node.test_cost,
                      "reasons": reasons(net, nid)})
        node.last_test_days = 0.0
    return picks


def _recall(net: Network, picked_ids: list) -> float:
    truth = net.hidden_contaminated
    if not truth:
        return 0.0
    return round(len(set(picked_ids) & truth) / len(truth), 3)


def oldest_first(net: Network, budget: float) -> list:
    order = sorted(net.nodes.values(),
                   key=lambda n: (n.last_test_days is not None, -(n.last_test_days or 0)))
    picked, spent = [], 0.0
    for node in order:
        if spent + node.test_cost <= budget:
            picked.append(node.id)
            spent += node.test_cost
    return picked


def random_average(net: Network, budget: float, trials: int = 500, seed: int = 42) -> float:
    rng = random.Random(seed)
    ids = list(net.nodes)
    slots = int(budget)
    total = 0.0
    for _ in range(trials):
        total += _recall(net, rng.sample(ids, min(slots, len(ids))))
    return round(total / trials, 3)


def compare_strategies(net: Network, budget: float) -> list:
    sentinel = [p["id"] for p in next_best_tests(net, budget)]
    return [
        {"strategy": "Sentinel Zero (risk × uncertainty × population ÷ cost)",
         "contaminated_places_found": _recall(net, sentinel)},
        {"strategy": "Test the oldest measurement first",
         "contaminated_places_found": _recall(net, oldest_first(net, budget))},
        {"strategy": "Random places (average of 500 runs)",
         "contaminated_places_found": random_average(net, budget)},
    ]


def build_network() -> Network:
    nodes = {}

    def add(nid, kind, name, pop, age, result, disrupted=False, reports=0, x=0, y=0):
        nodes[nid] = Node(id=nid, kind=kind, name=name, population=pop, last_test_days=age,
                          last_result=result, disrupted=disrupted, recent_reports=reports, x=x, y=y)

    add("source", "source", "River intake", 9000, 3, "ok", x=60, y=200)
    add("plant", "plant", "Treatment plant", 9000, 3, "ok", x=200, y=200)
    add("tank_A", "tank", "Storage tank A", 2000, None, None, disrupted=True, x=350, y=90)
    add("tank_B", "tank", "Storage tank B", 7000, 2, "ok", x=350, y=310)
    add("dist_1", "distribution", "Lanes 1–3", 800, 2, "ok", reports=6, x=530, y=35)
    add("dist_2", "distribution", "Lanes 4–6", 1200, 9, "ok", reports=5, x=530, y=135)
    add("dist_3", "distribution", "Lanes 7–9", 1000, 1, "ok", x=530, y=265)
    add("dist_4", "distribution", "Lanes 10–12", 1500, 20, "ok", x=530, y=365)

    edges = [("source", "plant"), ("plant", "tank_A"), ("plant", "tank_B"),
             ("tank_A", "dist_1"), ("tank_A", "dist_2"),
             ("tank_B", "dist_3"), ("tank_B", "dist_4")]
    return Network(nodes=nodes, edges=edges, hidden_contaminated={"tank_A", "dist_1", "dist_2"})
