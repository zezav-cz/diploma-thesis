"""Export OpenAPI specification to a JSON file."""

import argparse
import json
import sys
from pathlib import Path

from fastapi import FastAPI

from app.routers.http import health
from app.routers.http.v1 import v1_router


def export_openapi_spec(spec_type: str = "v1", output_dir: str = "doc") -> None:
    """Export OpenAPI specification to a JSON file.

    Args:
        spec_type: Type of spec to export - 'health' or 'v1'
        output_dir: Output directory (default: 'doc')
    """
    if spec_type == "health":
        # Create minimal app with just health endpoints
        app = FastAPI(title="Health Endpoints")
        app.include_router(health.router)
        openapi_schema = app.openapi()
    elif spec_type == "v1":
        # Export v1 router directly
        openapi_schema = v1_router.openapi()
    else:
        print(f"Error: Invalid spec_type '{spec_type}'. Must be 'health' or 'v1'")
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Write to file
    output_file = output_path / f"openapi_{spec_type}.json"
    output_file.write_text(json.dumps(openapi_schema, indent=2))

    print(f"OpenAPI specification ({spec_type}) exported to: {output_file.absolute()}")
    print(f'Total endpoints: {len(openapi_schema.get("paths", {}))}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export OpenAPI specification to JSON files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
      Export health and v1 specs to doc/ directory

  %(prog)s --specs v1
      Export only v1 spec to doc/openapi_v1.json

  %(prog)s --specs health,v1 --output docs
      Export both specs to docs/ directory

  %(prog)s -s v1 -o api-specs
      Short form: export v1 spec to api-specs/ directory
        """,
    )

    parser.add_argument(
        "-s",
        "--specs",
        type=str,
        default="health,v1",
        help="Comma-separated list of spec types to export. Options: health, v1 (default: health,v1)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="doc",
        help="Directory to save the JSON files (default: doc)",
    )

    args = parser.parse_args()

    # Parse spec types
    spec_types = [s.strip() for s in args.specs.split(",")]

    # Export each spec type
    for spec_type in spec_types:
        export_openapi_spec(spec_type, args.output)
