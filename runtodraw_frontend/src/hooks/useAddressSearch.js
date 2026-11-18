import { useEffect, useRef, useState } from "react";
import { DEFAULT_CENTER } from "../config";
import { searchPlaces } from "../api/geocoding";

// Recherche d'adresses avec suggestions (voir api/geocoding.js pour les services interrogés).
//
// - la saisie est envoyée telle quelle (majuscules et accents aident le classement),
// - petit délai pendant la frappe, et annulation de la requête précédente,
// - pas de nouvelle recherche quand le texte est celui de la suggestion choisie,
// - les résultats proches du point déjà choisi (ou de Bordeaux par défaut) sont favorisés.
//
// `onPick([lat, lon], label)` est appelée quand l'utilisateur choisit une suggestion.
export function useAddressSearch({ center, onPick }) {
  const [address, setAddress] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  // Recherche internationale en cours (plus lente) : heure de début, pour afficher l'attente.
  const [worldSearchStart, setWorldSearchStart] = useState(null);
  const [worldElapsed, setWorldElapsed] = useState(0);

  const debounceRef = useRef(null);
  const abortRef = useRef(null);
  // Texte de la dernière suggestion choisie : on ne relance pas de recherche dessus.
  const pickedLabelRef = useRef(null);

  useEffect(() => {
    const query = address.trim();

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (query === pickedLabelRef.current) return undefined;

    if (query.length < 3) {
      if (abortRef.current) abortRef.current.abort();
      setWorldSearchStart(null);
      setSuggestions([]);
      setActiveIndex(-1);
      setLoading(false);
      setStatus(query.length === 0 ? "" : "Tape au moins 3 caractères");
      return undefined;
    }

    debounceRef.current = setTimeout(async () => {
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setLoading(true);
      try {
        const results = await searchPlaces(query, {
          bias: center ?? DEFAULT_CENTER,
          signal: controller.signal,
          // Affichage progressif : les premières suggestions arrivent sans attendre le service le plus lent.
          onPhase: (phase) => {
            if (controller.signal.aborted) return;
            setWorldSearchStart(phase === "world-start" ? Date.now() : null);
          },
          onUpdate: (partial) => {
            if (controller.signal.aborted || !partial.length) return;
            setSuggestions(partial);
            setActiveIndex((i) => (i >= 0 && i < partial.length ? i : 0));
          },
        });
        if (controller.signal.aborted) return;
        setSuggestions(results);
        setActiveIndex((i) => (i >= 0 && i < results.length ? i : results.length ? 0 : -1));
        setStatus(
          results.length > 0
            ? `${results.length} résultat${results.length > 1 ? "s" : ""}`
            : "Aucun résultat, essaie avec la ville ou le code postal"
        );
      } catch (error) {
        if (error.name === "AbortError") return;
        console.error(error);
        setSuggestions([]);
        setActiveIndex(-1);
        setStatus(
          error.name === "WorldTimeout"
            ? "La recherche à l’étranger ne répond pas, réessaie dans un instant"
            : "Recherche indisponible, vérifie ta connexion"
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
          setWorldSearchStart(null);
        }
      }
    }, 150);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // `center` volontairement absent : choisir un point ne doit pas relancer la recherche.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [address]);

  // Compteur de secondes pendant la recherche internationale.
  useEffect(() => {
    if (worldSearchStart === null) {
      setWorldElapsed(0);
      return undefined;
    }
    const timer = setInterval(() => {
      setWorldElapsed(Math.floor((Date.now() - worldSearchStart) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [worldSearchStart]);

  // Les requêtes en cours sont annulées au démontage.
  useEffect(() => () => abortRef.current?.abort(), []);

  function changeAddress(value) {
    pickedLabelRef.current = null;
    setAddress(value);
  }

  function pickSuggestion(suggestion) {
    const label = [suggestion.title, suggestion.subtitle].filter(Boolean).join(", ");
    pickedLabelRef.current = label;
    if (abortRef.current) abortRef.current.abort();
    onPick([suggestion.lat, suggestion.lon], label);
    setAddress(label);
    setSuggestions([]);
    setActiveIndex(-1);
    setLoading(false);
    setWorldSearchStart(null);
    setStatus("Point de départ choisi");
  }

  // Navigation au clavier dans la liste : flèches, Entrée pour choisir, Échap pour fermer.
  function handleKeyDown(event) {
    if (!suggestions.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((i) => (i + 1) % suggestions.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => (i - 1 + suggestions.length) % suggestions.length);
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      pickSuggestion(suggestions[activeIndex]);
    } else if (event.key === "Escape") {
      setSuggestions([]);
      setActiveIndex(-1);
    }
  }

  return {
    address,
    changeAddress,
    suggestions,
    loading,
    status,
    activeIndex,
    setActiveIndex,
    worldSearchStart,
    worldElapsed,
    pickSuggestion,
    handleKeyDown,
  };
}
