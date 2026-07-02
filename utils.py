import re, tool_args
import pygit2

def _validate_semver(raw: str):

    semver_pattern = r'^[0-9]+\.[0-9]+\.[0-9]+$'
    if raw is None:
        return None, "Release rejected: no version number was produced."

    version = raw.strip()
    if not re.match(semver_pattern, version):
        return None, (
            f"Release rejected: '{raw}' is not a valid semantic version "
            f"(expected MAJOR.MINOR.PATCH (without 'v'), e.g. 1.2.3). No release was created."
        )

    return version, None

def _check_python_syntax(source: str, path: str):
    """Return an error message if `source` is not valid Python, otherwise None.

    Lets us reject an edit before writing it, so a malformed or hallucinated
    change never lands on disk and breaks the script.
    """
    try:
        compile(source, path, 'exec')
    except SyntaxError as e:
        return (
            f"Edit rejected: the result would not be valid Python "
            f"({e.msg} at line {e.lineno}, column {e.offset}). "
            f"No changes were written to {path}."
        )
    return None

def _numbered_excerpt(lines: list[str], start: int, end: int) -> str:
    """1-based, inclusive, clamped excerpt of `lines` with line numbers."""
    start = max(1, start)
    end = min(len(lines), end)
    rendered = []
    for i in range(start, end + 1):
        text = lines[i - 1].rstrip('\n').rstrip('\r')
        rendered.append(f"{i}\t{text}")
    return "\n".join(rendered)

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