import ee

from core.validator import GEECommand
from gee.operations.ndvi import run_ndvi
from gee.operations.sar import run_sar
from gee.operations.land_cover import run_land_cover
from gee.operations.flood import run_flood
from gee.operations.burn_area import run_burn_area
from gee.operations.urban_heat import run_urban_heat
from gee.operations.ndwi import run_ndwi
from gee.operations.evi import run_evi
from utils.region_resolver import resolve_region


OPERATION_MAP = {
    "NDVI": run_ndvi,
    "SAR": run_sar,
    "LAND_COVER": run_land_cover,
    "FLOOD": run_flood,
    "BURN_AREA": run_burn_area,
    "URBAN_HEAT": run_urban_heat,
    "NDWI": run_ndwi,
    "EVI": run_evi,
}

VIS_MAP = {
    "NDVI": {
        "min": -0.2, "max": 0.8,
        "palette": ["red", "yellow", "lightgreen", "darkgreen"],
    },
    "EVI": {
        "min": -0.2, "max": 0.8,
        "palette": ["red", "yellow", "lightgreen", "darkgreen"],
    },
    "NDWI": {
        "min": -0.5, "max": 0.5,
        "palette": ["brown", "white", "blue"],
    },
    "SAR": {
        "min": -25, "max": 0,
        "palette": ["black", "white"],
    },
    "FLOOD": {
        "min": -25, "max": 0,
        "palette": ["white", "blue"],
    },
    "LAND_COVER": {
        "min": 1, "max": 17,
        "palette": ["blue", "green", "yellow", "orange", "red"],
    },
    "BURN_AREA": {
        "min": -0.5, "max": 0,
        "palette": ["yellow", "orange", "red", "darkred"],
    },
    "URBAN_HEAT": {
        "min": 25, "max": 55,
        "palette": ["blue", "yellow", "orange", "red"],
    },
}


def get_stats(image: ee.Image, region: ee.Geometry) -> dict:
    """Calculate mean, minimum, and maximum for each image band."""
    result = image.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            reducer2=ee.Reducer.minMax(),
            sharedInputs=True,
        ),
        geometry=region,
        scale=100,
        maxPixels=1e9,
        bestEffort=True,
    ).getInfo()

    return {
        key: value
        for key, value in (result or {}).items()
        if value is not None
    }


def get_preview_url(
    image: ee.Image,
    region: ee.Geometry,
    operation: str,
) -> str:
    """Generate a static PNG preview as a fallback."""
    vis_params = VIS_MAP.get(operation, {"min": 0, "max": 1})

    return image.visualize(**vis_params).getThumbURL({
        "region": region,
        "dimensions": 1024,
        "format": "png",
    })


def get_map_data(
    image: ee.Image,
    region: ee.Geometry,
    operation: str,
) -> dict:
    """Generate Earth Engine tiles and Leaflet-compatible bounds."""
    vis_params = VIS_MAP.get(operation, {"min": 0, "max": 1})

    # Create a map tile URL from the Earth Engine image.
    map_id = image.getMapId(vis_params)
    tile_url = map_id["tile_fetcher"].url_format

    # Convert the region's rectangular bounds to Leaflet format:
    # [[south, west], [north, east]]
    ring = region.bounds().coordinates().getInfo()[0]

    longitudes = [point[0] for point in ring]
    latitudes = [point[1] for point in ring]

    bounds = [
        [min(latitudes), min(longitudes)],
        [max(latitudes), max(longitudes)],
    ]

    return {
        "tile_url": tile_url,
        "bounds": bounds,
        "visualization": vis_params,
    }


async def execute_command(command: GEECommand) -> dict:
    operation = command.operation.upper()
    region = resolve_region(command.region.value)

    params = {
        "operation": operation,
        "satellite": command.satellite,
        "start_date": command.date_range.start,
        "end_date": command.date_range.end,
        "output_mode": command.output_mode,
        "parameters": command.parameters or {},
    }

    handler = OPERATION_MAP.get(operation)

    if not handler:
        raise ValueError(
            f"Operation '{operation}' has no registered handler."
        )

    image = handler(params, region)

    if command.output_mode != "tile_preview":
        return {"job_id": "export_coming_soon"}

    # Keep the PNG preview for fallback use.
    preview_url = get_preview_url(image, region, operation)

    # Calculate image statistics before visualization.
    stats = get_stats(image, region)

    # Generate the data needed for the interactive Leaflet map.
    map_data = get_map_data(image, region, operation)

    return {
        "preview_url": preview_url,
        "stats": stats,
        **map_data,
    }
