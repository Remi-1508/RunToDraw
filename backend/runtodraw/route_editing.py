"""Édition manuelle d'un itinéraire : déplacer, insérer ou supprimer un point d'ancrage.

Un segment est décrit par son chemin (indices de nœuds du graphe) et par la position, dans ce chemin, de
ses points d'ancrage. Ce sont les « sommets » que l'utilisateur voit et manipule sur la carte : entre deux
ancrages consécutifs, le tracé est le plus court chemin sur le réseau routier.

Modifier un ancrage ne touche donc que les (au plus deux) tronçons voisins : le coût d'une édition est de
deux recherches A*, indépendamment de la taille de l'itinéraire. Les fonctions sont pures (aucun état
conservé côté serveur) : le client renvoie le segment, le serveur renvoie le segment recalculé.
"""
import numpy as np

from runtodraw.geometry import latlon_to_xy_m, polyline_length

# Un point déposé trop loin de tout chemin est refusé plutôt que « aimanté » vers une rue sans rapport.
MAX_SNAP_M = 300.0
MIN_ANCHORS = 2


class EditError(ValueError):
    """Édition impossible (point trop loin du réseau, tronçon inaccessible, opération invalide)."""


# Nœud du réseau le plus proche d'un point GPS ; erreur s'il est au-delà de MAX_SNAP_M.
def snap_latlon(graph, lat, lon, max_snap_m=MAX_SNAP_M):
    x, y = latlon_to_xy_m(lat, lon, graph.center_lat, graph.center_lon)
    indices, distances = graph.nearest_indices(np.array([[x, y]]))
    if float(distances[0]) > max_snap_m:
        raise EditError("Ce point est trop éloigné des routes ou chemins.")
    return int(indices[0])


# Relie une suite de nœuds par des plus courts chemins. Renvoie (chemin, position de chaque nœud d'entrée).
def connect(graph, nodes):
    path = [nodes[0]]
    positions = [0]
    for start, goal in zip(nodes[:-1], nodes[1:]):
        leg, _ = graph.shortest_path_idx(start, goal)
        if leg is None:
            raise EditError("Ce point est inaccessible depuis le reste du tracé.")
        path.extend(leg[1:])
        positions.append(len(path) - 1)
    return path, positions


# Remplace, dans un segment, la portion comprise entre les ancrages `lo` et `hi` (exclus) par un chemin
# passant par `middle` (liste de nœuds, éventuellement vide). `lo` ou `hi` valent None en bout de segment.
# Renvoie (nouveau chemin, nouveaux ancrages, positions des nœuds de `middle`).
def _rebuild(graph, path, anchors, lo, hi, middle):
    chain = []
    if lo is not None:
        chain.append(path[anchors[lo]])
    chain.extend(middle)
    if hi is not None:
        chain.append(path[anchors[hi]])

    head = path[:anchors[lo]] if lo is not None else []
    tail = path[anchors[hi] + 1:] if hi is not None else []
    mid_path, positions = connect(graph, chain)
    offset = len(head)

    new_path = head + mid_path + tail
    shift = len(new_path) - len(path)

    first_new = 1 if lo is not None else 0
    middle_positions = [offset + positions[first_new + i] for i in range(len(middle))]
    kept_before = anchors[:lo + 1] if lo is not None else []
    kept_after = [a + shift for a in anchors[hi:]] if hi is not None else []
    new_anchors = sorted(set(kept_before + middle_positions + kept_after))
    return new_path, new_anchors, middle_positions


def _check_anchor(anchors, k):
    if not 0 <= k < len(anchors):
        raise EditError("Point d'ancrage inconnu.")


def move_anchor(graph, path, anchors, k, node):
    """Déplace l'ancrage k vers le nœud `node` et recalcule les deux tronçons voisins."""
    _check_anchor(anchors, k)
    lo = k - 1 if k > 0 else None
    hi = k + 1 if k + 1 < len(anchors) else None
    new_path, new_anchors, _ = _rebuild(graph, path, anchors, lo, hi, [node])
    return new_path, new_anchors


def insert_anchor(graph, path, anchors, k, node):
    """Insère un nouvel ancrage sur le tronçon qui suit l'ancrage k (entre k et k+1)."""
    _check_anchor(anchors, k)
    if k + 1 >= len(anchors):
        raise EditError("Aucun tronçon à cet endroit.")
    new_path, new_anchors, _ = _rebuild(graph, path, anchors, k, k + 1, [node])
    return new_path, new_anchors


def delete_anchor(graph, path, anchors, k):
    """Supprime l'ancrage k : les voisins sont reliés directement (en bout de segment, le tracé est raccourci)."""
    _check_anchor(anchors, k)
    if len(anchors) <= MIN_ANCHORS:
        raise EditError("Il faut garder au moins deux points sur le tracé.")
    lo = k - 1 if k > 0 else None
    hi = k + 1 if k + 1 < len(anchors) else None
    if lo is None:      # premier point : le tracé commence désormais au suivant
        cut = anchors[1]
        return path[cut:], [a - cut for a in anchors[1:]]
    if hi is None:      # dernier point : le tracé s'arrête au précédent
        cut = anchors[-2]
        return path[:cut + 1], anchors[:-1]
    new_path, new_anchors, _ = _rebuild(graph, path, anchors, lo, hi, [])
    return new_path, new_anchors


# Applique une opération {"type", "anchor", "lat", "lon"} à un segment {"node_path", "anchors"} (indices).
def apply_operation(graph, segment, operation):
    path, anchors = segment["node_path"], segment["anchors"]
    kind = operation["type"]
    k = operation["anchor"]
    if kind == "delete":
        new_path, new_anchors = delete_anchor(graph, path, anchors, k)
    elif kind in ("move", "insert"):
        node = snap_latlon(graph, operation["lat"], operation["lon"])
        edit = move_anchor if kind == "move" else insert_anchor
        new_path, new_anchors = edit(graph, path, anchors, k, node)
    else:
        raise EditError("Opération inconnue.")
    return {**segment, "node_path": new_path, "anchors": new_anchors}


# Recalcule les liaisons d'un mot « lettres reliées » après modification d'une lettre : chaque liaison
# relie la fin de la lettre précédente au début de la suivante.
def _relink(graph, segments, index):
    for j in (index - 1, index + 1):
        if 0 <= j < len(segments) and segments[j].get("kind") == "link":
            before = segments[j - 1]["node_path"][-1] if j - 1 >= 0 else None
            after = segments[j + 1]["node_path"][0] if j + 1 < len(segments) else None
            if before is None or after is None:
                continue
            link, _ = connect(graph, [before, after])
            segments[j] = {**segments[j], "node_path": link, "anchors": []}


# Édite le segment `index` d'un itinéraire (liste de segments en indices de nœuds) et renvoie la nouvelle liste.
def edit_route(graph, segments, index, operation):
    if not 0 <= index < len(segments):
        raise EditError("Segment inconnu.")
    if segments[index].get("kind") == "link":
        raise EditError("Les liaisons entre lettres ne se modifient pas directement.")
    updated = [dict(s) for s in segments]
    updated[index] = apply_operation(graph, updated[index], operation)
    _relink(graph, updated, index)
    return updated


# Longueur en mètres d'un chemin d'indices de nœuds.
def path_length_m(graph, path):
    if len(path) < 2:
        return 0.0
    return float(polyline_length(graph.node_array[path]))

