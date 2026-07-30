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

def validate_csv_basename(name: str) -> str:
    """Accept only a bare CSV file name (no directory component, no traversal)."""
    cleaned = name.replace("\\", "/")
    if "/" in cleaned or cleaned in ("", ".", ".."):
        raise ValueError(f"file_name must be a bare CSV file name with no path, got '{name}'")
    if not cleaned.lower().endswith(".csv"):
        raise ValueError(f"'{name}' is not a CSV file")
    return cleaned

CSVFileName = Annotated[str, AfterValidator(validate_csv_basename)]

class swapCSVArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description=f"The protocol whose CSV is being replaced. Options are: {literal_to_str(available_protocols)}"
    )

    file_name: CSVFileName = Field(
        description="Bare name of the CSV file to replace, e.g. 'images.csv'. Must already exist in <protocol>/make/CSV."
    )

    content: str = Field(
        description="Full UTF-8 text contents of the replacement CSV"
    )

class latestOrPrerelease(BaseModel):
    latest_or_prerelease: Literal['Latest','Prerelease'] = Field(
        title="Should this release be marked as latest or as a prerelease?"
    )

class buildSaveReleaseArgs(BaseModel):
    protocol_name: available_protocols = Field(description="The protocol in use")

    release_message: Optional[str] = Field(default=None, description="A one-line description of the release. Leave blank to let an LLM automatically generate this based on the changes made.")

    release_notes: Optional[str] = Field(default=None, description="A detailed description of the release. Leave blank to let an LLM automatically generate this based on the changes made.")

    isLatest: bool = Field(default=False, description="Whether to mark this release as the latest release. Defaults to false")
