"""Répartition de l'évaluation des candidats sur quelques threads.

Un ProcessPoolExecutor a été essayé en premier (la piste "intuitive" pour du
travail CPU), mais mesuré plus lent que le séquentiel une fois le KD-tree en
place : le travail par candidat est tombé à quelques millisecondes, et le
coût de sérialisation entre processus (target, route_points, métriques)
dépasse largement ce qu'on gagnerait à le répartir.

Un petit pool de threads mesure un vrai gain (~1,8x avec 2 threads sur un
graphe de 40 000 nœuds) : les threads partagent la mémoire du graphe, donc
aucune sérialisation, et une bonne partie du travail (KD-tree via scipy,
numpy) relâche le GIL pendant son exécution. Au-delà de 2-4 threads, la
contention sur la partie Dijkstra (boucle Python pure) fait retomber le
gain, d'où un nombre de workers volontairement modeste.
"""

from concurrent.futures import ThreadPoolExecutor

_DEFAULT_WORKERS = 4


def make_executor(max_workers=None):
    """Crée un pool de threads pour répartir l'évaluation des candidats.

    À utiliser comme context manager, le temps d'une planification :
        with make_executor() as executor:
            ...
    """
    return ThreadPoolExecutor(max_workers=max_workers or _DEFAULT_WORKERS)
