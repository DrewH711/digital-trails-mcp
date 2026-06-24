from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional

available_protocols = Literal["protocol-uma","protocol-leia","mindtrails_movement","mindtrails_spanish","github-mcp-test"]

def literal_to_str(literal):
    return str(literal).replace("typing.Literal","")

class protocolArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description=f"The protocol to clone. Options are: {literal_to_str(available_protocols)}"
        )
    
class releaseProtocolArgs(BaseModel):
    protocol_name: available_protocols = Field(
        description=f"The protocol to clone. Options are: {literal_to_str(available_protocols)}"
        )
    
class latestOrPrerelease(BaseModel):
    latest_or_prerelease: Literal['Latest','Prerelease'] = Field(
        title="Should this release be marked as latest or as a prerelease?"
    )
