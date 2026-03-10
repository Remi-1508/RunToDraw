export function boundsFromCenterRadiusKm(lat, lng, radiusKm) {
  const kmPerDegreeLat = 111.32;
  const deltaLat = radiusKm / kmPerDegreeLat;

  const kmPerDegreeLng = 111.32 * Math.cos((lat * Math.PI) / 180);
  const deltaLng = radiusKm / kmPerDegreeLng;

  const southWest = [lat - deltaLat, lng - deltaLng];
  const northEast = [lat + deltaLat, lng + deltaLng];

  return [southWest, northEast];
}