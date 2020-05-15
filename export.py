import lightmill.default_settings as default_settings
from lightmill.csv_export import csv_export
import argparse
import os

if __name__ == "__main__":

    DEFAULT_OUTPUT_DIR = os.environ["LIGHTMILL_EXPORT_DIR"] or "./export"

    parser = argparse.ArgumentParser(description="Lightmill CSV export.")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: {}).".format(DEFAULT_OUTPUT_DIR),
    )
    parser.add_argument(
        "-d",
        "--database",
        default=default_settings.DATABASE_URI,
        type=str,
        help="Database file path (default: {}).".format(default_settings.DATABASE_URI),
    )
    args = parser.parse_args()

    csv_export(args.output_dir, args.database)
