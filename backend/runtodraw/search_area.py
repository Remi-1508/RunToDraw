"""Rayon d'extraction : taille de la zone routière à télécharger pour couvrir tous les candidats testés."""
import numpy as np

from runtodraw.geometry import fit_points
from runtodraw.search import shape_layout
from runtodraw.shapes import get_base_shape
from runtodraw.text_routes import split_letter_layout, split_letters


# Rayon d'extraction.
# Le réseau routier n'a besoin de couvrir que les candidats qui seront réellement testés.
# Chaque candidat est « forme de taille S, centrée en c, tournée d'un certain angle » : tous ses points
# sont donc à moins de |c| + S * r_max de l'origine, quel que soit l'angle (r_max = plus grande distance
# au centre de la forme à la taille 1). Le maximum sur tous les candidats, plus une marge pour les
# petits détours des vraies routes, donne le rayon à télécharger.

def _shape_extent_m(base_points, centers, sizes):
    unit = fit_points(base_points, np.zeros(2, dtype=float), 1.0)
    r_max = float(np.max(np.hypot(unit[:, 0], unit[:, 1])))
    return max(float(np.hypot(*c)) for c in centers) + max(sizes) * r_max


def _anchored_extent_m(base_points, sizes):
    """Méthode « départ inclus » : le point de départ est sur le contour, donc tout le dessin tient
    dans un disque de rayon égal à son diamètre (plus grande distance entre deux de ses points)."""
    unit = fit_points(base_points, np.zeros(2, dtype=float), 1.0)
    diffs = unit[:, None, :] - unit[None, :, :]
    diameter = float(np.sqrt((diffs ** 2).sum(-1)).max())
    return max(sizes) * diameter


def required_radius_m(drawing, distance_m):
    drawing = drawing or {}
    mode = drawing.get("mode", "shape")
    text = (drawing.get("text") or "P2I").upper()

    if mode == "text":
        base = get_base_shape("text", text)
        centers, sizes = shape_layout(base, distance_m, "text", use_translation=True)
        extent = max(_shape_extent_m(base, centers, sizes), _anchored_extent_m(base, sizes))
        # Lettres séparées : les distances au centre ne dépendent pas de l'orientation,
        # on peut donc prendre le sens de lecture (1, 0).
        direction, normal = np.array([1.0, 0.0]), np.array([0.0, 1.0])
        for _, letter_base, letter_centers, letter_sizes, _target in split_letter_layout(
            split_letters(text), distance_m, direction, normal
        ):
            extent = max(extent, _shape_extent_m(letter_base, letter_centers, letter_sizes))
    else:
        shape_name = "custom" if mode == "custom" else drawing.get("shape", "heart")
        base = get_base_shape(shape_name, text, drawing.get("points"))
        centers, sizes = shape_layout(base, distance_m, shape_name, use_translation=True)
        extent = max(_shape_extent_m(base, centers, sizes), _anchored_extent_m(base, sizes))

    # Marge pour les détours ; jamais plus que l'ancien rayon (distance / 2), qui reste un plafond.
    margin = 600.0 + 0.05 * extent
    return float(min(extent + margin, distance_m / 2.0))
