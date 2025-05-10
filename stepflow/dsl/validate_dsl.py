
import argparse
from stepflow.dsl.dsl_loader import load_and_validate_dsl, SchemaValidationError
from stepflow.dsl.dsl_validator import validate_semantic
from pydantic import ValidationError as PydanticValidationError


def main():
    parser = argparse.ArgumentParser(description="Validate a StepFlow DSL file.")
    parser.add_argument("file", help="Path to the DSL file (JSON/YAML)")
    parser.add_argument("--schema", required=True, help="Path to JSON Schema file")
    args = parser.parse_args()

    try:
        model = load_and_validate_dsl(args.file, args.schema)
        print("✅ Schema validation passed.")
    except SchemaValidationError as e:
        print(f"❌ Schema validation failed:\n{e}")
        return
    except PydanticValidationError as e:
        print("❌ Model validation failed:")
        print(e)
        return

    semantic_errors = validate_semantic(model)
    if semantic_errors:
        print("❌ Semantic validation failed:")
        for e in semantic_errors:
            print(f"  - {e}")
    else:
        print("✅ Semantic validation passed.")


if __name__ == "__main__":
    main()
