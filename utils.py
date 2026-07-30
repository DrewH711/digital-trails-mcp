import tool_args
from fastmcp.server.dependencies import get_access_token
from typing import Literal

def get_github_url(protocol: tool_args.available_protocols) -> str:
    if protocol in ["mindtrails_movement", "mindtrails_spanish"]:
        return f"https://github.com/TeachmanLab/{protocol}"
    else:
        return f"https://github.com/digital-trails/{protocol}"
    
def get_repo_owner(protocol: tool_args.available_protocols) -> str:
    if protocol in ["mindtrails_movement", "mindtrails_spanish"]:
        return f"TeachmanLab/{protocol}" 
    else:
        return f"digital-trails/{protocol}"
    
def _parse_tag(tag: str):
    tag = tag.replace('refs/tags/','').strip("v").strip()

    nums = tag.split('.')

    try:
        major = int(nums[0])
        minor = int(nums[1])
        patch = int(nums[2])

        return (major, minor, patch)
    
    except:
        raise Exception("Tag in invalid form. Must be `MAJOR.MINOR.PATCH` or `vMAJOR.MINOR.PATCH`")

def increment_tag(tag: str):
    semver = _parse_tag(tag)
    return f'{semver[0]}.{semver[1]}.{semver[2] + 1}'

def enforce_role(role: Literal["admin", "member"]):

    token = get_access_token()
    
    if not token:
        raise Exception("No valid token found")
    
    if token.claims.get('user')["role"] == f'org:{role}':
        return
    
    raise Exception("Access denied")
