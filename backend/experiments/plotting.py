"""Tracés matplotlib pour l'expérimentation et le débogage (hors API)."""
import math

import numpy as np


# EN: matplotlib is only needed for the experiment plots (command line), not by the API.
# Importing it lazily keeps the backend lighter and faster to start.
# FR: matplotlib ne sert qu'aux tracés d'expérimentation (ligne de commande), pas à l'API.
# On l'importe à la demande pour alléger le backend et accélérer son démarrage.
def _plt():
    import matplotlib.pyplot as plt
    return plt


def draw_graph(ax, graph, max_edges=3500):
    count = 0
    seen = set()

    for e in graph.edges:
        u = e["from"]
        v = e["to"]
        key = tuple(sorted((u, v)))
        if key in seen:
            continue
        seen.add(key)

        pu = graph.node_xy.get(u)
        pv = graph.node_xy.get(v)
        if pu is None or pv is None:
            continue

        ax.plot([pu[0], pv[0]], [pu[1], pv[1]], linewidth=0.35, alpha=0.25)
        count += 1
        if count >= max_edges:
            break


def annotate_metrics(ax, metrics, desired_distance_m, tolerance_ratio):
    max_allowed = desired_distance_m * (1.0 + tolerance_ratio)
    txt = (
        f"route = {metrics.get('length_route', 0.0):.0f} m\n"
        f"target = {metrics.get('length_target', 0.0):.0f} m\n"
        f"gap = {metrics.get('length_gap', 0.0):.0f} m\n"
        f"max = {max_allowed:.0f} m\n"
        f"over = {metrics.get('over_max', 0.0):.0f} m\n"
        f"shape = {metrics.get('shape_error', 0.0):.1f}\n"
        f"turn = {metrics.get('turn_penalty', 0.0):.1f}\n"
        f"angle = {metrics.get('angle_deg', 0.0):.1f}°"
    )
    ax.text(0.02, 0.02, txt, transform=ax.transAxes, fontsize=8, bbox=dict(boxstyle="round", alpha=0.85))


def variant_title(method_name, variant_name):
    left = "Projection" if method_name == "projection" else "Translation"
    right = "Distance la plus proche" if variant_name == "closest_to_distance" else "Meilleur compromis"
    return f"{left} - {right}"


def set_local_view(ax, target, route):
    pts = []
    if len(target) > 0:
        pts.append(target)
    if len(route) > 0:
        pts.append(route)
    if pts:
        all_pts = np.vstack(pts)
        xmin, ymin = np.min(all_pts, axis=0)
        xmax, ymax = np.max(all_pts, axis=0)
        pad = max(xmax - xmin, ymax - ymin) * 0.6 + 100.0
        cx = 0.5 * (xmin + xmax)
        cy = 0.5 * (ymin + ymax)
        ax.set_xlim(cx - pad, cx + pad)
        ax.set_ylim(cy - pad, cy + pad)


def plot_results(graph, results, desired_distance_m, tolerance_ratio, title):
    plt = _plt()
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    axes = axes.ravel()

    order = [
        ("projection", "closest_to_distance"),
        ("projection", "best_compromise"),
        ("translation", "closest_to_distance"),
        ("translation", "best_compromise"),
    ]

    for ax, (method_name, variant_name) in zip(axes, order):
        block = results[method_name][variant_name]
        target = block["target"]
        route = block["route_points"]

        draw_graph(ax, graph)

        if len(target) > 0:
            ax.plot(target[:, 0], target[:, 1], "--", linewidth=2, label="cible")
        if len(route) > 0:
            ax.plot(route[:, 0], route[:, 1], linewidth=2.2, label="trajet")

        ax.set_title(variant_title(method_name, variant_name))
        ax.set_aspect("equal")
        ax.legend()
        annotate_metrics(ax, block["metrics"], desired_distance_m, tolerance_ratio)
        set_local_view(ax, target, route)

    fig.suptitle(title)
    plt.tight_layout()
    plt.show()


def plot_split_text_results(graph, split_results, per_letter_distance_m, tolerance_ratio, text):
    n = len(split_results)
    cols = 2 if n > 1 else 1
    rows = math.ceil(n / cols)

    plt = _plt()
    fig, axes = plt.subplots(rows, cols, figsize=(8 * cols, 5 * rows))
    axes = np.array(axes).reshape(-1)

    for ax, item in zip(axes, split_results):
        draw_graph(ax, graph)

        target = item["target"]
        route = item["route_points"]

        ax.plot(target[:, 0], target[:, 1], "--", linewidth=2, label="cible")
        if len(route) > 0:
            ax.plot(route[:, 0], route[:, 1], linewidth=2.2, label="trajet")

        ax.set_title(f"Lettre {item['letter']} - cible ~ {per_letter_distance_m:.0f} m")
        ax.set_aspect("equal")
        ax.legend()
        annotate_metrics(ax, item["metrics"], per_letter_distance_m, tolerance_ratio)
        set_local_view(ax, target, route)

    for ax in axes[len(split_results):]:
        ax.axis("off")

    fig.suptitle(f"RunToDraw V16 - texte séparé : {text.upper()} ({n} itinéraires)")
    plt.tight_layout()
    plt.show()


def plot_split_text_global(graph, split_results, text):
    plt = _plt()
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    draw_graph(ax, graph)

    first_target = True
    first_route = True

    for item in split_results:
        target = item["target"]
        route = item["route_points"]

        if len(target) > 0:
            ax.plot(
                target[:, 0],
                target[:, 1],
                "--",
                linewidth=2,
                label="cible" if first_target else None,
            )
            first_target = False

        if len(route) > 0:
            ax.plot(
                route[:, 0],
                route[:, 1],
                linewidth=2.2,
                label="trajet" if first_route else None,
            )
            first_route = False

    ax.set_title(f"RunToDraw V16 - mot global : {text.upper()}")
    ax.set_aspect("equal")
    ax.legend()

    pts = []
    for item in split_results:
        if len(item["target"]) > 0:
            pts.append(item["target"])
        if len(item["route_points"]) > 0:
            pts.append(item["route_points"])

    if pts:
        all_pts = np.vstack(pts)
        xmin, ymin = np.min(all_pts, axis=0)
        xmax, ymax = np.max(all_pts, axis=0)
        pad = max(xmax - xmin, ymax - ymin) * 0.8 + 120.0
        cx = 0.5 * (xmin + xmax)
        cy = 0.5 * (ymin + ymax)
        ax.set_xlim(cx - pad, cx + pad)
        ax.set_ylim(cy - pad, cy + pad)

    plt.tight_layout()
    plt.show()
