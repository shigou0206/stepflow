# stepflow/engine/field_value.py

from enum import Enum

class FieldMode(str, Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    JSONATA = "jsonata"

class FieldValue:
    """
    描述一个字段的配置:
      - mode: "static", "dynamic", or "jsonata"
      - value: 若 static => literal
               若 dynamic => "$.contextPath"
               若 jsonata => "Jsonata表达式"
    """
    def __init__(self, mode: FieldMode, value):
        self.mode = mode
        self.value = value

    def __repr__(self):
        return f"FieldValue(mode={self.mode}, value={self.value})"