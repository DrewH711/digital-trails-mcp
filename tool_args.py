from pydantic import BaseModel, Field, model_validator, field_validator, AfterValidator
from typing import Literal, Optional, Annotated
import os

available_protocols = Literal["protocol-uma","protocol-leia","mindtrails_movement","mindtrails_spanish","github-mcp-test"]

def literal_to_str(literal):
    return str(literal).replace("typing.Literal","")

def validate_path(path: str) -> str:
    path = path.replace("\\", "/")
    if not os.access(path, mode=0):
        raise ValueError(f"{path} is not a valid file path. Ensure that all file paths begin with './<protocol_name>/'")
    
    return path

FilePath = Annotated[str, AfterValidator(validate_path)]

class protocolArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description=f"The protocol to clone. Options are: {literal_to_str(available_protocols)}"
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

    file_path: FilePath = Field(
        description = "Path to CSV file"
    )

    start: int = Field(
        ge = 0,
        default=0,
        description="Index of the first line to read"
    )

    end: int = Field(
        default=20,
        description="Index of the final line to read. The difference between end and start cannot be greater than 200"
    )

    @field_validator('file_path', mode='after')
    @classmethod
    def validate_csv(cls, path: str) -> str:
        if not path.lower().endswith(".csv"): raise ValueError("File is not CSV")
        return path

    @model_validator(mode='after')
    def check_bounds(self):
        with open(self.file_path, mode='r', encoding="utf-8", errors="replace") as file:
            file_length = len(file.readlines())

        if abs(self.end-self.start) > 200:
            raise ValueError(f"end-start cannot be greater than 200 but was {self.end-self.start}")

        if self.end > file_length:
            raise ValueError(f"End index {self.end} out of range for file with {file_length} lines")
        
        return self
        
class latestOrPrerelease(BaseModel):
    latest_or_prerelease: Literal['Latest','Prerelease'] = Field(
        title="Should this release be marked as latest or as a prerelease?"
    )
