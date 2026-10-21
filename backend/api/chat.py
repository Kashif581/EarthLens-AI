
import json
import math
import os
import uuid

from fastapi import APIRouter, HTTPException
from groq import Groq

from config import settings
from schemas.requests import ChatRequest
from schemas.responses import ChatResponse
from core.validator import validate_command
from gee.executor import execute_command


router = APIRouter(prefix="/api", tags=["chat"])

sessions: dict = {}

groq_client = Groq(api_key=settings.groq_api_key)


TITLES = {
    "NDVI": "Vegetation Health Analysis",
    "EVI": "Vegetation Greenness Analysis",
    "NDWI": "Water Detection Analysis",
    "SAR": "Radar Surface Analysis",
    "FLOOD": "Potential Flood Detection",
    "URBAN_HEAT": "Urban Surface Temperature Analysis",
    "BURN_AREA": "Burn Area Analysis",
    "LAND_COVER": "Land Cover Analysis",
    "CLIMATE": "Climate Analysis",
    "TIMESERIES": "Satellite Time-Series Analysis",
}


COMMAND_SYSTEM_PROMPT = """
You are the command-generation engine for GeoVision AI.

Convert the user's natural-language request into ONE valid JSON object
representing a GEECommand. Do not return an explanation or Markdown.

The required structure is:

{
  "operation": "NDVI",
  "satellite": "SENTINEL_2",
  "region": {
    "type": "named",
    "value": "Lahore"
  },
  "date_range": {
    "start": "2025-01-01",
    "end": "2025-12-31"
  },
  "output_mode": "tile_preview",
  "parameters": {}
}

Follow the actual GEECommand schema and use these exact allowed values.

Allowed operations:
NDVI, NDWI, BURN_AREA, URBAN_HEAT, LAND_COVER,
FLOOD, CLIMATE, TIMESERIES, EVI, SAR.

Allowed satellites:
MODIS, LANDSAT_8, LANDSAT_9, SENTINEL_1, SENTINEL_2.

Never use operation aliases such as calculate_ndvi or NDVI_Analysis.
Never use descriptive satellite names such as Sentinel-2 or Landsat 8.
Use only the exact allowed enum values.

For a named place:
"region": {"type": "named", "value": "Lahore"}

For a bounding box:
"region": {
  "type": "bbox",
  "value": [min_longitude, min_latitude, max_longitude, max_latitude]
}

Never return GeoJSON Point, Feature, or FeatureCollection objects.
A single coordinate is not a bounding box.
If the user supplies a place name, use that place name.
Do not invent a region.

Use dates requested by the user. If the user does not specify dates,
choose a reasonable recent date range supported by the selected dataset.
The end date must not be in the future.

Use tile_preview for map-based analysis requests.

Return all required fields in the correct types.
Return valid JSON only.
"""


# ---------------------------------------------------------
# Command generation and normalization
# ---------------------------------------------------------

def normalize_gee_command(command_data: dict) -> dict:
    """Normalize common LLM aliases before schema validation."""

    if not isinstance(command_data, dict):
        return {}

    data = dict(command_data)

    operation_aliases = {
        "CALCULATE_NDVI": "NDVI",
        "NDVI_ANALYSIS": "NDVI",
        "CALCULATE_NDWI": "NDWI",
        "NDWI_ANALYSIS": "NDWI",
        "CALCULATE_EVI": "EVI",
        "EVI_ANALYSIS": "EVI",
        "SAR_ANALYSIS": "SAR",
        "LAND_COVER_ANALYSIS": "LAND_COVER",
        "FLOOD_ANALYSIS": "FLOOD",
        "BURN_AREA_ANALYSIS": "BURN_AREA",
        "URBAN_HEAT_ANALYSIS": "URBAN_HEAT",
        "CLIMATE_ANALYSIS": "CLIMATE",
        "TIMESERIES_ANALYSIS": "TIMESERIES",
    }

    operation = data.get("operation")
    if isinstance(operation, str):
        operation = operation.strip().upper()
        data["operation"] = operation_aliases.get(
            operation, operation
        )

    satellite_aliases = {
        "SENTINEL-1": "SENTINEL_1",
        "SENTINEL-2": "SENTINEL_2",
        "LANDSAT 8": "LANDSAT_8",
        "LANDSAT 8 OLI/TIRS": "LANDSAT_8",
        "LANDSAT 9": "LANDSAT_9",
    }

    satellite = data.get("satellite")
    if isinstance(satellite, str):
        satellite = satellite.strip().upper()
        data["satellite"] = satellite_aliases.get(
            satellite, satellite
        )

    # Only convert a GeoJSON Feature when a place name is explicit.
    region = data.get("region")

    if isinstance(region, dict):
        region_type = region.get("type")

        if region_type == "Feature":
            properties = region.get("properties") or {}
            place_name = (
                properties.get("name")
                or properties.get("region")
                or properties.get("place")
            )

            if place_name:
                data["region"] = {
                    "type": "named",
                    "value": place_name,
                }

    return data


def generate_gee_command(
    user_message: str,
    history: list | None = None,
    retry_error: str | None = None,
) -> dict | None:
    """Generate a GEE command, independently of the report-generation LLM."""

    messages = [
        {
            "role": "system",
            "content": COMMAND_SYSTEM_PROMPT,
        }
    ]

    # Include only a small amount of conversational context.
    for turn in (history or [])[-4:]:
        if (
            isinstance(turn, dict)
            and turn.get("role") in {"user", "assistant"}
            and isinstance(turn.get("content"), str)
        ):
            messages.append(turn)

    user_content = (
        "Generate a GEECommand JSON object for this request:\n"
        f"{user_message}"
    )

    if retry_error:
        user_content += (
            "\n\nYour previous command failed validation. "
            "Correct the command to satisfy the schema. "
            "Validation error:\n"
            f"{retry_error}\n"
            "Return the complete corrected JSON command only."
        )

    messages.append({
        "role": "user",
        "content": user_content,
    })

    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=1500,
        )

        content = response.choices[0].message.content

        if not content:
            return None

        parsed = json.loads(content)

        if not isinstance(parsed, dict):
            return None

        return normalize_gee_command(parsed)

    except Exception as exc:
        print(f"GEE command generation failed: {exc}")
        return None


# ---------------------------------------------------------
# Analysis metadata
# ---------------------------------------------------------

def build_analysis_metadata(command):
    operation = command.operation.upper()

    date_range = (
        f"{command.date_range.start} to {command.date_range.end}"
    )

    metadata = {
        "dataset_info": {
            "date_range": date_range,
            "dataset_name": "Satellite Dataset",
        },
        "methodology": (
            f"{operation} analysis was performed using Google Earth Engine."
        ),
        "interpretation": (
            "The satellite analysis has been completed. "
            "Interpret the result using the selected dataset and legend."
        ),
        "legend": {},
    }

    if operation == "NDVI":
        metadata.update({
            "dataset_info": {
                "date_range": date_range,
                "dataset_name": "Sentinel-2 Level-2A",
                "gee_collection": "COPERNICUS/S2_SR_HARMONIZED",
                "resolution": "10 m",
                "bands_used": ["B4 (Red)", "B8 (Near Infrared)"],
                "cloud_mask": True,
                "composite_method": "Median Composite",
            },
            "methodology": (
                "NDVI compares red and near-infrared reflectance "
                "to estimate vegetation-related spectral signals."
            ),
            "interpretation": (
                "Higher NDVI values generally indicate greener vegetation. "
                "Lower values may reflect sparse vegetation, bare soil, "
                "built-up areas, or water."
            ),
            "legend": {
                "Red": "Sparse vegetation or bare surfaces",
                "Orange": "Lower vegetation index",
                "Yellow": "Moderate vegetation index",
                "Light Green": "Higher vegetation index",
                "Dark Green": "Dense vegetation signal",
            },
        })

    elif operation == "EVI":
        metadata.update({
            "dataset_info": {
                "date_range": date_range,
                "dataset_name": "Sentinel-2 Level-2A",
                "gee_collection": "COPERNICUS/S2_SR_HARMONIZED",
                "resolution": "10 m",
                "bands_used": [
                    "B2 (Blue)",
                    "B4 (Red)",
                    "B8 (Near Infrared)",
                ],
            },
            "methodology": (
                "EVI uses blue, red, and near-infrared reflectance "
                "to estimate vegetation greenness."
            ),
            "interpretation": (
                "Higher EVI values generally indicate stronger vegetation "
                "signals. Season and date range can influence the result."
            ),
            "legend": {
                "Red": "Lower vegetation index",
                "Yellow": "Moderate vegetation index",
                "Green": "Higher vegetation index",
            },
        })

    elif operation == "NDWI":
        metadata.update({
            "dataset_info": {
                "date_range": date_range,
                "dataset_name": "Sentinel-2 Level-2A",
                "gee_collection": "COPERNICUS/S2_SR_HARMONIZED",
                "resolution": "10 m",
                "bands_used": ["B3 (Green)", "B8 (Near Infrared)"],
            },
            "methodology": (
                "NDWI compares green and near-infrared reflectance "
                "to highlight potential water-related patterns."
            ),
            "interpretation": (
                "Higher values can indicate water, but shadows and other "
                "surface features may affect the result."
            ),
            "legend": {
                "Dark Blue": "Higher water index",
                "Light Blue": "Possible water",
                "Yellow": "Lower water index",
                "Brown": "Low or negative index",
            },
        })

    elif operation == "SAR":
        metadata.update({
            "dataset_info": {
                "date_range": date_range,
                "dataset_name": "Sentinel-1 GRD",
                "gee_collection": "COPERNICUS/S1_GRD",
                "resolution": "10 m",
            },
            "methodology": (
                "Sentinel-1 radar imagery is used to examine "
                "surface backscatter patterns."
            ),
            "interpretation": (
                "Radar returns depend on surface roughness, moisture, "
                "viewing geometry, and land cover."
            ),
            "legend": {
                "White": "Higher radar return",
                "Gray": "Moderate radar return",
                "Black": "Lower radar return",
            },
        })

    elif operation == "URBAN_HEAT":
        metadata.update({
            "dataset_info": {
                "date_range": date_range,
                "dataset_name": "Landsat 8 Collection 2 Level-2",
                "gee_collection": "LANDSAT/LC08/C02/T1_L2",
                "resolution": "30 m",
            },
            "methodology": (
                "Landsat thermal imagery is used to examine land surface "
                "temperature. Interpretation depends on the processing "
                "and temperature conversion in the analysis."
            ),
            "interpretation": (
                "Built-up and bare surfaces may be warmer than vegetated "
                "areas. Land surface temperature is not air temperature."
            ),
            "legend": {
                "Blue": "Cooler surface",
                "Green": "Moderate surface temperature",
                "Yellow": "Warmer surface",
                "Red": "Hotter surface",
            },
        })

    elif operation == "FLOOD":
        metadata.update({
            "dataset_info": {
                "date_range": date_range,
                "dataset_name": "Sentinel-1 GRD",
                "gee_collection": "COPERNICUS/S1_GRD",
                "resolution": "10 m",
            },
            "methodology": (
                "The configured satellite workflow examines patterns "
                "associated with potential flooding."
            ),
            "interpretation": (
                "Potential detections are not definitive proof of flooding. "
                "Permanent water and radar conditions can affect results."
            ),
            "legend": {
                "Blue": "Potential water or flood detection",
                "White": "Other or undetected area",
            },
        })

    elif operation == "BURN_AREA":
        metadata.update({
            "dataset_info": {
                "date_range": date_range,
                "dataset_name": "Satellite burn-area analysis",
            },
            "methodology": (
                "The configured workflow analyses spectral patterns "
                "that may be associated with burned land."
            ),
            "interpretation": (
                "Other land-cover changes can produce similar signals."
            ),
            "legend": {
                "Yellow": "Lower index response",
                "Orange": "Moderate index response",
                "Red": "Stronger index response",
            },
        })

    elif operation == "LAND_COVER":
        metadata.update({
            "dataset_info": {
                "date_range": date_range,
                "dataset_name": "Land cover classification",
            },
            "methodology": (
                "The selected land-cover workflow assigns surface "
                "categories to locations in the mapped area."
            ),
            "interpretation": (
                "Category meanings depend on the classification product "
                "and its class definitions."
            ),
            "legend": {},
        })

    return metadata


# ---------------------------------------------------------
# Safe JSON conversion and fallback reporting
# ---------------------------------------------------------

def make_json_safe(value):
    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [make_json_safe(item) for item in value]

    if hasattr(value, "item"):
        try:
            return make_json_safe(value.item())
        except (ValueError, TypeError):
            pass

    if isinstance(value, float) and not math.isfinite(value):
        return None

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def build_fallback_report(
    operation,
    region,
    date_range,
    stats,
    metadata,
):
    summaries = {
        "NDVI": (
            "The vegetation analysis is ready. Higher index values "
            "generally indicate stronger vegetation signals."
        ),
        "EVI": (
            "The vegetation greenness analysis is ready. Seasonal "
            "conditions can influence the observed patterns."
        ),
        "NDWI": (
            "The water-index analysis is ready. The map highlights "
            "patterns that may be associated with water."
        ),
        "FLOOD": (
            "The potential flood analysis is ready. Detected areas "
            "require independent verification."
        ),
        "URBAN_HEAT": (
            "The surface-temperature analysis is ready. The result "
            "describes land surface temperature, not air temperature."
        ),
        "SAR": (
            "The radar analysis is ready. Bright and dark areas "
            "represent differences in radar backscatter."
        ),
        "BURN_AREA": (
            "The burn-area analysis is ready. The mapped patterns "
            "may require comparison with other dates."
        ),
        "LAND_COVER": (
            "The land-cover analysis is ready. Category accuracy "
            "depends on the source and classification method."
        ),
    }

    summary = summaries.get(
        operation,
        f"The {operation} analysis for {region} is ready.",
    )

    finding = metadata["interpretation"]

    if not stats:
        finding += " No usable pixel statistics were returned."

    return {
        "plain_language_summary": (
            f"{summary} Selected region: {region}. "
            f"Date range: {date_range}."
        ),
        "key_findings": [finding],
        "why_it_matters": (
            "The results can help identify areas for further inspection "
            "or comparison with other dates and independent data."
        ),
        "recommended_actions": [
            "Inspect the map and its legend.",
            "Compare with other imagery or independent data before "
            "making important decisions.",
        ],
        "limitations": [
            "Clouds, shadows, surface conditions, and processing choices "
            "can affect satellite results.",
            "Potential detections should be independently verified "
            "before important decisions are made.",
        ],
        "technical_interpretation": metadata["interpretation"],
    }


def generate_interpretation(
    operation,
    region,
    date_range,
    stats,
    metadata,
):
    """Generate a report without risking loss of a successful map."""

    safe_stats = make_json_safe(stats or {})

    fallback = build_fallback_report(
        operation,
        region,
        date_range,
        safe_stats,
        metadata,
    )

    if not settings.groq_api_key:
        return fallback

    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": """
You explain satellite analysis to non-experts.
Return only a valid JSON object with:
plain_language_summary (string),
key_findings (array of strings),
why_it_matters (string),
recommended_actions (array of strings),
limitations (array of strings),
technical_interpretation (string).

Use only the supplied data. Do not invent measurements, trends,
causes, or risks. Explain uncertainty. Distinguish vegetation
signals from proven plant health, water signals from confirmed
flooding, and land surface temperature from air temperature.
""",
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "operation": operation,
                        "region": region,
                        "date_range": date_range,
                        "statistics": safe_stats,
                        "dataset_info": metadata["dataset_info"],
                        "methodology": metadata["methodology"],
                        "interpretation": metadata["interpretation"],
                    }, allow_nan=False),
                },
            ],
            temperature=0,
            max_tokens=1400,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            return fallback

        report = json.loads(content)
        if not isinstance(report, dict):
            return fallback

        summary = report.get("plain_language_summary")
        if not isinstance(summary, str) or not summary.strip():
            return fallback

        def clean_list(key):
            value = report.get(key)
            if not isinstance(value, list):
                return fallback[key]
            result = [
                item.strip()
                for item in value
                if isinstance(item, str) and item.strip()
            ]
            return result or fallback[key]

        return {
            "plain_language_summary": summary.strip(),
            "key_findings": clean_list("key_findings"),
            "why_it_matters": (
                report.get("why_it_matters")
                if isinstance(report.get("why_it_matters"), str)
                else fallback["why_it_matters"]
            ),
            "recommended_actions": clean_list("recommended_actions"),
            "limitations": clean_list("limitations"),
            "technical_interpretation": (
                report.get("technical_interpretation")
                if isinstance(
                    report.get("technical_interpretation"), str
                )
                else fallback["technical_interpretation"]
            ),
        }

    except Exception as exc:
        print(f"Report generation failed: {exc}")
        return fallback


# ---------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    history = sessions.get(session_id, [])

    # Generate a GEE command using its own dedicated prompt.
    raw_command = generate_gee_command(
        user_message=request.message,
        history=history,
    )

    if not raw_command:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not generate a valid satellite-analysis command. "
                "Please try again with a clear operation and region."
            ),
        )

    command, error = validate_command(raw_command)

    # Retry once if validation fails.
    if error:
        raw_command = generate_gee_command(
            user_message=request.message,
            history=history,
            retry_error=str(error),
        )

        if not isinstance(raw_command, dict):
            raw_command = {}

        command, error = validate_command(raw_command)

        if error:
            print(f"GEE command validation failed: {error}")
            raise HTTPException(
                status_code=422,
                detail=f"Invalid command after retry: {error}",
            )

    # Execute the validated command.
    try:
        result = await execute_command(command)
    except Exception as exc:
        print(f"Satellite execution failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=(
                "Satellite analysis failed. Check the operation, region, "
                "date range, dataset, and Earth Engine configuration."
            ),
        ) from exc

    operation = command.operation.upper()
    metadata = build_analysis_metadata(command)
    dataset_info = metadata["dataset_info"]

    # Save conversation history.
    history.extend([
        {"role": "user", "content": request.message},
        {
            "role": "assistant",
            "content": json.dumps(raw_command),
        },
    ])
    sessions[session_id] = history[-10:]

    # Map-based analysis response.
    if command.output_mode == "tile_preview":
        stats = result.get("stats") or {}

        report = generate_interpretation(
            operation=operation,
            region=command.region.value,
            date_range=dataset_info["date_range"],
            stats=stats,
            metadata=metadata,
        )

        return ChatResponse(
            reply=report["plain_language_summary"],
            session_id=session_id,
            analysis_title=TITLES.get(operation, operation),
            region=command.region.value,
            satellite=str(command.satellite),
            resolution=dataset_info.get("resolution"),

            preview_url=result.get("preview_url"),
            tile_url=result.get("tile_url"),
            bounds=result.get("bounds"),
            visualization=result.get("visualization"),

            dataset_info=dataset_info,
            methodology=metadata["methodology"],
            stats=stats,
            legend=metadata["legend"],

            plain_language_summary=report["plain_language_summary"],
            key_findings=report["key_findings"],
            why_it_matters=report["why_it_matters"],
            recommended_actions=report["recommended_actions"],
            limitations=report["limitations"],
            interpretation=report["technical_interpretation"],
            technical_interpretation=report["technical_interpretation"],
        )

    # Export-job response.
    return ChatResponse(
        reply=f"Export requested. Job ID: {result.get('job_id')}",
        session_id=session_id,
        analysis_title=TITLES.get(operation, operation),
        region=command.region.value,
        satellite=str(command.satellite),
        resolution=dataset_info.get("resolution"),
        job_id=result.get("job_id"),
        dataset_info=dataset_info,
        methodology=metadata["methodology"],
        stats=result.get("stats"),
    )
