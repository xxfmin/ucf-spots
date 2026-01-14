"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { MarkerData, MapProps } from "@/types";
import { formatTime, formatBuildingName } from "@/utils/format";

// UCF campus center coordinates (calculated from building data)
const UCF_CENTER: [number, number] = [-81.2, 28.602];

/**
 * Calculates the default zoom level based on display size
 * @returns Zoom level appropriate for the current screen size
 */
const getDefaultZoom = (): number => {
  if (typeof window === "undefined") return 15.85; // SSR fallback

  const width = window.innerWidth;
  const height = window.innerHeight;

  // Mobile (portrait): < 640px width
  if (width < 640) {
    return 14.6;
  }

  // Mobile (landscape) / Small tablet: 640px - 768px
  if (width < 768) {
    return 15.3;
  }

  // Tablet: 768px - 1024px
  if (width < 1024) {
    return 15.6;
  }

  // Desktop: 1024px - 1440px
  if (width < 1440) {
    return 15.75;
  }

  // Large desktop (MacBook Pro, etc.): 1440px - 1920px
  if (width < 1920) {
    return 15.85;
  }

  // Extra large desktop: >= 1920px
  return 16.0;
};

export default function Map({
  facilityData,
  onMarkerClick,
  onMapLoaded,
}: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<
    globalThis.Map<string, { marker: mapboxgl.Marker; data: MarkerData }>
  >(new globalThis.Map());
  const activePopupRef = useRef<mapboxgl.Popup | null>(null);
  const [isMapLoaded, setIsMapLoaded] = useState(false);

  const handleMarkerClick = useCallback(
    (id: string) => onMarkerClick(id),
    [onMarkerClick]
  );

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current) return;

    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
    if (!token) {
      console.error("Mapbox access token is not configured.");
      return;
    }

    mapboxgl.accessToken = token;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: UCF_CENTER,
      zoom: getDefaultZoom(),
      minZoom: 14,
      maxZoom: 19,
      antialias: true,
    });

    map.current.on("load", () => {
      setIsMapLoaded(true);
      onMapLoaded?.();
    });

    // Add navigation controls
    map.current.addControl(
      new mapboxgl.NavigationControl({ showCompass: false }),
      "top-right"
    );

    // Add geolocation control
    map.current.addControl(
      new mapboxgl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true,
        showUserHeading: true,
      }),
      "top-right"
    );

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [onMapLoaded]);

  // Update markers when facility data changes
  useEffect(() => {
    if (!map.current || !isMapLoaded || !facilityData) return;

    // Close any active popup
    if (activePopupRef.current) {
      activePopupRef.current.remove();
      activePopupRef.current = null;
    }

    /**
     * Creates a marker element with appropriate styling based on availability
     */
    const createMarkerElement = (data: MarkerData): HTMLDivElement => {
      const container = document.createElement("div");
      container.className = "flex items-center justify-center w-6 h-6"; // Stable hit area

      const el = document.createElement("div");
      el.className =
        "transition-all duration-200 ease-out transform-gpu cursor-pointer hover:scale-150";

      const baseClasses = "h-3 w-3 rounded-full";

      if (!data.isOpen) {
        // Closed building - gray
        el.className += ` ${baseClasses} bg-zinc-500 shadow-[0_0_8px_rgba(113,113,122,0.6)]`;
      } else if (data.available === 0) {
        // No rooms available - red
        el.className += ` ${baseClasses} bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]`;
      } else if (data.available < data.total / 2) {
        // Less than half available - yellow
        el.className += ` ${baseClasses} bg-yellow-400 shadow-[0_0_8px_rgba(250,204,21,0.6)]`;
      } else {
        // Many rooms available - green
        el.className += ` ${baseClasses} bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]`;
      }

      container.appendChild(el);
      return container;
    };

    /**
     * Gets the status dot color class based on availability
     */
    const getStatusDotColor = (data: MarkerData): string => {
      if (!data.isOpen) return "bg-zinc-500";
      if (data.available === 0) return "bg-red-500";
      if (data.available < data.total / 2) return "bg-yellow-400";
      return "bg-green-500";
    };

    /**
     * Creates popup HTML content for a marker
     */
    const createPopupContent = (data: MarkerData): string => {
      const dotColor = getStatusDotColor(data);
      const buildingName = formatBuildingName(data.id);

      if (!data.isOpen) {
        return `
          <div class="p-3 min-w-45 bg-zinc-900 rounded-lg">
            <div class="flex items-center gap-2 mb-2">
              <div class="w-2.5 h-2.5 rounded-full ${dotColor} shrink-0 shadow-[0_0_4px_rgba(0,0,0,0.3)]"></div>
              <div class="font-semibold text-sm text-zinc-100">${buildingName}</div>
            </div>
            <div class="text-xs text-zinc-500">
              <span class="text-zinc-400">Closed</span>
              ${
                data.hours.open
                  ? `<span class="mx-1 text-zinc-600">·</span><span class="text-zinc-500">Opens ${formatTime(
                      data.hours.open
                    )}</span>`
                  : ""
              }
            </div>
          </div>
        `;
      }

      return `
        <div class="p-3 min-w-45 bg-zinc-900 rounded-lg">
          <div class="flex items-center gap-2 mb-3">
            <div class="w-2.5 h-2.5 rounded-full ${dotColor} shrink-0 shadow-[0_0_4px_rgba(0,0,0,0.3)]"></div>
            <div class="font-semibold text-sm text-zinc-100">${buildingName}</div>
          </div>
          <div class="flex items-center justify-between text-xs mb-2">
            <span class="text-zinc-500">Rooms available</span>
            <span class="font-semibold text-white bg-zinc-800/50 px-2 py-0.5 rounded-lg">${
              data.available
            }/${data.total}</span>
          </div>
          <div class="h-1.5 bg-zinc-800 rounded-full overflow-hidden border border-zinc-700/50">
            <div class="h-full ${dotColor} rounded-full transition-all shadow-sm" style="width: ${
        (data.available / data.total) * 100
      }%"></div>
          </div>
        </div>
      `;
    };

    /**
     * Sets up hover and click interactions for a marker
     */
    const setupMarkerInteractions = (el: HTMLDivElement, data: MarkerData) => {
      // Show popup on hover
      el.addEventListener("mouseenter", () => {
        activePopupRef.current?.remove();
        activePopupRef.current = new mapboxgl.Popup({
          closeButton: false,
          closeOnClick: false,
          offset: [0, -8],
          className: "ucf-popup",
        })
          .setLngLat([data.coordinates.longitude, data.coordinates.latitude])
          .setHTML(createPopupContent(data))
          .addTo(map.current!);
      });

      // Hide popup on mouse leave
      el.addEventListener("mouseleave", () => {
        activePopupRef.current?.remove();
        activePopupRef.current = null;
      });

      // Handle click - fly to building and trigger accordion
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        activePopupRef.current?.remove();
        activePopupRef.current = null;

        map.current?.flyTo({
          center: [data.coordinates.longitude, data.coordinates.latitude],
          zoom: 17,
          duration: 800,
          essential: true,
        });

        handleMarkerClick(data.id);
      });
    };

    /**
     * Creates or updates a marker on the map
     */
    const createOrUpdateMarker = (key: string, data: MarkerData) => {
      // Remove existing marker if present
      const existing = markersRef.current.get(key);
      if (existing) {
        existing.marker.remove();
      }

      const el = createMarkerElement(data);
      const marker = new mapboxgl.Marker({ element: el })
        .setLngLat([data.coordinates.longitude, data.coordinates.latitude])
        .addTo(map.current!);

      setupMarkerInteractions(el, data);
      markersRef.current.set(key, { marker, data });
    };

    /**
     * Removes markers that are no longer in the data
     */
    const removeStaleMarkers = (keysToRemove: Set<string>) => {
      keysToRemove.forEach((key) => {
        const entry = markersRef.current.get(key);
        if (entry) {
          entry.marker.remove();
          markersRef.current.delete(key);
        }
      });
    };

    // Track current markers to detect removals
    const currentKeys = new Set(markersRef.current.keys());

    // Process each facility
    Object.values(facilityData.facilities).forEach((facility) => {
      if (!facility.coordinates || !facility.roomCounts) {
        console.warn(
          `Facility ${facility.id} missing coordinates or roomCounts`
        );
        return;
      }

      const markerData: MarkerData = {
        id: facility.id,
        name: facility.name,
        coordinates: {
          latitude: facility.coordinates.latitude,
          longitude: facility.coordinates.longitude,
        },
        isOpen: facility.isOpen,
        available: facility.roomCounts.available,
        total: facility.roomCounts.total,
        hours: facility.hours,
      };

      const key = `building-${facility.id}`;

      if (currentKeys.has(key)) {
        currentKeys.delete(key);

        // Check if marker needs update
        const existing = markersRef.current.get(key);
        if (existing) {
          const hasChanged =
            existing.data.isOpen !== markerData.isOpen ||
            existing.data.available !== markerData.available ||
            existing.data.total !== markerData.total;

          if (hasChanged) {
            createOrUpdateMarker(key, markerData);
          }
        }
      } else {
        // New marker
        createOrUpdateMarker(key, markerData);
      }
    });

    // Remove markers for buildings no longer in data
    removeStaleMarkers(currentKeys);

    // Add building labels layer
    try {
      const mapRef = map.current!;
      const sourceId = "building-labels-source";
      const layerId = "building-labels";

      const features = Object.values(facilityData.facilities)
        .filter((f) => f.coordinates)
        .map((f) => ({
          type: "Feature" as const,
          geometry: {
            type: "Point" as const,
            coordinates: [f.coordinates.longitude, f.coordinates.latitude],
          },
          properties: {
            id: f.id,
            name: f.name,
            isOpen: f.isOpen,
            available: f.roomCounts.available,
            total: f.roomCounts.total,
          },
        }));

      const geojson: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features,
      };

      const existingSource = mapRef.getSource(sourceId) as
        | mapboxgl.GeoJSONSource
        | undefined;

      if (existingSource) {
        existingSource.setData(geojson);
      } else {
        mapRef.addSource(sourceId, { type: "geojson", data: geojson });

        mapRef.addLayer({
          id: layerId,
          type: "symbol",
          source: sourceId,
          layout: {
            "text-field": ["get", "name"],
            "text-font": ["DIN Pro Medium", "Arial Unicode MS Regular"],
            "text-size": [
              "interpolate",
              ["linear"],
              ["zoom"],
              15,
              10,
              16,
              11,
              17,
              12,
              18,
              14,
            ],
            "text-anchor": "top",
            "text-offset": [0, 0.8],
            "text-allow-overlap": false,
            "text-max-width": 8,
          },
          paint: {
            "text-color": "#ffffff",
            "text-halo-color": "#000000",
            "text-halo-width": 1.5,
            "text-halo-blur": 0.5,
            "text-opacity": [
              "interpolate",
              ["linear"],
              ["zoom"],
              14.5,
              0,
              15.5,
              1,
            ],
          },
        });

        // Add click interaction for labels
        mapRef.on("click", layerId, (e) => {
          const feature = e.features?.[0];
          if (!feature) return;

          const id = feature.properties?.id as string;
          const coords = (feature.geometry as GeoJSON.Point).coordinates;

          activePopupRef.current?.remove();
          activePopupRef.current = null;

          mapRef.flyTo({
            center: [coords[0], coords[1]],
            zoom: 17,
            duration: 800,
            essential: true,
          });

          handleMarkerClick(id);
        });

        // Change cursor on hover
        mapRef.on("mouseenter", layerId, () => {
          mapRef.getCanvas().style.cursor = "pointer";
        });

        mapRef.on("mouseleave", layerId, () => {
          mapRef.getCanvas().style.cursor = "";
        });
      }
    } catch (error) {
      console.warn("Failed to set up building labels:", error);
    }

    return () => {
      activePopupRef.current?.remove();
      activePopupRef.current = null;
    };
  }, [facilityData, handleMarkerClick, isMapLoaded]);

  return (
    <div ref={mapContainer} className="w-full h-full">
      {!isMapLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
          <div className="text-gray-400">Loading map...</div>
        </div>
      )}
    </div>
  );
}
