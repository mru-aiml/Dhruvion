"""Validate GeoJSON file structure and content."""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data_pipeline.vector_loader import validate_geojson, get_vector_info
from app.data_pipeline.validation import validate_vector


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_geojson.py <path_to_geojson>")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: File not found: {path}")
        sys.exit(1)
    
    print(f"Validating GeoJSON: {path}")
    print("=" * 60)
    
    # Get basic info
    info = get_vector_info(path)
    if "error" in info:
        print(f"Error: {info['error']}")
        sys.exit(1)
    
    print(f"Feature count: {info['feature_count']}")
    print(f"Geometry types: {', '.join(info['geometry_types'])}")
    print(f"Property keys: {', '.join(info['property_keys'])}")
    print(f"CRS: {info['crs']}")
    
    print("\nValidating structure...")
    print("=" * 60)
    
    with open(path, "r") as f:
        data = json.load(f)
    
    is_valid, errors = validate_geojson(data)
    
    if is_valid:
        print("✓ GeoJSON structure is valid")
    else:
        print("✗ GeoJSON structure has errors:")
        for err in errors:
            print(f"  - {err}")
    
    print("\nRunning validation checks...")
    print("=" * 60)
    
    from app.data_pipeline.validation import validate_vector
    result = validate_vector(Path(sys.argv[1]))
    
    print(f"Overall valid: {result.is_valid}")
    print(f"Dataset ID: {result.dataset_id}")
    
    for issue in result.issues:
        severity = issue.severity.value.upper()
        print(f"  [{severity}] {issue.code}: {issue.message}")
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