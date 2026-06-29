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
from utils import _check_python_syntax, _numbered_excerpt, _validate_semver

load_dotenv("keys.env")

server = FastMCP(name="digital-trails-autodeploy", instructions="Use tools from this server to deploy a digital trails-based project such as Leia, Mindtrails-Movement, Mindtrails-Spanish, UMA, or github-mcp-test")

def get_github_path(protocol: tool_args.available_protocols) -> str:
    if protocol in ["mindtrails_movement", "mindtrails_spanish"]:
        return f"https://github.com/TeachmanLab/{protocol}"
    else:
        return f"https://github.com/digital-trails/{protocol}"
    
def get_owner_repo(protocol: tool_args.available_protocols) -> str:
    if protocol in ["mindtrails_movement", "mindtrails_spanish"]:
        return f"TeachmanLab/{protocol}" 
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
        raise Exception(f"An unexpected exception occurred while retrieving protocol. Ensure that the protocol name is valid. Error msg: {e}")
    
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
    
    
@server.tool(description="Build a protocol to prepare for a save and/or release")
async def build_protocol(args: tool_args.protocolArgs, ctx: Context = CurrentContext()):

    if not os.access(args.protocol_name, mode=0):
        return f"Protocol '{args.protocol_name}' not found. Please use `get_protocol` first."
    
    repo_dir = f'{os.getcwd()}/{args.protocol_name}'

    try:
        subprocess.run(["python", "make/scripts/sessions.py"], cwd=repo_dir, check=True)
        await ctx.report_progress(progress=40,total=100)
        subprocess.run(["python", "make/scripts/surveys.py"], cwd=repo_dir, check=True)
        await ctx.report_progress(progress=45,total=100)
        if os.access(f'{repo_dir}/make/scripts/resources.py', mode=0): subprocess.run(["python","make/scripts/resources.py"], cwd=repo_dir, check=True)

        src = f"{repo_dir}/make/~out"
        dst = f"{repo_dir}/src/flows"
        shutil.copytree(src, dst, dirs_exist_ok=True)
        await ctx.report_progress(progress=60,total=100)
    
        # get git diff and create changenotes
        git_diff_bytes = subprocess.run( ['git','diff','--diff-algorithm','minimal','--','make/CSV', 'make/scripts', ':(exclude)src/flows', ':(exclude)make/~out'], cwd=repo_dir, capture_output=True, check=True).stdout
        git_diff = bytes.decode(git_diff_bytes, "utf-8", errors="ignore")

        await ctx.set_state(key=f'release notes {args.protocol_name}', value='')

        release_notes_result = await ctx.sample(
            messages=f"Review this git diff and write concise and accurate release notes: {git_diff}",
            system_prompt="Provide a bulleted list. Be brief",
            temperature=0.5,
            max_tokens=350
        )
    
        release_notes = release_notes_result.text

        await ctx.set_state(key = f'release notes {args.protocol_name}', value = release_notes)
        await ctx.report_progress(progress=75,total=100)


        commit_message_result = await ctx.sample(
            messages = f"Here are some change notes: {release_notes}" 
            "Summarize these into a one-line commit message.",
            system_prompt="Be descriptive but brief",
            temperature=0.3,
            max_tokens=50
        )

        await ctx.set_state(key = f'commit message {args.protocol_name}', value = commit_message_result.text)

        await ctx.report_progress(progress=100,total=100)

        return f"Built {args.protocol_name} succesfully"

    except subprocess.CalledProcessError as e:
        raise Exception(f"Build failed due to subprocess error. Error message: {e}")
    except Exception as e:
        raise Exception(f"Build failed due to unexpected exception. Error message: {e}")
    
@server.tool(description="Save protocol without releasing. Default to this over save and release. Save after building and before releasing.")
async def save_protocol(args: tool_args.protocolArgs, ctx: Context = CurrentContext()):
    
    # commit and push changes
    repo_dir = f'{os.getcwd()}/{args.protocol_name}'

    if not os.access(repo_dir, mode=0):
        return f"Protocol '{args.protocol_name}' not found. Please use `get_protocol` first."

    commit_message = await ctx.get_state(f'commit message {args.protocol_name}')
    release_notes = await ctx.get_state(f'release notes {args.protocol_name}')

    if not commit_message or not release_notes:
        return "No commit message or release notes found. Run `build_protocol` before saving."
    
    try:

        subprocess.run(['git','switch','agent-testing'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'add', '-A'], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", f"{commit_message}", "-m", f"{release_notes}"], cwd=repo_dir, check=True)
        subprocess.run(["git", "push"], cwd=repo_dir, check=True)

    except subprocess.SubprocessError as e:
        raise Exception(f"Failed to save due to subprocess error. Error message: {e}")

    return(f"Successfuly saved {args.protocol_name}")

@server.tool(description="Create a new release version of this protocol and push it to GitHub. Always build and save first")
async def release_protocol(args: tool_args.protocolArgs, ctx: Context = CurrentContext()):
    # create new release number and push release
    try:
        last_release_number_bytes = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=args.protocol_name,
            capture_output=True,
            check=True
        ).stdout

        last_release_number = bytes.decode(last_release_number_bytes, 'utf-8').strip()
        if(len(last_release_number)==0):
            last_release_number = "0.0.0"

    except UnicodeDecodeError as e:
        raise Exception(f"Release failed due to unicode decoding error. Error msg: {e}")

    except subprocess.CalledProcessError:
        # `git describe` exits non-zero when the repo has no tags yet; treat this
        # as the very first release rather than a failure.
        last_release_number = "0.0.0"

    except subprocess.SubprocessError as e:
        raise Exception(f"Release failed due to subprocess error while attempting to get previous release number. Error: {e}")

    release_notes = await ctx.get_state(f'release notes {args.protocol_name}')

    release_number_result = await ctx.sample(
        messages=f"The previous release was numbered {last_release_number}. The release notes are: {release_notes}. Based on the previous release number and description, give the new semantic versioning number. Normally, only the `patch` number should be incremented. If there are significant changes, you may increment the `minor` number. Never increment the `major` version number unless specifically instructed.",
        system_prompt="Only provide the semantic versioning number and nothing else.",
        temperature=0,
        max_tokens=5
    )

    new_release_number, semver_validation_error = _validate_semver(release_number_result.text) #type: ignore
    if semver_validation_error:
        raise Exception(f"Release failed due to invalid semantic versioning number. Error: {semver_validation_error}")

    isPrerelease = await ctx.elicit(
        message="Mark as prerelease?",
        response_type=tool_args.latestOrPrerelease
    )

    # must use GitHub REST API to publish releases because it cannot be done via command line
    try:
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

    except requests.HTTPError as e:
        raise Exception(f"An error occurred while publishing release to GitHub. Error msg: {e}")

    return f"{args.protocol_name} released successfully"



@server.tool(description="Create and publish new release for a protocol")
async def build_save_and_release_protocol(args: tool_args.protocolArgs):

    if not os.access(args.protocol_name, mode=0):
        return f"Protocol '{args.protocol_name}' not found. Please use `get_protocol` first."
    
    # A failing sub-tool raises ToolError out of `call_tool` (it does not return a
    # ToolResult with is_error=True), so each stage is wrapped to short-circuit
    # with a clear message instead of falsely reporting success.
    try:
        await server.call_tool(name="build_protocol", arguments={'args':tool_args.protocolArgs(protocol_name=args.protocol_name)})
    except Exception as e:
        return f"Build failed for {args.protocol_name}. Error: {e}"

    try:
        await server.call_tool(name="save_protocol", arguments={'args':tool_args.protocolArgs(protocol_name=args.protocol_name)})
    except Exception as e:
        return f"Save failed for {args.protocol_name}. Error: {e}"

    try:
        await server.call_tool(name="release_protocol", arguments={'args':tool_args.protocolArgs(protocol_name=args.protocol_name)})
    except Exception as e:
        return f"Release failed for {args.protocol_name}. Error: {e}"

    return f"Successfully built, saved, and released {args.protocol_name}"

# return lists of paths to python scripts and CSVs
# There are far too many JSON files to be useful, and they will be regenerated by the scripts on release anyway
@server.tool(description="List file paths from a protocol")
def get_protocol_csv_list(args: tool_args.protocolArgs):

    if not os.access(args.protocol_name, mode=0): return f"Protocol {args.protocol_name} not found. Use `get_protocol` tool first."
    path = f"./{args.protocol_name}/make/CSV/"
    return [(path+file) for file in os.listdir(path) if (file.endswith(".csv") and "image" not in file)]

@server.tool(description="View list of available python scripts")
def get_protocol_python_script_list(args: tool_args.protocolArgs):
    if not os.access(args.protocol_name, mode=0): return f"Protocol {args.protocol_name} not found. Use `get_protocol` tool first."
    path = f"./{args.protocol_name}/make/scripts/"
    return [(path+file) for file in os.listdir(path) if (file.endswith(".py") and "image" not in file)]

@server.tool(description="View list of special json files such as instructions")
def get_protocol_special_json(args: tool_args.protocolArgs):
    if not os.access(args.protocol_name, mode=0): return f"Protocol {args.protocol_name} not found. Use `get_protocol` tool first."
    
    # get json from /src, then /flows
    file_paths = []

    src_path = f"./{args.protocol_name}/src/"
    for file in os.listdir(src_path):
        if file.endswith(".json"): file_paths.append(src_path + file)

    flows_path = src_path + "flows/"
    for file in os.listdir(flows_path):
        if file.endswith(".json"): file_paths.append(flows_path + file)

    return file_paths

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