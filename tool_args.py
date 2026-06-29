from pydantic import BaseModel, Field, model_validator, field_validator, AfterValidator
from typing import Literal, Optional, Annotated
import os

available_protocols = Literal["protocol-uma","protocol-leia","mindtrails_movement","mindtrails_spanish"]

def literal_to_str(literal):
    return str(literal).replace("typing.Literal","")

def validate_path(path: str) -> str:
    path = path.replace("\\", "/")
    if not os.access(path, mode=0):
        raise ValueError(f"{path} is not a valid file path. Ensure that all file paths begin with './<protocol_name>/'")
    
    return path

def validate_csv_path(path: str) -> str:
    if not path.endswith('.csv'): raise ValueError(f"{path} is not a CSV file")
    return path

FilePath = Annotated[str, AfterValidator(validate_path)]
CSVPath = Annotated[FilePath, AfterValidator(validate_csv_path)]

class protocolArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description=f"The protocol in use. Options are: {literal_to_str(available_protocols)}"
        )
    
class readProtocolArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description=f"The protocol to read files from. Options are: {literal_to_str(available_protocols)}"
        )
    
    file_paths: list[FilePath] = Field(
        description = "List of file paths to read"
    )
class readCSVArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description=f"The protocol to read CSV files from. Options are: {literal_to_str(available_protocols)}"
    )

    csv_path: CSVPath = Field(
        description = "Path to CSV file"
    )

    start: Optional[int] = Field(
        ge = 0,
        default=0,
        description="Index of the first line to read"
    )

    end: Optional[int] = Field(
        default=20,
        description="Index of the final line to read. The difference between end and start cannot be greater than 200"
    )

    @model_validator(mode='after')
    def check_bounds(self):
        with open(self.csv_path, mode='r', encoding="utf-8", errors="replace") as file:
            file_length = len(file.readlines())

        if self.end:

            if self.start and abs(self.end-self.start) > 200:
                raise ValueError(f"end-start cannot be greater than 200 but was {self.end-self.start}")

            if self.end > file_length:
                raise ValueError(f"End index {self.end} out of range for file with {file_length} lines")
        
        return self
    
class searchCSVArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description="The current protocol being worked on"
    )

    csv_path: CSVPath = Field(
        description="Path to the CSV file to search"
    )

    search_string: str = Field(
        description="The string to search for"
    )

    column_name: Optional[str] = Field(
        default=None,
        description="The column to search in (optional)"
    )
    
class editCSVArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description="The name of the protocol that is being edited"
    )

    csv_path: CSVPath = Field(
        description="Path to the CSV file being edited"
    )

    column_name: str = Field(
        description="Column of the cell to edit"
    )

    row_index: int = Field(
        ge=0,
        description="Index of the row to edit"
    )

    new_value: str = Field(
        description="The new value to be placed into the cell"
    )

class findAndReplaceArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description="The name of the protocol that is being edited"
    )

    csv_path: CSVPath = Field(
        description="Path to the CSV file being edited"
    )

    old_value: str = Field(
        description="The value to search for"
    )

    new_value: str = Field(
        description="The new value to replace the old value"
    )

def validate_script_path(path: str) -> str:
    path = validate_path(path)
    normalized = path.replace('\\', '/')
    if '/make/scripts/' not in normalized or not normalized.endswith('.py'):
        raise ValueError('Path must point to a Python file under <protocol>/make/scripts')
    return path

ScriptPath = Annotated[str, AfterValidator(validate_script_path)]

class editScriptArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description="The protocol that owns the script"
    )

    script_path: ScriptPath = Field(
        description="Path to a Python script under <protocol>/make/scripts"
    )

    new_contents: str = Field(
        description="Complete replacement contents for the script"
    )

class editScriptLinesArgs(BaseModel):
    protocol_name: available_protocols

    script_path: ScriptPath = Field(
        description="Path to a Python script under <protocol>/make/scripts"
    )

    start_line: int = Field(ge=1, description="First line to replace (1-based)")
    end_line: int = Field(ge=1, description="Last line to replace (1-based, inclusive)")

    replacement_text: str = Field(
        description="Replacement text for the specified line range. Pass an empty string to delete the range."
    )

    @model_validator(mode='after')
    def check_line_order(self):
        if self.end_line < self.start_line:
            raise ValueError(
                f"end_line ({self.end_line}) must be greater than or equal to start_line ({self.start_line})"
            )
        return self

class latestOrPrerelease(BaseModel):
    latest_or_prerelease: Literal['Latest','Prerelease'] = Field(
        title="Should this release be marked as latest or as a prerelease?"
    )
