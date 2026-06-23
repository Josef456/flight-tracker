/* Arrivals map. Plots each flight origin and draws a route to Entebbe, sized by
   how many customs declarations came in on that route. Data is aggregated in
   SQL and served from /api/geo/origins. Uses Leaflet with OpenStreetMap tiles. */
(function () {
  "use strict";
  const el = document.querySelector(".js-map");
  if (!el || typeof L === "undefined") return;

  const navy = "#16344e", brass = "#b6883b", red = "#bf4133";

  const map = L.map(el, { scrollWheelZoom: false, attributionControl: true });
  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap, &copy; CARTO",
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(map);

  function dot(color, r) {
    return L.divIcon({
      className: "",
      html: '<span style="display:block;width:' + r * 2 + "px;height:" + r * 2 +
            "px;border-radius:50%;background:" + color + ";border:2px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,.15)\"></span>",
      iconSize: [r * 2, r * 2],
      iconAnchor: [r, r],
    });
  }

  // A gentle arc between two points so overlapping routes stay readable.
  function arc(a, b) {
    const lat = (a[0] + b[0]) / 2, lng = (a[1] + b[1]) / 2;
    const dx = b[1] - a[1], dy = b[0] - a[0];
    const off = 0.12;
    const ctrl = [lat + dx * off, lng - dy * off];
    const pts = [];
    for (let t = 0; t <= 1.001; t += 0.05) {
      const u = 1 - t;
      pts.push([
        u * u * a[0] + 2 * u * t * ctrl[0] + t * t * b[0],
        u * u * a[1] + 2 * u * t * ctrl[1] + t * t * b[1],
      ]);
    }
    return pts;
  }

  fetch("/api/geo/origins", { headers: { Accept: "application/json" } })
    .then((r) => r.json())
    .then((data) => {
      const dest = data.destination;
      const destLL = [dest.lat, dest.lng];
      const bounds = [destLL];
      const max = Math.max.apply(null, data.origins.map((o) => o.count).concat([1]));

      data.origins.forEach((o) => {
        const ll = [o.lat, o.lng];
        bounds.push(ll);
        const weight = 1 + (o.count / max) * 4;
        L.polyline(arc(ll, destLL), { color: navy, weight: weight, opacity: 0.5 }).addTo(map);
        const r = 5 + (o.count / max) * 9;
        L.marker(ll, { icon: dot(o.flagged > 0 ? red : brass, r) })
          .addTo(map)
          .bindPopup(
            '<div class="route-pop"><b>' + o.city + " (" + (o.code || "") + ")</b>" +
            "<span>" + o.count + " declaration" + (o.count === 1 ? "" : "s") +
            ", " + o.flagged + " flagged</span></div>"
          );
      });

      L.marker(destLL, { icon: dot(navy, 9) })
        .addTo(map)
        .bindPopup('<div class="route-pop"><b>Entebbe (EBB)</b><span>Destination</span></div>');

      map.fitBounds(bounds, { padding: [40, 40] });
    })
    .catch((err) => console.error(err));
})();
