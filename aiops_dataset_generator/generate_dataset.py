import argparse
import sys
from pathlib import Path
import yaml
import random

from utils.random_utils import SeedManager
from pipeline.dataset_builder import DatasetBuilder
from pipeline.dataset_splitter import DatasetSplitter
from pipeline.dataset_validator import DatasetValidator

def main():
    parser = argparse.ArgumentParser(description="AIOps Incident Correlation & Self-Healing Synthetic Dataset Generator")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Path to config YAML file")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--scenarios", type=int, default=None, help="Number of scenarios to generate")
    parser.add_argument("--output-dir", type=str, default="data", help="Output directory path")
    parser.add_argument("--num-workers", type=int, default=1, help="Number of parallel worker processes")
    args = parser.parse_args()

    # Load configuration
    config_path = Path(args.config)
    config = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    seed = args.seed if args.seed is not None else config.get("random_seed", 42)
    num_scenarios = args.scenarios if args.scenarios is not None else config.get("num_scenarios", 100)

    print(f"=== AIOps Dataset Generator ===")
    print(f"Seed: {seed}")
    print(f"Scenarios: {num_scenarios}")
    print(f"Output Directory: {args.output_dir}")
    print(f"Workers: {args.num_workers}")
    print(f"================================")

    # 1. Build Dataset
    builder = DatasetBuilder(global_seed=seed, config=config)
    dirs = builder.build_dataset(num_scenarios=num_scenarios, output_dir=args.output_dir, num_workers=args.num_workers)

    # 2. Perform Scenario-Level Dataset Splitting
    py_rng = random.Random(seed)
    splitter = DatasetSplitter(
        train_ratio=config.get("train_ratio", 0.70),
        val_ratio=config.get("validation_ratio", 0.15),
        test_ratio=config.get("test_ratio", 0.15)
    )
    splitter.split_dataset(data_dir=args.output_dir, py_rng=py_rng)

    # 3. Validate Dataset Integrity & Anti-Leakage Audit
    validator = DatasetValidator(data_dir=args.output_dir)
    report = validator.validate()

    if report["status"] == "FAILED":
        print("\n❌ Dataset validation failed. Please check the errors above.")
        sys.exit(1)
    else:
        print("\n🎉 Dataset generation, scenario splitting, and validation completed successfully!")

if __name__ == "__main__":
    main()
