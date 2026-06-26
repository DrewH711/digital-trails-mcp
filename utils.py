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