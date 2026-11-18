import { useState } from "react";
import { styles } from "./styles";

// Petit drapeau du pays d'un résultat de recherche.
// Images de flagcdn.com (gratuit) plutôt que des emojis : Windows n'affiche pas les
// drapeaux emoji (on y verrait « FR », « GB »…). Si l'image ne charge pas, on affiche le code pays.
export default function CountryFlag({ code, country }) {
  const [failed, setFailed] = useState(false);
  if (!/^[a-z]{2}$/.test(code || "")) return null;
  if (failed) {
    return <span style={styles.flagFallback} title={country}>{code.toUpperCase()}</span>;
  }
  return (
    <img
      src={`https://flagcdn.com/20x15/${code}.png`}
      srcSet={`https://flagcdn.com/40x30/${code}.png 2x`}
      width={20}
      height={15}
      alt={country || code.toUpperCase()}
      title={country}
      loading="lazy"
      style={styles.flag}
      onError={() => setFailed(true)}
    />
  );
}
