"""
Phase 1 Export: Read Braintrust labeled export (JSON), filter human_label == "ok",
write seed_tags.json and seed_prerequisites.json.

Usage:
  1. Export labeled dataset from Braintrust as JSON
  2. Save the export file (default: phase1_labeled_export.json)
  3. Run: python phase1_export_seeds.py [--input phase1_labeled_export.json]
"""

import json
import os
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=os.path.join(os.path.dirname(__file__), "phase1_labeled_export.json"),
        help="Path to Braintrust labeled export JSON file",
    )
    args = parser.parse_args()

    with open(args.input) as f:
        rows = json.load(f)

    seed_tags = []
    seed_prerequisites = []

    for row in rows:
        # Braintrust export includes human annotations — field name may vary.
        # Expected structure after export: row has "input", "expected", and "scores" or "metadata"
        # Human label is stored under scores with the annotation name.
        human_label = None

        # Try common Braintrust export structures
        if "output" in row and isinstance(row["output"], str):
            human_label = row["output"].strip().lower()
        elif "scores" in row:
            human_label = row["scores"].get("human_label") or row["scores"].get("Human Label")
        elif row.get("metadata"):
            human_label = row["metadata"].get("human_label")

        if human_label != "ok":
            continue

        input_data = row.get("input", {})
        row_type = input_data.get("type")
        value = input_data.get("value", "").strip()

        if not value:
            continue

        if row_type == "tag":
            seed_tags.append(value)
        elif row_type == "prerequisite":
            seed_prerequisites.append(value)

    # Deduplicate preserving order
    seed_tags = list(dict.fromkeys(seed_tags))
    seed_prerequisites = list(dict.fromkeys(seed_prerequisites))

    eval_dir = os.path.dirname(__file__)

    with open(os.path.join(eval_dir, "seed_tags.json"), "w") as f:
        json.dump(seed_tags, f, indent=2)

    with open(os.path.join(eval_dir, "seed_prerequisites.json"), "w") as f:
        json.dump(seed_prerequisites, f, indent=2)

    print(f"seed_tags.json:          {len(seed_tags)} tags")
    print(f"seed_prerequisites.json: {len(seed_prerequisites)} prerequisites")


if __name__ == "__main__":
    main()
