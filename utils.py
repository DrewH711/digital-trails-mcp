import tool_args
from fastmcp.server.dependencies import get_access_token

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

def validate_user():
    ALLOW_LIST = {"user_3GVABHlVRLtumhBnIIkAY1IH7oF","user_3GBhLGw7Fczb9jDNvmHEkOwUExh","user_3GBggq1svMAQChxeWLLGnGUspAx","user_3GDxg44ltExURYV4LnmvOaYgnUS","user_3GEZRLcl7NmMUrrUePGNyTgUigE","user_3GY5LNS9apzvI534vneTJM2OIw4"}

    token = get_access_token()
    
    if not token:
        raise Exception("No valid token found")

    print(token.claims)    
    
    if token.claims.get('sub') in ALLOW_LIST:
        return True
    
    raise Exception("Access denied")
