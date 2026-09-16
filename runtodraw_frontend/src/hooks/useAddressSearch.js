import { useEffect, useRef, useState } from "react";
import { searchAddresses } from "../services/geocoding";

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 3;
const DEFAULT_BIAS = [44.8378, -0.5792];

/*
============================================================
Recherche d'adresse avec debounce (attend une pause dans la frappe avant
d'interroger les API) et annulation de la requête précédente si une
nouvelle démarre entre-temps. biasCenter privilégie les résultats proches du
point déjà choisi sur la carte ; onPick est appelée avec [lat, lon] quand
l'utilisateur choisit une suggestion.
============================================================
*/
export function useAddressSearch({ biasCenter, onPick }) {
  const [address, setAddress] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggest, setLoadingSuggest] = useState(false);
  const [searchStatus, setSearchStatus] = useState("");

  const debounceRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    const query = address.trim();

    if (query.length < MIN_QUERY_LENGTH) {
      setSuggestions([]);
      setSearchStatus(query.length === 0 ? "" : "Tape au moins 3 caractères");
      return undefined;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      setLoadingSuggest(true);
      setSearchStatus("Recherche d’adresses…");

      if (abortRef.current) abortRef.current.abort();
      abortRef.current = new AbortController();

      const [latBias, lonBias] = biasCenter ?? DEFAULT_BIAS;

      try {
        const results = await searchAddresses(query, {
          lat: latBias,
          lon: lonBias,
          signal: abortRef.current.signal,
        });
        setSuggestions(results);
        setSearchStatus(
          results.length > 0 ? `${results.length} résultat${results.length > 1 ? "s" : ""}` : "Aucun résultat"
        );
      } catch (error) {
        if (error.name !== "AbortError") {
          console.error(error);
          setSuggestions([]);
          setSearchStatus("Recherche indisponible");
        }
      } finally {
        setLoadingSuggest(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [address, biasCenter]);

  function pickSuggestion(suggestion) {
    onPick([suggestion.lat, suggestion.lon], suggestion.display);
    setAddress(suggestion.display);
    setSuggestions([]);
    setSearchStatus("Adresse sélectionnée");
  }

  return { address, setAddress, suggestions, loadingSuggest, searchStatus, pickSuggestion };
}
