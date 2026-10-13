"use client";

import { useEffect, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LagosMap() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<any>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !mapRef.current || mapInstance.current) return;
    let cancelled = false;

    async function init() {
      const L = (await import("leaflet")).default;
      // @ts-ignore
      await import("leaflet/dist/leaflet.css");
      if (cancelled || !mapRef.current) return;

      const map = L.map(mapRef.current).setView([6.5244, 3.3792], 10);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap",
        maxZoom: 18,
      }).addTo(map);

      mapInstance.current = map;

      // Load LGA markers from API
      try {
        const res = await fetch(`${API}/api/v1/geo/hierarchy?level=lga&limit=50`);
        if (res.ok) {
          const lgas = await res.json();
          // Approximate Lagos LGA centres for display when no geometry
          const approx: Record<string, [number, number]> = {
            Ikeja: [6.6018, 3.3515],
            "Lagos Island": [6.4541, 3.3947],
            "Lagos Mainland": [6.507, 3.384],
            Surulere: [6.4969, 3.356],
            Alimosho: [6.610, 3.250],
            Agege: [6.621, 3.325],
            Mushin: [6.533, 3.354],
            Oshodi: [6.556, 3.336],
            "Oshodi-Isolo": [6.556, 3.336],
            Apapa: [6.441, 3.363],
            Eti-Osa: [6.458, 3.601],
            Ikorodu: [6.619, 3.510],
            Badagry: [6.431, 2.887],
            Epe: [6.584, 3.983],
            "Ibeju-Lekki": [6.469, 3.840],
            Kosofe: [6.556, 3.390],
            Shomolu: [6.541, 3.387],
            "Ifako-Ijaiye": [6.670, 3.310],
            "Ajeromi-Ifelodun": [6.455, 3.334],
            "Amuwo-Odofin": [6.458, 3.288],
            Ojo: [6.458, 3.195],
          };
          lgas.forEach((g: any) => {
            const coords = approx[g.name];
            if (coords) {
              L.circleMarker(coords, {
                radius: 8,
                color: "#10b981",
                fillColor: "#059669",
                fillOpacity: 0.7,
              })
                .addTo(map)
                .bindPopup(
                  `<strong>${g.name}</strong><br/>LGA · ${g.is_placeholder ? "placeholder" : "official"}`
                );
            }
          });
        }
      } catch {
        L.marker([6.5244, 3.3792])
          .addTo(map)
          .bindPopup("Lagos State · CLAIM Geo Intelligence");
      }
    }

    init();
    return () => {
      cancelled = true;
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, []);

  return <div ref={mapRef} className="h-full w-full rounded bg-slate-950" style={{ minHeight: 380 }} />;
}
