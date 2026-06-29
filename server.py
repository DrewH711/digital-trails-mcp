from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext
from dotenv import load_dotenv
import subprocess
import tool_args
import os
import shutil
import requests
import json
import pandas
from utils import _check_python_syntax, _numbered_excerpt

load_dotenv("keys.env")

server = FastMCP(name="digital-trails-autodeploy", instructions="Use tools from this server to deploy a digital trails-based project such as Leia, Mindtrails-Movement, Mindtrails-Spanish, UMA, or github-mcp-test")

def get_github_path(protocol: tool_args.available_protocols) -> str:
    if protocol in ["mindtrails_movement", "mindtrails_spanish"]:
        return f"https://github.com/TeachmanLab/{protocol}"
    elif protocol=="github-mcp-test":
        return f"https://github.com/DrewH711/{protocol}"
    else:
        return f"https://github.com/digital-trails/{protocol}"
    
def get_owner_repo(protocol: tool_args.available_protocols) -> str:
    if protocol in ["mindtrails_movement", "mindtrails_spanish"]:
        return f"TeachmanLab/{protocol}"
    elif protocol=="github-mcp-test":
        return f"DrewH711/{protocol}"   
    else:
        return f"digital-trails/{protocol}"

@server.tool(description="Clone a protocol into the current directory so it can be read and modified")
def get_protocol(args: tool_args.protocolArgs):
    
    try:
        if os.access(args.protocol_name, mode=0):
            return f"Protocol '{args.protocol_name}' retrieved"
        
        subprocess.run(['git','switch','main'], check=True, shell=True)
        subprocess.run(f"git clone {get_github_path(args.protocol_name)}", shell=True, check=True)
        subprocess.run(['git','switch','agent-testing'], cwd=f'./{args.protocol_name}', check=True, shell=True)

        return f"Protocol '{args.protocol_name}' retrieved"
    
    except Exception as e:
        return f"Exception occurred: {e}"
    
@server.tool(description="Ask the user to specify the protocol to perform actions on")
async def specify_protocol(ctx: Context = CurrentContext()):
    result = await ctx.elicit(
        message = "Please specify a protocol to perform actions on",
        response_type=tool_args.protocolArgs
    )

    if result.action=='accept':
        return result.data.protocol_name
    elif result.action=='decline':
        return "No protocol specified"
    else: return "Operation cancelled"
    
    
@server.tool(description="Save all changes to a protocol")
async def save_protocol(args: tool_args.protocolArgs, ctx: Context = CurrentContext()):

    if not os.access(args.protocol_name, mode=0):
        return f"Protocol '{args.protocol_name}' not found. Please use `get_protocol` first."
    
    repo_dir = args.protocol_name
    
    if args.protocol_name!="github-mcp-test":
        subprocess.run(["python", "make/scripts/sessions.py"], cwd=repo_dir, check=True)
        await ctx.report_progress(progress=40,total=100)
        subprocess.run(["python", "make/scripts/surveys.py"], cwd=repo_dir, check=True)
        await ctx.report_progress(progress=45,total=100)
        if os.access(f'{repo_dir}/make/scripts/resources.py', mode=0): subprocess.run(["python","make/scripts/resources.py"], cwd=repo_dir, check=True)

        src = f"{repo_dir}/make/~out"
        dst = f"{repo_dir}/src/flows"
        shutil.copytree(src, dst, dirs_exist_ok=True)
        await ctx.report_progress(progress=50,total=100)

    # get git diff and create changenotes
    git_diff_bytes = subprocess.run(['git','diff','--diff-algorithm','minimal'], cwd=repo_dir, capture_output=True, check=True).stdout
    git_diff = bytes.decode(git_diff_bytes, "utf-8", errors="ignore")

    release_notes_result = await ctx.sample(
        messages=f"Here is the git diff. Summarize the changes into release notes.\n {git_diff[0:1000]}", # truncate git diff at 1000 characters to stay within context window
        system_prompt="Provide a bulleted list of changes. Be brief",
        temperature=0.5,
        max_tokens=350
    )
    await ctx.report_progress(progress=65,total=100)

    release_notes = release_notes_result.text

    await ctx.set_state(key = 'release notes', value=release_notes)

    commit_message_result = await ctx.sample(
        messages = f"Here are some change notes: {release_notes}" 
        "Summarize these into a one-line commit message.",
        system_prompt="Be descriptive but brief",
        temperature=0.3,
        max_tokens=50
    )

    await ctx.report_progress(progress=90,total=100)

    # commit and push changes
    subprocess.run(['git','switch','agent-testing'], cwd=repo_dir, check=True)
    subprocess.run(['git', 'add', '-A'], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", f"{commit_message_result.text}", "-m", f"{release_notes}"], cwd=repo_dir, check=True)
    await ctx.report_progress(progress=95,total=100)
    subprocess.run(["git", "push"], cwd=repo_dir, check=True)
    await ctx.report_progress(progress=100,total=100)
    return("Successfuly saved protocol")
    

@server.tool(description="Create and publish new release for a protocol")
async def save_and_release_protocol(args: tool_args.protocolArgs, ctx: Context = CurrentContext()):
    # ensure existence of protocol

    if not os.access(args.protocol_name, mode=0):
        return f"Protocol '{args.protocol_name}' not found. Please use `get_protocol` first."
    
    # save changes
    await server.call_tool(name="save_protocol", arguments={'args':tool_args.protocolArgs(protocol_name=args.protocol_name)})

    # create new release number and push release
    last_release_number_bytes = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=args.protocol_name,
        capture_output=True,
        check=True
    ).stdout

    try:
        last_release_number = bytes.decode(last_release_number_bytes, 'utf-8')
        if(len(last_release_number)==0):
            last_release_number = "0.0.0"

    except UnicodeDecodeError:
        last_release_number = "0.0.0"

    release_notes = await ctx.get_state('release notes')

    release_number_result = await ctx.sample(
        messages=f"The previous release was numbered {last_release_number}. The release notes are: {release_notes}. Based on the previous release number and description, give the new semantic versioning number. Normally, only the `patch` number should be incremented. If there are significant changes, you may increment the `minor` number. Never increment the `major` version number unless specifically instructed.",
        system_prompt="Only provide the semantic versioning number and nothing else.",
        temperature=0,
        max_tokens=5
    )

    new_release_number = release_number_result.text
    
    isPrerelease = await ctx.elicit(
        message="Mark as prerelease?",
        response_type=tool_args.latestOrPrerelease
    )

    # must use GitHub REST API to publish releases because it cannot be done via command line
    requests.post(
        f"https://api.github.com/repos/{get_owner_repo(args.protocol_name)}/releases",
        headers={
            "Authorization": f"Bearer {os.getenv('GITHUB_PAT')}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "tag_name": new_release_number,
            "name": new_release_number,
            "body": release_notes,
            "prerelease": (isPrerelease.action=='accept' and isPrerelease.data.latest_or_prerelease == "prerelease")
        },
    ).raise_for_status()

    return "Protocol released successfully"

# return lists of paths to python scripts and CSVs
# There are far too many JSON files to be useful, and they will be regenerated by the scripts on release anyway
@server.tool(description="List file paths from a protocol")
def get_protocol_csv_list(protocol: tool_args.available_protocols):

    if not os.access(protocol, mode=0): return f"Protocol {protocol} not found. Use `get_protocol` tool first."

    path = os.getcwd() + f"/{protocol}/make/CSV"
    return [file for file in os.listdir(path) if (file.endswith(".csv") and "image" not in file)]

@server.tool(description="View list of available python scripts")
def get_protocol_python_script_list(protocol: tool_args.available_protocols):
    if not os.access(protocol, mode=0): return f"Protocol {protocol} not found. Use `get_protocol` tool first."
    
    path = os.getcwd() + f"/{protocol}/make/scripts"
    return [file for file in os.listdir(path) if (file.endswith(".py") and "image" not in file)]

@server.tool(description="Get file contents from a protocol")
def get_file_contents(args: tool_args.readProtocolArgs):

    file_contents = {}

    for path in args.file_paths:

        with open(path, encoding="utf-8", errors="replace") as file:
            file_contents[path] = file.read()

    return file_contents

@server.tool(description="Replace the entire contents of a Python script under <protocol>/make/scripts. The edit is rejected if the result is not valid Python. Prefer edit_protocol_script_lines for small, targeted changes.")
def edit_protocol_script(args: tool_args.editScriptArgs):

    try:
        with open(args.script_path, encoding='utf-8') as file:
            existing_contents = file.read()
    except UnicodeDecodeError as e:
        return f"Could not read {args.script_path} as UTF-8: {e}"

    if existing_contents == args.new_contents:
        return "No changes required; new contents are identical to the current file."

    syntax_error = _check_python_syntax(args.new_contents, args.script_path)
    if syntax_error:
        return syntax_error

    with open(args.script_path, 'w', encoding='utf-8', newline='\n') as file:
        file.write(args.new_contents)

    old_count = existing_contents.count('\n') + 1
    new_count = args.new_contents.count('\n') + 1
    return f"Replaced {args.script_path} ({old_count} -> {new_count} lines)."

@server.tool(description="Replace a 1-based, inclusive line range in a Python script under <protocol>/make/scripts. Use this for small, targeted edits. The edit is rejected if the result is not valid Python.")
def edit_protocol_script_lines(args: tool_args.editScriptLinesArgs):

    try:
        with open(args.script_path, encoding='utf-8') as file:
            lines = file.readlines()
    except UnicodeDecodeError as e:
        return f"Could not read {args.script_path} as UTF-8: {e}"

    if args.end_line > len(lines):
        return f"end_line {args.end_line} is out of range; {args.script_path} only has {len(lines)} lines."

    # Newline-terminate every replacement line so the edit can never glue itself
    # onto the following line (an empty replacement_text deletes the range).
    replacement_lines = [line + '\n' for line in args.replacement_text.splitlines()]

    new_lines = lines[:args.start_line - 1] + replacement_lines + lines[args.end_line:]

    # Preserve the file's original end-of-file convention: don't force a trailing
    # newline onto a file that didn't end with one when the edit touches the tail.
    original_ends_with_newline = bool(lines) and lines[-1].endswith('\n')
    if new_lines and not original_ends_with_newline and args.end_line == len(lines):
        new_lines[-1] = new_lines[-1].rstrip('\n')

    new_source = ''.join(new_lines)

    syntax_error = _check_python_syntax(new_source, args.script_path)
    if syntax_error:
        return syntax_error

    with open(args.script_path, 'w', encoding='utf-8', newline='\n') as file:
        file.write(new_source)

    # Show the updated region (with a little context) so the edit can be verified.
    region_start = args.start_line
    region_end = args.start_line + len(replacement_lines) - 1
    excerpt = _numbered_excerpt(new_lines, region_start - 3, region_end + 3)
    return (
        f"Replaced lines {args.start_line}-{args.end_line} of {args.script_path} "
        f"with {len(replacement_lines)} line(s). Updated region with context:\n{excerpt}"
    )

@server.tool(description="Read specific lines of a CSV")
def read_csv(args: tool_args.readCSVArgs):
    df = pandas.read_csv(args.csv_path, encoding="utf-8", encoding_errors="replace")
    return df.iloc[args.start:args.end].to_dict(orient='records')

@server.tool(description="Get CSV schema to make edits")
def get_csv_schema(args: tool_args.readCSVArgs):
    df = pandas.read_csv(args.csv_path, encoding="utf-8", encoding_errors="replace")
    return list(df.head(0))

@server.tool(description="Get indices of CSV rows that contain a specific string")
def search_for_string_in_csv(args: tool_args.searchCSVArgs):
    match_indices = set()
    df = pandas.read_csv(args.csv_path, encoding="utf-8", encoding_errors="replace")
    
    if not args.column_name:
        for column in df.iloc():

            if args.search_string.lower().strip() in str(column).lower():
                match_indices.add(column.name)
    else:
        try:
            for i, item in enumerate(df[args.column_name]):
                if args.search_string.lower().strip() in item.lower():
                    match_indices.add(i)
        except KeyError:
            return f"'{args.column_name}' is not a valid column name for the CSV at path {args.csv_path}"

    return f"Index matches: {match_indices}"

@server.tool(description="Change a specific CSV cell")
def edit_csv_cell(args: tool_args.editCSVArgs):
    df = pandas.read_csv(args.csv_path, encoding="utf-8", encoding_errors="replace")

    df.loc[args.row_index, args.column_name] = args.new_value

    df.to_csv(args.csv_path, index=False)

@server.tool(description="Find and replace all occurrences of a string in a CSV file")
def find_and_replace_in_csv(args: tool_args.findAndReplaceArgs):
    df = pandas.read_csv(args.csv_path, encoding="utf-8", encoding_errors="replace")

    df.replace(to_replace=args.old_value, value=args.new_value, inplace=True, regex=True)
    
    df.to_csv(args.csv_path, index=False)

    return f"Replaced {args.old_value} with {args.new_value}"


if __name__ == '__main__':
    server.run(transport="streamable-http")