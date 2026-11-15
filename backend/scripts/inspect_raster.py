"""Inspect raster file metadata and properties."""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data_pipeline.raster_loader import get_raster_info
from app.data_pipeline.validation import validate_raster


def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_raster.py <path_to_raster>")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: File not found: {path}")
        sys.exit(1)
    
    print(f"Inspecting raster: {path}")
    print("=" * 60)
    
    # Get basic info
    info = get_raster_info(path)
    if "error" in info:
        print(f"Error: {info['error']}")
        sys.exit(1)
    
    print(f"Width: {info['width']} px")
    print(f"Height: {info['height']} px")
    print(f"Bands: {info['count']}")
    print(f"Data type: {info['dtype']}")
    print(f"CRS: {info['crs']}")
    print(f"Bounds: {info['bounds']}")
    print(f"Resolution: {info['resolution']}")
    print(f"NoData value: {info['nodata']}")
    print(f"Driver: {info['driver']}")
    
    print("\nValidating...")
    print("=" * 60)
    
    result = validate_raster(Path(sys.argv[1]))
    print(f"Valid: {result.is_valid}")
    print(f"Dataset ID: {result.dataset_id}")
    
    for issue in result.issues:
        print(f"  [{issue.severity.value.upper()}] {issue.code}: {issue.message}")
        if issue.field:
            print(f"    Field: {issue.field}")
        if issue.details:
            print(f"    Details: {issue.details}")
    
    # Save validation report
    report = result.to_dict()
    report_path = Path(sys.argv[1]).with_suffix(".validation.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nValidation report saved to: {report_path}")


if __name__ == "__main__":
    main()