// Accès au stockage local du navigateur, sans planter s'il est indisponible (navigation privée, par exemple).
export function readStorage(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeStorage(key, value) {
  try {
    localStorage.setItem(key, String(value));
  } catch {
    // stockage indisponible : le réglage ne sera simplement pas mémorisé
  }
}
