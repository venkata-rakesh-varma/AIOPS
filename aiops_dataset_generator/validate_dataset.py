import argparse
import sys
from pathlib import Path
from pipeline.dataset_validator import DatasetValidator

def main():
    parser = argparse.ArgumentParser(description="Validate AIOps Dataset Integrity and Anti-Leakage Rules")
    parser.add_argument("--data-dir", type=str, default="data", help="Directory containing generated dataset")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: Target dataset directory '{data_dir}' does not exist.")
        sys.exit(1)

    validator = DatasetValidator(data_dir=data_dir)
    report = validator.validate()

    if report["status"] == "FAILED":
        print("\n❌ Dataset validation failed!")
        sys.exit(1)
    else:
        print("\n✅ Dataset validation passed cleanly!")

if __name__ == "__main__":
    main()
