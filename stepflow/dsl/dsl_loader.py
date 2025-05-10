
import json
import yaml
from pathlib import Path
from typing import Union
from jsonschema import Draft7Validator
from pydantic import ValidationError as PydanticValidationError

from stepflow.dsl.dsl_model import WorkflowDSL


class SchemaValidationError(Exception):
    pass


def load_dsl_file(file_path: Union[str, Path]) -> dict:
    path = Path(file_path)
    with open(path, 'r', encoding='utf-8') as f:
        if path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif path.suffix == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")


def validate_with_schema(data: dict, schema_path: Union[str, Path]) -> None:
    schema = json.loads(Path(schema_path).read_text(encoding='utf-8'))
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(data))
    if errors:
        messages = [f"{e.message} at {list(e.path)}" for e in errors]
        raise SchemaValidationError("Schema validation failed:\n" + "\n".join(messages))


def parse_dsl_model(data: dict) -> WorkflowDSL:
    try:
        return WorkflowDSL.model_validate(data)
    except PydanticValidationError as e:
        raise e
    
def parse_dsl_json(dsl_json: str) -> WorkflowDSL:
    try:
        return WorkflowDSL.model_validate_json(dsl_json)
    except PydanticValidationError as e:
        raise e


def load_and_validate_dsl(file_path: Union[str, Path], schema_path: Union[str, Path]) -> WorkflowDSL:
    dsl_raw = load_dsl_file(file_path)
    validate_with_schema(dsl_raw, schema_path)
    return parse_dsl_model(dsl_raw)
