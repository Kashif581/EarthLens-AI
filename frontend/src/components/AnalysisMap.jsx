
import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  LayersControl,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

function FitBounds({ bounds }) {
  const map = useMap();

  useEffect(() => {
    if (bounds?.length === 2) {
      map.fitBounds(bounds, { padding: [20, 20] });
    }
  }, [map, bounds]);

  return null;
}

export default function AnalysisMap({
  tileUrl,
  bounds,
  previewUrl,
}) {
  const [opacity, setOpacity] = useState(0.75);
  const [tileError, setTileError] = useState(false);

  useEffect(() => {
    console.log("Analysis map data:", {
      tileUrl,
      bounds,
      previewUrl,
    });

    setTileError(false);
  }, [tileUrl, bounds, previewUrl]);

  if (!tileUrl || !bounds || bounds.length !== 2) {
    return (
      <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
        <p className="mb-3 text-sm text-amber-600">
          Interactive map data is unavailable. Showing the static preview.
        </p>

        {previewUrl && (
          <img
            src={previewUrl}
            alt="Satellite analysis preview"
            className="w-full rounded-lg"
          />
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="h-[420px] overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
        <MapContainer
          key={tileUrl}
          bounds={bounds}
          scrollWheelZoom
          className="h-full w-full"
        >
          <FitBounds bounds={bounds} />

          <LayersControl position="topright">
            <LayersControl.BaseLayer
              checked
              name="Street Map"
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
                maxZoom={19}
              />
            </LayersControl.BaseLayer>

            <LayersControl.BaseLayer name="Satellite Imagery">
              <TileLayer
                attribution="Tiles &copy; Esri"
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                maxZoom={19}
              />
            </LayersControl.BaseLayer>

            <LayersControl.Overlay
              checked
              name="Analysis Layer"
            >
              <TileLayer
                key={tileUrl}
                url={tileUrl}
                opacity={opacity}
                maxZoom={19}
                eventHandlers={{
                  loading: () => {
                    console.log("Analysis tiles loading...");
                    setTileError(false);
                  },
                  load: () => {
                    console.log("Analysis tiles loaded.");
                    setTileError(false);
                  },
                  tileerror: (event) => {
                    console.error(
                      "Analysis tile failed:",
                      event
                    );
                    setTileError(true);
                  },
                }}
              />
            </LayersControl.Overlay>
          </LayersControl>
        </MapContainer>
      </div>

      {tileError && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          Some analysis tiles failed to load. Check the browser
          console and Network tab for the failed tile request.
        </div>
      )}

      <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
        <div className="mb-2 flex items-center justify-between">
          <label
            htmlFor="analysis-map-opacity"
            className="text-sm font-medium"
          >
            Analysis layer opacity
          </label>

          <span className="text-sm text-slate-500">
            {Math.round(opacity * 100)}%
          </span>
        </div>

        <input
          id="analysis-map-opacity"
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={opacity}
          onChange={(event) =>
            setOpacity(Number(event.target.value))
          }
          className="w-full"
        />
      </div>
    </div>
  );
}
