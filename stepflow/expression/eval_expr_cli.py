
import argparse
import json
from stepflow.expression.parameter_mapper import evaluate_expr, apply_parameters, apply_result_expr, apply_output_expr

def main():
    parser = argparse.ArgumentParser(description="Evaluate JSONPath-style expressions for parameter mapping.")
    parser.add_argument("file", help="Path to JSON input file")
    parser.add_argument("--expr", help="Expression to evaluate")
    parser.add_argument("--mode", choices=["input", "result", "output", "raw"], default="raw", help="Evaluation mode")
    parser.add_argument("--parameters", help="Optional JSON parameters to merge with input (used with --mode=input)")
    args = parser.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if args.mode == "raw":
        result = evaluate_expr(data, args.expr)
    elif args.mode == "input":
        parameters = json.loads(args.parameters) if args.parameters else {}
        result = apply_parameters(data, parameters, args.expr)
    elif args.mode == "result":
        result = apply_result_expr(data, args.expr)
    elif args.mode == "output":
        result = apply_output_expr(data, args.expr)
    else:
        raise ValueError("Unknown mode")

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
