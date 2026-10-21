
import { useState } from "react";
import {
  MapPin,
  Thermometer,
  Satellite,
  BookOpen,
  Lightbulb,
  ListChecks,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Info,
} from "lucide-react";

import AnalysisMap from "./AnalysisMap";

function formatValue(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return String(value ?? "N/A");
  }

  return value.toLocaleString(undefined, {
    maximumFractionDigits: 3,
  });
}

function getStatGroups(stats) {
  const groups = {};

  for (const [key, value] of Object.entries(stats || {})) {
    const match = key.match(/^(.*)_(mean|min|max)$/);

    if (!match || typeof value !== "number") continue;

    const [, band, metric] = match;

    if (!groups[band]) groups[band] = {};
    groups[band][metric] = value;
  }

  return Object.entries(groups);
}

function ReportSection({
  icon: Icon,
  title,
  children,
  className = "",
}) {
  return (
    <section
      className={`rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900 ${className}`}
    >
      <div className="mb-3 flex items-center gap-2">
        {Icon && (
          <Icon
            size={18}
            className="shrink-0 text-blue-600 dark:text-blue-400"
          />
        )}
        <h3 className="font-semibold">{title}</h3>
      </div>

      {children}
    </section>
  );
}

function TextList({ items, marker = "bullet" }) {
  if (!Array.isArray(items) || items.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No information available.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {items.map((item, index) => (
        <li
          key={`${index}-${item}`}
          className="flex items-start gap-2 text-sm leading-6 text-slate-700 dark:text-slate-300"
        >
          <span className="mt-0.5 shrink-0 font-semibold text-blue-600 dark:text-blue-400">
            {marker === "number" ? `${index + 1}.` : "•"}
          </span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function AnalysisCard({ data }) {
  const [showTechnicalDetails, setShowTechnicalDetails] =
    useState(false);

  if (!data) return null;

  const {
    reply,
    analysis_title,
    region,
    satellite,
    resolution,
    preview_url,
    tile_url,
    bounds,
    visualization,
    dataset_info,
    methodology,
    interpretation,
    technical_interpretation,
    plain_language_summary,
    key_findings,
    why_it_matters,
    recommended_actions,
    limitations,
    legend,
    stats,
  } = data;

  const statGroups = getStatGroups(stats);

  const title = analysis_title || "Satellite Analysis";

  const summary =
    plain_language_summary || reply || "Analysis completed.";

  const technicalExplanation =
    technical_interpretation || interpretation;

  const temperatureAnalysis =
    title.toLowerCase().includes("heat") ||
    title.toLowerCase().includes("temperature");

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-slate-900 dark:border-slate-800 dark:bg-[#111827] dark:text-white sm:p-6">
      {/* Report header */}
      <header className="mb-6 border-b border-slate-200 pb-5 dark:border-slate-800">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800 dark:bg-blue-950 dark:text-blue-300">
            Satellite Analysis Report
          </span>

          {resolution && (
            <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
              {resolution} resolution
            </span>
          )}
        </div>

        <h2 className="mt-4 text-2xl font-bold sm:text-3xl">
          {title}
        </h2>

        {region && (
          <div className="mt-3 flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
            <MapPin size={16} />
            <span>{region}</span>
          </div>
        )}

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-lg bg-white p-3 dark:bg-slate-900">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Satellite size={15} />
              Satellite
            </div>
            <p className="mt-1 break-words text-sm font-semibold">
              {satellite || "Not specified"}
            </p>
          </div>

          <div className="rounded-lg bg-white p-3 dark:bg-slate-900">
            <div className="text-xs text-slate-500">Dataset</div>
            <p className="mt-1 break-words text-sm font-semibold">
              {dataset_info?.dataset_name || "Not specified"}
            </p>
          </div>

          <div className="rounded-lg bg-white p-3 dark:bg-slate-900">
            <div className="text-xs text-slate-500">Analysis period</div>
            <p className="mt-1 text-sm font-semibold">
              {dataset_info?.date_range || "Not specified"}
            </p>
          </div>
        </div>
      </header>

      {/* Plain-language summary */}
      <section className="mb-6 rounded-xl border border-blue-200 bg-blue-50 p-5 dark:border-blue-900 dark:bg-blue-950/30">
        <div className="mb-3 flex items-center gap-2">
          <BookOpen
            size={20}
            className="text-blue-700 dark:text-blue-400"
          />
          <h3 className="text-lg font-bold">What did we find?</h3>
        </div>

        <p className="text-sm leading-7 text-slate-800 dark:text-slate-200">
          {summary}
        </p>
      </section>

      {/* Key findings */}
      <div className="mb-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ReportSection icon={ListChecks} title="Key Findings">
          <TextList items={key_findings} />
        </ReportSection>

        <ReportSection icon={Lightbulb} title="Why It Matters">
          <p className="text-sm leading-7 text-slate-700 dark:text-slate-300">
            {why_it_matters ||
              "These results can help identify areas for further investigation."}
          </p>
        </ReportSection>
      </div>

      {/* Interactive satellite map */}
      <section className="mb-6">
        <div className="mb-3">
          <h3 className="text-lg font-bold">
            Explore the Satellite Map
          </h3>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Explore the selected area and use the map controls to
            inspect satellite observations.
          </p>
        </div>

        <AnalysisMap
          tileUrl={tile_url}
          bounds={bounds}
          previewUrl={preview_url}
        />

        {visualization && (
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            Displayed index range: {visualization.min ?? "N/A"} to{" "}
            {visualization.max ?? "N/A"}
          </p>
        )}
      </section>

      {/* Statistics */}
      {statGroups.length > 0 && (
        <section className="mb-6">
          <div className="mb-3">
            <h3 className="text-lg font-bold">
              What Do the Numbers Mean?
            </h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              These values summarize measurements from the processed
              satellite image.
            </p>
          </div>

          <div className="space-y-4">
            {statGroups.map(([band, values]) => (
              <div
                key={band}
                className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
              >
                <h4 className="mb-3 font-semibold">{band}</h4>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  {[
                    ["Average", values.mean],
                    ["Lowest", values.min],
                    ["Highest", values.max],
                  ]
                    .filter(([, value]) => value !== undefined)
                    .map(([label, value]) => (
                      <div
                        key={label}
                        className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800"
                      >
                        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                          {temperatureAnalysis && (
                            <Thermometer size={14} />
                          )}
                          {label}
                        </div>

                        <p className="mt-2 text-xl font-bold">
                          {formatValue(value)}
                          {temperatureAnalysis ? "°C" : ""}
                        </p>
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>

          <p className="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">
            Statistics depend on the selected area, date range,
            satellite product, and valid image pixels. Values are
            not automatically percentages.
          </p>
        </section>
      )}

      {/* Recommended actions */}
      <div className="mb-6">
        <ReportSection
          icon={ListChecks}
          title="Recommended Next Steps"
        >
          <TextList
            items={recommended_actions}
            marker="number"
          />
        </ReportSection>
      </div>

      {/* Limitations */}
      <div className="mb-6">
        <ReportSection
          icon={AlertTriangle}
          title="Important Limitations"
        >
          <TextList items={limitations} />
        </ReportSection>
      </div>

      {/* Legend */}
      {legend && Object.keys(legend).length > 0 && (
        <div className="mb-6">
          <ReportSection icon={Info} title="Map Legend">
            <div className="space-y-3">
              {Object.entries(legend).map(([color, description]) => (
                <div
                  key={color}
                  className="flex flex-wrap items-start justify-between gap-2 text-sm"
                >
                  <span className="font-semibold">{color}</span>
                  <span className="flex-1 text-left text-slate-600 dark:text-slate-300 sm:text-right">
                    {description}
                  </span>
                </div>
              ))}
            </div>
          </ReportSection>
        </div>
      )}

      {/* Technical details */}
      <section className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
        <button
          type="button"
          onClick={() =>
            setShowTechnicalDetails((current) => !current)
          }
          className="flex w-full items-center justify-between gap-3 bg-white p-4 text-left hover:bg-slate-50 dark:bg-slate-900 dark:hover:bg-slate-800"
          aria-expanded={showTechnicalDetails}
        >
          <div>
            <h3 className="font-semibold">Technical Details</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Dataset, spectral bands, methodology, and interpretation
            </p>
          </div>

          {showTechnicalDetails ? (
            <ChevronUp size={20} />
          ) : (
            <ChevronDown size={20} />
          )}
        </button>

        {showTechnicalDetails && (
          <div className="space-y-4 border-t border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
            <div>
              <h4 className="mb-2 font-semibold">Dataset Information</h4>

              <div className="space-y-2 break-words text-sm text-slate-600 dark:text-slate-300">
                <p>
                  <strong>Dataset:</strong>{" "}
                  {dataset_info?.dataset_name || "Not specified"}
                </p>

                <p>
                  <strong>Collection:</strong>{" "}
                  {dataset_info?.gee_collection || "Not specified"}
                </p>

                <p>
                  <strong>Date range:</strong>{" "}
                  {dataset_info?.date_range || "Not specified"}
                </p>

                <p>
                  <strong>Resolution:</strong>{" "}
                  {resolution ||
                    dataset_info?.resolution ||
                    "Not specified"}
                </p>

                {dataset_info?.composite_method && (
                  <p>
                    <strong>Composite:</strong>{" "}
                    {dataset_info.composite_method}
                  </p>
                )}

                {dataset_info?.cloud_mask !== undefined && (
                  <p>
                    <strong>Cloud masking:</strong>{" "}
                    {dataset_info.cloud_mask ? "Applied" : "Not specified"}
                  </p>
                )}
              </div>
            </div>

            {dataset_info?.bands_used?.length > 0 && (
              <div>
                <h4 className="mb-2 font-semibold">Spectral Bands</h4>
                <div className="flex flex-wrap gap-2">
                  {dataset_info.bands_used.map((band) => (
                    <span
                      key={band}
                      className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                    >
                      {band}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {methodology && (
              <div>
                <h4 className="mb-2 font-semibold">Methodology</h4>
                <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
                  {methodology}
                </p>
              </div>
            )}

            {technicalExplanation && (
              <div>
                <h4 className="mb-2 font-semibold">
                  Technical Interpretation
                </h4>
                <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
                  {technicalExplanation}
                </p>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
