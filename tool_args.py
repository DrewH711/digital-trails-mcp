from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
import os

available_protocols = Literal["protocol-uma","protocol-leia","mindtrails_movement","mindtrails_spanish","github-mcp-test"]

def literal_to_str(literal):
    return str(literal).replace("typing.Literal","")

class protocolArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description=f"The protocol to clone. Options are: {literal_to_str(available_protocols)}"
        )
    
class readProtocolArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description=f"The protocol to read files from. Options are: {literal_to_str(available_protocols)}"
        )
    
    file_paths: list[str] = Field(
        description = "List of file paths to read"
    )

    @field_validator('file_paths', mode='before')
    @classmethod
    def validate_file_paths(cls, path_list: list[str]):
        return [path.replace("\\", "/") for path in path_list if os.access(path, mode=0)]
        
class latestOrPrerelease(BaseModel):
    latest_or_prerelease: Literal['Latest','Prerelease'] = Field(
        title="Should this release be marked as latest or as a prerelease?"
    )
