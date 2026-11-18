"""Ligne de commande d'expérimentation : lance le moteur sur un graphe exporté (JSON) et trace les résultats.

Usage (depuis backend/) : python -m experiments.cli --json graphe.json --shape heart --distance 15000"""
import argparse
import json

from experiments.plotting import plot_results, plot_split_text_global, plot_split_text_results
from runtodraw.road_graph import RoadGraph
from runtodraw.search import evaluate_method
from runtodraw.shapes import get_base_shape
from runtodraw.text_routes import split_text_itineraries_full_distance


def ask_distance_if_missing(distance_m):
    if distance_m is not None:
        return float(distance_m)
    while True:
        raw = input("Distance souhaitée en mètres ? ").strip()
        try:
            value = float(raw)
            if value > 0:
                return value
        except ValueError:
            pass
        print("Entre un nombre valide, par exemple 15000")


def print_summary(results):
    print("\n===== Summary =====")
    for method_name, variants in results.items():
        print(f"\n[{method_name.upper()}]")
        for variant_name in ["closest_to_distance", "best_compromise"]:
            m = variants[variant_name]["metrics"]
            print(
                f"{variant_name:20s} | route={m['length_route']:8.1f} m | "
                f"gap={m['length_gap']:7.1f} | over={m['over_max']:7.1f} | "
                f"shape={m['shape_error']:7.1f} | turn={m['turn_penalty']:7.1f} | "
                f"angle={m['angle_deg']:6.1f}"
            )


def print_split_summary(split_results):
    print("\n===== Split text summary =====")
    for i, item in enumerate(split_results, start=1):
        m = item["metrics"]
        print(
            f"{i:02d} - {item['letter']} | route={m['length_route']:8.1f} m | "
            f"target={m['length_target']:8.1f} m | "
            f"gap={m['length_gap']:7.1f} | over={m['over_max']:7.1f} | "
            f"shape={m['shape_error']:7.1f} | turn={m['turn_penalty']:7.1f} | "
            f"angle={m['angle_deg']:6.1f}"
        )


# Fonction principale d’expérimentation.
# Elle charge un graphe depuis un JSON, lance soit une recherche de forme,
# soit une recherche de texte, affiche les résultats, puis imprime un résumé.
def run_experiment(json_path, shape_name="heart", text="P2I", distance_m=None, tolerance_ratio=0.10, text_mode="whole"):
    desired_distance_m = ask_distance_if_missing(distance_m)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph = RoadGraph(data)

    if shape_name == "text" and text_mode in {"split", "both"}:
        split_results = split_text_itineraries_full_distance(
            graph,
            text,
            desired_distance_m,
            tolerance_ratio,
        )
        plot_split_text_results(graph, split_results, desired_distance_m, tolerance_ratio, text)
        plot_split_text_global(graph, split_results, text)
        print_split_summary(split_results)

        if text_mode == "split":
            return split_results

    base_points = get_base_shape(shape_name, text)
    results = {
        "projection": evaluate_method(graph, base_points, desired_distance_m, tolerance_ratio, shape_name, "projection"),
        "translation": evaluate_method(graph, base_points, desired_distance_m, tolerance_ratio, shape_name, "translation"),
    }

    title = f"RunToDraw V16 - {shape_name}"
    if shape_name == "text":
        title += f" - {text.upper()}"

    plot_results(graph, results, desired_distance_m, tolerance_ratio, title)
    print_summary(results)
    return results


# Point d’entrée en ligne de commande.
# Cela permet d’utiliser ce fichier comme script d’expérimentation autonome.
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="Chemin vers le JSON du graphe")
    parser.add_argument("--shape", default="heart", choices=["square", "circle", "heart", "star", "infinity", "text"])
    parser.add_argument("--text", default="P2I", help="Texte à dessiner en MAJUSCULES si --shape text")
    parser.add_argument("--distance", type=float, default=None, help="Distance souhaitée en mètres")
    parser.add_argument("--tolerance", type=float, default=0.10, help="Tolérance relative au-dessus de la distance, ex: 0.10 pour +10%%")
    parser.add_argument("--text-mode", default="split", choices=["whole", "split", "both"], help="Pour --shape text: mot complet, lettres séparées, ou les deux")
    args = parser.parse_args()

    run_experiment(
        args.json,
        shape_name=args.shape,
        text=args.text,
        distance_m=args.distance,
        tolerance_ratio=args.tolerance,
        text_mode=args.text_mode,
    )
