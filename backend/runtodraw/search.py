"""Recherche du meilleur itinéraire : génération des candidats (position, taille, angle), calibrage de la taille
sur la distance demandée, méthodes « projection », « translation » et « départ inclus »."""
import numpy as np

from runtodraw.geometry import fit_points, fold_angle, is_closed, point_at_fraction, polyline_length, resample_polyline, rotate_closed_outline, rotate_points
from runtodraw.road_graph import dominant_graph_angle
from runtodraw.routing import route_from_target
from runtodraw.scoring import score_solution
from runtodraw.validation import SHAPES


# Construit plusieurs tailles candidates autour de la taille nominale demandée.
def estimate_size_candidates(base_points, desired_distance_m, shape_name):
    base_len = max(polyline_length(base_points), 1e-9)
    base_size = desired_distance_m / max(base_len, 1e-9)

    if shape_name == "text":
        factors = [0.45, 0.60, 0.75, 0.90, 1.05]
    elif shape_name == "custom" or shape_name in SHAPES:
        factors = [0.65, 0.80, 0.95, 1.10]
    else:
        factors = [0.75, 0.90, 1.00, 1.10]

    return [max(80.0, base_size * f) for f in factors]


# Construit un candidat transformé à partir d’une forme de base :
# taille + rotation + translation.
def make_candidate_points(base_points, center, size_m, angle_deg):
    pts = fit_points(base_points, np.array([0.0, 0.0], dtype=float), size_m)
    pts = rotate_points(pts, angle_deg)
    pts[:, 0] += center[0]
    pts[:, 1] += center[1]
    return pts


# Génère tous les candidats de recherche pour une forme :
# centres possibles, angles et tailles.
# Le mode translation explore quelques centres décalés, alors que le mode projection
# n’utilise que le centre du graphe.
# Cadre de recherche : le point choisi par l'utilisateur (origine du repère local x/y) et un carré
# de côté égal à la distance demandée. Avant, ce cadre était la boîte englobante du graphe téléchargé
# (rayon = distance / 2), c'est-à-dire le même carré. Le définir explicitement permet que les
# candidats ne dépendent plus de la quantité de réseau routier téléchargée.
def search_frame(desired_distance_m):
    return np.zeros(2, dtype=float), float(desired_distance_m)


# Centres et tailles testés pour une forme (les angles sont ajoutés à part, ils dépendent du graphe).
def shape_layout(base_points, desired_distance_m, shape_name, use_translation):
    center, span = search_frame(desired_distance_m)
    step = 0.12 * span

    if shape_name == "text":
        step *= 0.95

    if use_translation:
        centers = [
            center,
            center + np.array([ step, 0.0]),
            center + np.array([-step, 0.0]),
            center + np.array([0.0,  step]),
            center + np.array([0.0, -step]),
        ]
    else:
        centers = [center]

    sizes = estimate_size_candidates(base_points, desired_distance_m, shape_name)
    return centers, sizes


# Recherche d'orientation.
# Les formes sont testées dans toutes les orientations, pour trouver le meilleur résultat là où les rues
# le permettent. Pour ne pas refaire des calculs identiques, chaque forme n'est tournée que sur sa période
# de symétrie (une étoile est identique tous les 72°, le signe infini tous les 180°, un carré tous les 90°),
# avec un pas angulaire fin. Le balayage part de l'axe dominant des rues : l'orientation alignée sur les
# rues fait donc toujours partie des angles testés.
# Exception : le texte. Un mot à l'envers est illisible, il reste donc à ±15° de l'horizontale.
ORIENTATION_RULES = {
    # forme      : (période de symétrie °, pas angulaire °)
    "square":   (90.0, 10.0),
    "circle":   (360.0, 90.0),    # toutes les orientations se valent : quelques angles suffisent
    "heart":    (360.0, 10.0),
    "star":     (72.0, 8.0),
    "infinity": (180.0, 10.0),
    "triangle": (120.0, 10.0),
    "diamond":  (180.0, 10.0),
    "custom":   (360.0, 15.0),     # dessin libre : aucune symétrie connue, pas plus gros pour limiter le calcul
}
TEXT_MAX_TILT_DEG = 15.0

# Formes qui ont un « haut » reconnaissable (l'éclair) : comme le texte, on ne les incline que de quelques
# degrés autour de l'horizontale (écart maximal, en degrés). Les autres formes restent testées dans toutes
# les orientations.
MAX_TILT_DEG = {"lightning": 25.0}
TILT_STEP_DEG = 12.5


def tilt_angles(max_tilt_deg):
    count = int(round(2 * max_tilt_deg / TILT_STEP_DEG)) + 1
    return [float(a) for a in np.linspace(-max_tilt_deg, max_tilt_deg, count)]


def search_angles(graph, shape_name):
    if shape_name == "text":
        return [float(a) for a in np.linspace(-TEXT_MAX_TILT_DEG, TEXT_MAX_TILT_DEG, 5)]

    if shape_name in MAX_TILT_DEG:
        return tilt_angles(MAX_TILT_DEG[shape_name])

    period, step = ORIENTATION_RULES.get(shape_name, (360.0, 10.0))
    street = fold_angle(dominant_graph_angle(graph), period)
    count = int(round(period / step))
    return [street + k * period / count for k in range(count)]


# Construit le trajet d'un candidat (forme à un centre, une taille et un angle donnés) et l'évalue.
def evaluate_candidate(graph, base_points, center, size_m, angle_deg, desired_distance_m, max_allowed_m, sample_count):
    target = make_candidate_points(base_points, center, size_m, angle_deg)
    node_path, route_points, extra = route_from_target(graph, target, sample_count=sample_count)
    anchor_idx = extra.pop("anchor_idx")

    metrics = score_solution(route_points, target, desired_distance_m, max_allowed_m,
                             route_length_m=extra["path_length_m"])
    metrics.update(extra)
    metrics["length_target_request"] = float(desired_distance_m)
    # Tolérance symétrique : trop court est aussi un écart (ex. ±10 % -> entre 13,5 et 16,5 km pour 15 km).
    min_allowed_m = 2.0 * desired_distance_m - max_allowed_m
    metrics["under_min"] = max(0.0, min_allowed_m - metrics["length_route"])
    metrics["angle_deg"] = float(angle_deg)
    metrics["size_m"] = float(size_m)
    metrics["center_x"] = float(center[0])
    metrics["center_y"] = float(center[1])

    return {
        "target": target,
        "node_path": node_path,
        "anchor_idx": anchor_idx,
        "route_points": route_points,
        "metrics": metrics,
    }


# Calibrage de la taille.
# Le trajet sur les vraies routes est toujours plus long que le dessin idéal (les rues ne suivent pas
# exactement la courbe), et l'écart dépend du lieu. Au lieu de tester quelques tailles fixes, chaque
# couple (centre, angle) ajuste la taille jusqu'à ce que la longueur du trajet corresponde à la distance
# demandée : taille <- taille * demandée / mesurée. La longueur grandit à peu près proportionnellement
# à la taille : 2 ou 3 étapes suffisent en général. Le rapport taille/longueur appris sur un couple sert
# de point de départ au suivant. Les tailles restent dans [min_size, max_size] pour que la forme tienne
# toujours dans la zone téléchargée (voir required_radius_m).
# Toutes les tailles évaluées sont gardées : le choix du « meilleur compromis » peut les utiliser.
CALIBRATION_MAX_STEPS = 4
CALIBRATION_TOLERANCE = 0.03   # on s'arrête à ±3 % de la distance demandée
EXPECTED_DETOUR = 1.5          # estimation initiale : trajet ≈ 1,5 × longueur du dessin


def _calibrate(evaluate_at, start_size, desired_distance_m, min_size, max_size):
    """Ajuste la taille d'un candidat jusqu'à la distance demandée. `evaluate_at(size)` route et
    évalue le candidat à cette taille. Renvoie (candidats évalués, dernier rapport taille/longueur)."""
    evaluated = []
    size_per_meter = None
    size = start_size
    for _ in range(CALIBRATION_MAX_STEPS):
        size = float(np.clip(size, min_size, max_size))
        cand = evaluate_at(size)
        evaluated.append(cand)
        length = cand["metrics"]["length_route"]
        if length <= 0:
            break
        size_per_meter = size / length
        if abs(length - desired_distance_m) <= CALIBRATION_TOLERANCE * desired_distance_m:
            break
        next_size = float(np.clip(size * float(np.clip(desired_distance_m / length, 0.6, 1.5)),
                                  min_size, max_size))
        if abs(next_size - size) < 1e-6:
            break  # bloqué sur une borne : inutile d'insister
        size = next_size
    return evaluated, size_per_meter


def calibrated_search(graph, base_points, centers, angles, desired_distance_m, max_allowed_m,
                      sample_count, min_size, max_size):
    nominal = desired_distance_m / max(polyline_length(base_points), 1e-9)
    size_per_meter = None
    evaluated = []

    for center in centers:
        for angle in angles:
            start = nominal / EXPECTED_DETOUR if size_per_meter is None else desired_distance_m * size_per_meter
            found, ratio = _calibrate(
                lambda size: evaluate_candidate(graph, base_points, center, size, angle,
                                                desired_distance_m, max_allowed_m, sample_count),
                start, desired_distance_m, min_size, max_size,
            )
            evaluated.extend(found)
            size_per_meter = ratio if ratio is not None else size_per_meter
    return evaluated


# Méthode « départ inclus ».
# L'utilisateur peut vouloir partir (et, pour une forme fermée, revenir) exactement au point choisi.
# Au lieu de centrer le dessin sur ce point, on le déplace pour que le point soit SUR son contour,
# à n'importe quelle position (la pointe du cœur n'a rien de particulier) : pour chaque position
# d'ancrage le long du contour et chaque angle, la forme est translatée pour que ce point du contour
# tombe sur le point de départ, et le trajet est forcé à passer par le nœud de départ. Pour une forme
# fermée, le contour est aussi « tourné » pour commencer à l'ancrage : la boucle part et revient au
# point de l'utilisateur. Chaque couple (ancrage, angle) passe par le même calibrage de taille.

START_ANCHORS = 12          # positions d'ancrage testées le long du contour
START_MIN_ANGLE_STEP = 30.0  # pas angulaire minimal (l'ancrage multiplie déjà les essais)


def start_angles(graph, shape_name):
    period, step = ORIENTATION_RULES.get(shape_name, (360.0, 10.0))
    if shape_name == "text" or shape_name in MAX_TILT_DEG:
        return search_angles(graph, shape_name)
    if shape_name == "circle":
        return [fold_angle(dominant_graph_angle(graph), period)]
    step = max(step, START_MIN_ANGLE_STEP)
    street = fold_angle(dominant_graph_angle(graph), period)
    count = max(1, int(round(period / step)))
    return [street + k * period / count for k in range(count)]


def _start_angles_near(angles, angle_hint):
    """Sans indication : tous les angles. Sinon, pour chaque meilleur angle de la projection, l'angle de départ
    le plus proche (modulo la période de la liste)."""
    if not angle_hint or len(angles) <= 3:
        return angles
    chosen = []
    for hint in angle_hint:
        nearest = min(angles, key=lambda a: abs((a - hint + 180.0) % 360.0 - 180.0))
        if nearest not in chosen:
            chosen.append(nearest)
    return chosen


def evaluate_anchored_candidate(graph, base_points, fraction, size_m, angle_deg, start_node,
                                desired_distance_m, max_allowed_m, sample_count):
    shape = make_candidate_points(base_points, np.zeros(2), size_m, angle_deg)
    if is_closed(shape):
        shape = rotate_closed_outline(shape, fraction)
        anchor = shape[0].copy()
        target = shape - anchor              # le point d'ancrage tombe sur l'origine = point de départ
        pinned = {0: start_node, sample_count - 1: start_node}
    else:
        anchor, _ = point_at_fraction(shape, fraction)
        target = shape - anchor
        # échantillon le plus proche de l'ancrage (le tracé passe par le départ en cours de route)
        rs = resample_polyline(target, n_samples=sample_count)
        pinned = {int(np.argmin(np.hypot(rs[:, 0], rs[:, 1]))): start_node}

    node_path, route_points, extra = route_from_target(graph, target, sample_count=sample_count, pinned=pinned)
    anchor_idx = extra.pop("anchor_idx")
    metrics = score_solution(route_points, target, desired_distance_m, max_allowed_m,
                             route_length_m=extra["path_length_m"])
    metrics.update(extra)
    metrics["length_target_request"] = float(desired_distance_m)
    min_allowed_m = 2.0 * desired_distance_m - max_allowed_m
    metrics["under_min"] = max(0.0, min_allowed_m - metrics["length_route"])
    metrics["angle_deg"] = float(angle_deg)
    metrics["size_m"] = float(size_m)
    metrics["anchor_fraction"] = float(fraction)
    center = -anchor
    metrics["center_x"], metrics["center_y"] = float(center[0]), float(center[1])
    return {"target": target, "node_path": node_path, "anchor_idx": anchor_idx, "route_points": route_points,
            "metrics": metrics, "start_node": graph.node_ids[start_node]}


def evaluate_start_method(graph, base_points, desired_distance_m, tolerance_ratio, shape_name, angle_hint=None):
    """Méthode « départ inclus » : mêmes sorties que evaluate_method. `angle_hint` : meilleurs angles de la projection ;
    on ne garde que les angles de départ qui en sont proches (à moins de la moitié d'un pas)."""
    max_allowed_m = desired_distance_m * (1.0 + tolerance_ratio)
    _, sizes = shape_layout(base_points, desired_distance_m, shape_name, use_translation=False)
    sample_count = 60 if shape_name == "text" else 72
    start_idx, _ = graph.nearest_indices(np.zeros((1, 2)))
    start_node = int(start_idx[0])

    closed = is_closed(base_points)
    fractions = [k / START_ANCHORS for k in range(START_ANCHORS)] if closed else \
        [k / (START_ANCHORS - 1) for k in range(START_ANCHORS)]
    nominal = desired_distance_m / max(polyline_length(base_points), 1e-9)

    evaluated, size_per_meter = [], None
    if len(search_angles(graph, shape_name)) < COARSE_MIN_ANGLES:
        angle_hint = None  # peu d'angles : tout est testé
    for angle in _start_angles_near(start_angles(graph, shape_name), angle_hint):
        for fraction in fractions:
            start = nominal / EXPECTED_DETOUR if size_per_meter is None else desired_distance_m * size_per_meter
            found, ratio = _calibrate(
                lambda size: evaluate_anchored_candidate(graph, base_points, fraction, size, angle, start_node,
                                                         desired_distance_m, max_allowed_m, sample_count),
                start, desired_distance_m, 80.0, max(sizes),
            )
            evaluated.extend(found)
            size_per_meter = ratio if ratio is not None else size_per_meter

    best_close, best_comp = pick_best(evaluated)
    return {"closest_to_distance": best_close, "best_compromise": best_comp,
            "all_candidates_count": len(evaluated)}


# Choisit les deux propositions parmi les candidats évalués :
# - « distance la plus proche » : parmi les candidats à ±3 % de la distance demandée, celui qui
#   ressemble le plus à la forme (meilleur score combiné) ; si aucun n'est aussi proche, le plus proche,
# - le meilleur compromis global entre forme, distance et fluidité.
# Les candidats hors tolérance (trop longs ou trop courts) ne servent que si rien d'autre n'est disponible.
def pick_best(evaluated):
    feasible = [
        e for e in evaluated
        if e["metrics"]["over_max"] <= 1e-6 and e["metrics"].get("under_min", 0.0) <= 1e-6
    ]

    if feasible:
        close_enough = [
            e for e in feasible
            if e["metrics"]["length_gap"] <= CALIBRATION_TOLERANCE * (e["metrics"]["length_target_request"])
        ]
        if close_enough:
            best_close = min(close_enough, key=lambda e: (e["metrics"]["combined"], e["metrics"]["length_gap"]))
        else:
            best_close = min(
                feasible,
                key=lambda e: (
                    e["metrics"]["length_gap"],
                    e["metrics"]["shape_error"],
                    e["metrics"]["turn_penalty"],
                ),
            )
        best_comp = min(
            feasible,
            key=lambda e: (
                e["metrics"]["combined"],
                e["metrics"]["length_gap"],
            ),
        )
    else:
        best_close = min(
            evaluated,
            key=lambda e: (
                e["metrics"]["over_max"],
                e["metrics"]["length_gap"],
                e["metrics"]["shape_error"],
            ),
        )
        best_comp = min(
            evaluated,
            key=lambda e: (
                e["metrics"]["combined"],
                e["metrics"]["over_max"],
            ),
        )
    return best_close, best_comp


# Recherche d'angle en deux temps (grossier puis fin).
# Tester tous les angles à chaque méthode multiplie le travail : un cœur compte 36 angles, et la méthode
# « translation » les reteste tous sur 5 positions. Or le meilleur angle dépend surtout de l'alignement de la
# forme avec les rues, pas de la méthode. On procède donc en deux temps :
# 1) la projection teste un angle sur COARSE_STRIDE (grossier), garde les meilleurs, puis teste leurs voisins (fin) ;
# 2) la translation et le départ inclus ne reprennent que les meilleurs angles de la projection.
# Les formes qui n'ont que peu d'angles (étoile, texte, éclair...) sont testées en entier, comme avant.
COARSE_STRIDE = 2        # un angle sur 2 au premier passage
COARSE_MIN_ANGLES = 12   # en dessous, pas de passage grossier : tout est testé
KEPT_ANGLES = 4          # nombre de meilleurs angles transmis aux autres méthodes


def rank_angles(evaluated):
    """Angles classés du meilleur au moins bon : pour chaque angle, son meilleur candidat (réalisable d'abord,
    puis score combiné)."""
    best = {}
    for e in evaluated:
        m = e["metrics"]
        feasible = m["over_max"] <= 1e-6 and m.get("under_min", 0.0) <= 1e-6
        key = (not feasible, m["combined"])
        angle = m["angle_deg"]
        if angle not in best or key < best[angle]:
            best[angle] = key
    return sorted(best, key=best.get)


def _neighbours(angles, chosen):
    """Angles voisins (dans la liste circulaire `angles`) de ceux déjà choisis, hors les choisis."""
    n = len(angles)
    index = {a: i for i, a in enumerate(angles)}
    out = []
    for a in chosen:
        for k in (-1, 1):
            b = angles[(index[a] + k) % n]
            if b not in chosen and b not in out:
                out.append(b)
    return out


# Lance une méthode de recherche (projection ou translation) avec calibrage de la taille.
# `angle_hint` : meilleurs angles trouvés par la projection (voir ci-dessus) ; la translation s'y limite.
def evaluate_method(graph, base_points, desired_distance_m, tolerance_ratio, shape_name, method_name, angle_hint=None):
    max_allowed_m = desired_distance_m * (1.0 + tolerance_ratio)
    use_translation = (method_name == "translation")
    centers, sizes = shape_layout(base_points, desired_distance_m, shape_name, use_translation)
    angles = search_angles(graph, shape_name)
    sample_count = 60 if shape_name == "text" else 72
    max_size = max(sizes)

    def search(some_angles):
        return calibrated_search(graph, base_points, centers, some_angles, desired_distance_m, max_allowed_m,
                                 sample_count, min_size=80.0, max_size=max_size)

    many_angles = len(angles) >= COARSE_MIN_ANGLES
    if angle_hint is not None and many_angles:
        evaluated = search([a for a in angles if a in angle_hint])
    elif many_angles:
        evaluated = search(angles[::COARSE_STRIDE])
        top = rank_angles(evaluated)[:2]
        evaluated += search(_neighbours(angles, top))
    else:
        evaluated = search(angles)

    best_close, best_comp = pick_best(evaluated)

    return {
        "closest_to_distance": best_close,
        "best_compromise": best_comp,
        "all_candidates_count": len(evaluated),
        "ranked_angles": rank_angles(evaluated)[:KEPT_ANGLES],
    }
