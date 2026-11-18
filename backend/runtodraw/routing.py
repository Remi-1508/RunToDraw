"""Routage d'une forme sur le réseau : échantillonnage, accroche aux nœuds les plus proches, plus courts chemins,
suppression des boucles courtes et des allers-retours."""
import math

import numpy as np

from runtodraw.geometry import polyline_length, resample_polyline, simplify_path_points


def simplify_consecutive_duplicates(seq):
    out = []
    for x in seq:
        if not out or out[-1] != x:
            out.append(x)
    return out


# EN: Removes short loops from a node path. When the path comes back to a node it already visited
# after less than `max_loop_m`, the detour in between is cut. This removes the back-and-forth "comb
# teeth" created when a shape point snaps to a node in a side street (go there, come back).
# Long loops are kept: they are part of the drawing (e.g. the crossing of the infinity sign).
# Intended back-and-forths are kept too: some drawings retrace their own strokes (the bars of an
# E, the stem of a T, the tips of a star). `protected[i]` marks the path nodes where the drawing
# itself turns around; a loop that contains such a node is never cut. Without this, the removal
# ate a retraced stroke step by step (each nested loop became short once the inner one was cut).
# Linear time: each node is pushed and popped at most once.
# FR: Supprime les boucles courtes d'un chemin de nœuds. Quand le chemin revient sur un nœud déjà visité
# après moins de `max_loop_m`, le détour entre les deux est coupé. Cela supprime les « dents de peigne »
# créées quand un point de la forme s'accroche à un nœud dans une rue latérale (on y va, on revient).
# Les grandes boucles sont gardées : elles font partie du dessin (ex. le croisement du signe infini).
# Les allers-retours voulus sont gardés aussi : certains dessins repassent sur leurs propres traits
# (les barres d'un E, la hampe d'un T, les pointes d'une étoile). `protected[i]` marque les nœuds du
# chemin où le dessin lui-même fait demi-tour ; une boucle qui en contient un n'est jamais coupée.
# Sans cela, la suppression « mangeait » un trait parcouru en aller-retour de proche en proche (chaque
# boucle englobante devenait courte une fois la boucle intérieure coupée).
# Temps linéaire : chaque nœud est ajouté et retiré au plus une fois.
def remove_short_loops(path_idx, node_array, max_loop_m, protected=None):
    out, cum, n_prot, last_pos = [], [], [], {}
    for k, v in enumerate(path_idx):
        is_prot = bool(protected[k]) if protected is not None else False
        if out:
            dx, dy = node_array[v] - node_array[out[-1]]
            d = cum[-1] + math.hypot(dx, dy)
            prot_count = n_prot[-1] + is_prot
        else:
            d = 0.0
            prot_count = int(is_prot)
        p = last_pos.get(v)
        loop_is_drawing = p is not None and prot_count - n_prot[p] > 0
        if p is not None and d - cum[p] <= max_loop_m and not loop_is_drawing:
            for w in out[p + 1:]:
                if last_pos.get(w, -1) > p:
                    del last_pos[w]
            del out[p + 1:]
            del cum[p + 1:]
            del n_prot[p + 1:]
            continue
        last_pos[v] = len(out)
        out.append(v)
        cum.append(d)
        n_prot.append(prot_count)
    return out


# EN: Loops shorter than this many sampling steps are considered back-and-forth noise.
# FR: Les boucles plus courtes que ce nombre de pas d'échantillonnage sont considérées comme des allers-retours parasites.
LOOP_REMOVAL_STEPS = 3.0

# EN: A sample where the drawing turns by more than this angle is a deliberate U-turn.
# FR: Un point où le dessin tourne de plus de cet angle est un demi-tour voulu.
REVERSAL_ANGLE_DEG = 120.0


def reversal_samples(points, min_turn_deg=REVERSAL_ANGLE_DEG):
    """Booléens : le dessin fait-il demi-tour en chaque point échantillonné ?

    Les directions sont comparées sur deux pas (k-2 -> k et k -> k+2) : si le bout d'un trait tombe
    entre deux échantillons, ceux-ci peuvent se superposer et masquer le demi-tour sur un seul pas.
    Les voisins immédiats sont aussi marqués, pour couvrir le nœud réellement atteint au bout du trait.
    """
    pts = np.asarray(points, dtype=float)
    n = len(pts)
    flags = np.zeros(n, dtype=bool)
    if n < 5:
        return flags
    a = pts[2:-2] - pts[:-4]
    b = pts[4:] - pts[2:-2]
    na = np.hypot(a[:, 0], a[:, 1])
    nb = np.hypot(b[:, 0], b[:, 1])
    ok = (na > 1e-9) & (nb > 1e-9)
    cosang = np.ones(len(a))
    cosang[ok] = np.einsum("ij,ij->i", a[ok], b[ok]) / (na[ok] * nb[ok])
    core = np.zeros(n, dtype=bool)
    core[2:-2] = np.degrees(np.arccos(np.clip(cosang, -1.0, 1.0))) > min_turn_deg
    flags = core.copy()
    flags[1:] |= core[:-1]
    flags[:-1] |= core[1:]
    return flags


def route_from_target(graph, target_points, sample_count=60, pinned=None):
    """`pinned` : {indice d'échantillon: indice de nœud} pour imposer le passage par un nœud précis
    (le point de départ de l'utilisateur). Un nœud imposé n'est jamais retiré par la suppression
    des allers-retours."""
    target_rs = resample_polyline(target_points, n_samples=sample_count)

    # EN: All sampled points are snapped in one vectorized KD-tree query.
    # FR: Tous les points échantillonnés sont accrochés en une seule requête KD-tree vectorisée.
    snapped_idx, snap_dists = graph.nearest_indices(target_rs)

    # Points consécutifs accrochés au même nœud : fusionnés, en gardant l'information « demi-tour ».
    turning = reversal_samples(target_rs)
    if pinned:
        snapped_idx = snapped_idx.copy()
        for sample, node in pinned.items():
            snapped_idx[sample] = node
            turning[sample] = True
    snapped, snapped_turn = [], []
    for node, turn in zip(snapped_idx.tolist(), turning.tolist()):
        if snapped and snapped[-1] == node:
            snapped_turn[-1] = snapped_turn[-1] or turn
        else:
            snapped.append(node)
            snapped_turn.append(turn)

    path_idx = []
    path_protected = []
    total_cost = 0.0
    unreachable = 0

    for i, (a, b) in enumerate(zip(snapped[:-1], snapped[1:])):
        sp, cost = graph.shortest_path_idx(a, b)
        if sp is None:
            unreachable += 1
            continue
        if not path_idx:
            path_idx.extend(sp)
            path_protected.extend([snapped_turn[i]] + [False] * (len(sp) - 1))
        else:
            path_idx.extend(sp[1:])
            path_protected.extend([False] * (len(sp) - 1))
        path_protected[-1] = snapped_turn[i + 1]
        total_cost += cost

    sampling_step = polyline_length(target_points) / max(sample_count - 1, 1)
    path_idx = remove_short_loops(path_idx, graph.node_array, LOOP_REMOVAL_STEPS * sampling_step,
                                  protected=path_protected)

    if path_idx:
        path_points = graph.node_array[path_idx]
        route_points = simplify_path_points(path_points, angle_tol_deg=6.0)
    else:
        path_points = route_points = np.empty((0, 2), dtype=float)

    full_path = [graph.node_ids[i] for i in path_idx]
    extra = {
        "snap_mean": float(np.mean(snap_dists)) if len(snap_dists) else float("inf"),
        "shortest_path_cost": total_cost,
        "unreachable_segments": unreachable,
        "n_route_nodes": len(full_path),
        # EN: real length of the path on the roads (the simplified polyline cuts corners).
        # FR: vraie longueur du trajet sur les routes (la polyligne simplifiée coupe les virages).
        "path_length_m": polyline_length(path_points),
    }
    return full_path, route_points, extra
