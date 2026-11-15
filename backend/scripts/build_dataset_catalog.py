"""Build dataset catalog from discovered datasets."""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data_pipeline.catalog import get_dataset_catalog, rebuild_catalog


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Build dataset catalog")
    parser.add_argument("--data-dir", type=str, default=None, help="Data directory path")
    parser.add_argument("--output", type=str, default="data/catalog.json", help="Output catalog file")
    parser.add_argument("--force", action="store_true", help="Force rebuild catalog")
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir) if args.data_dir else None
    
    print("Building dataset catalog...")
    print("=" * 60)
    
    catalog = rebuild_catalog(data_dir)
    
    stats = catalog.get_statistics()
    print(f"\nCatalog Statistics:")
    print(f"  Total datasets: {stats['total_datasets']}")
    print(f"  By type: {stats['by_type']}")
    print(f"  By status: {stats['by_status']}")
    print(f"  By provenance: {stats['by_provenance']}")
    print(f"  Total size: {stats['total_size_bytes'] / (1024*1024):.2f} MB")
    
    output_path = Path(args.output)
    if catalog.export_catalog(Path(args.output)):
        print(f"\nCatalog exported to: {args.output}")
    else:
        print(f"\nFailed to export catalog")
        sys.exit(1)


if __name__ == "__main__":
    main()