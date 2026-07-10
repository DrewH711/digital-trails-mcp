from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext
from fastmcp.server.auth.providers.github import GitHubProvider
from dotenv import load_dotenv
import subprocess
import tool_args
import os
import shutil
import requests
import pandas
import utils
import pygit2 as git
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# add spaces and comments

load_dotenv("keys.env")

userpass = git.UserPass(
    username ="Digital Trails Auto-Commit Bot",
    password = os.getenv('LEIA_PAT') # type: ignore
)

GITHUB_CREDENTIALS = git.RemoteCallbacks(credentials=userpass)
ALLOW_LIST = os.getenv('ALLOW_LIST',{})
client_secret = os.getenv('OAUTH_CLIENT_SECRET',"")

auth_provider = GitHubProvider(
    client_id="Ov23likbvFkZTbNxc8at",
    client_secret=client_secret,
    base_url=os.getenv('BASE_URL','about:blank')
)

server = FastMCP(name="digital-trails-autodeploy", instructions="Use tools from this server to deploy a digital trails-based project such as Leia, Mindtrails-Movement, Mindtrails-Spanish, UMA, or github-mcp-test", auth=auth_provider)

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET", "DELETE"],
        allow_headers=[
            "mcp-protocol-version",
            "mcp-session-id",
            "Authorization",
            "Content-Type",
        ],
        expose_headers=["mcp-session-id"],
    )
]

server.disable(tags={'disable'})

@server.tool(description="Clone a protocol into the current directory so it can be read and modified")
def get_protocol(args: tool_args.protocolArgs):

    utils.validate_user()

    try:
        url = utils.get_github_url(args.protocol_name)
        git.clone_repository(url = url, path = f"./{args.protocol_name}", checkout_branch="main", depth=1)

    except ValueError:
        return f"Protocol '{args.protocol_name}' retrieved"

    except git.GitError as e:
        raise Exception(f"Git encountered an error: {e}")
    
    except Exception as e:
        raise Exception(f"An unexpected exception occurred while retrieving protocol. Ensure that the protocol name is valid. Error msg: {e}")

    return f"Protocol '{args.protocol_name}' retrieved"
    
@server.tool(description="Ask the user to specify the protocol to perform actions on", tags={'disable'})
async def specify_protocol(ctx: Context = CurrentContext()):
    utils.validate_user()
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
async def build_protocol(args: tool_args.buildSaveReleaseArgs, ctx: Context = CurrentContext()):
    utils.validate_user()
    
    repo_dir = f'{os.getcwd()}/{args.protocol_name}'

    try:
        repo = git.Repository(path = repo_dir)

    except git.GitError:
        raise Exception(f"Protocol not found at path {repo_dir}. Use `get_protocol` first.")

    if(args.release_message and args.release_notes):
        await ctx.set_state(key=f'release notes {args.protocol_name}', value=args.release_notes)
        await ctx.set_state(key = f'commit message {args.protocol_name}', value = args.release_message)

    else:
        try:    
            # get git diff and create changenotes
            diff = repo.diff()

            git_diff = ""

            for obj in diff:
                if type(obj) == git.Patch:
                    for hunk in obj.hunks:
                        for line in hunk.lines:
                            # The new_lineno represents the new location of the line after the patch. If it's -1, the line has been deleted.
                            if line.new_lineno == -1: 
                                git_diff += f"[removal line {line.old_lineno}] {line.content.strip()}\n"
                            # Similarly, if a line did not previously have a place in the file, it's been added fresh. 
                            if line.old_lineno == -1: 
                                git_diff += f"[addition line {line.new_lineno}] {line.content.strip()}\n" 

            await ctx.set_state(key=f'release notes {args.protocol_name}', value='')

            release_notes_result = await ctx.sample(
                messages=f"Review this git diff and write concise and accurate release notes: {git_diff[0:10000]} (showing first 10000 characters)",
                system_prompt="Provide a bulleted list. Be brief",
                temperature=0.5,
                max_tokens=350
            )
        
            release_notes = release_notes_result.text

            await ctx.set_state(key = f'release notes {args.protocol_name}', value = release_notes)

            commit_message_result = await ctx.sample(
                messages = f"Here are some change notes: {release_notes}" 
                "Summarize these into a one-line commit message.",
                system_prompt="Be descriptive but brief",
                temperature=0.3,
                max_tokens=50
            )

            await ctx.set_state(key = f'commit message {args.protocol_name}', value = commit_message_result.text)

        except ValueError as e:
            e.add_note("Build failed because client cannot automatically generate release notes. Notes must be entered manually")
            raise e
        
        except Exception as e:
            e.add_note("Build failed due to unexpected error")
            raise e
        
    try:
        # Build JSON last so git diff is not too long          
        subprocess.run(["python", "make/scripts/sessions.py"], cwd=repo_dir, check=True)
        subprocess.run(["python", "make/scripts/surveys.py"], cwd=repo_dir, check=True)
        if os.access(f'{repo_dir}/make/scripts/resources.py', mode=0): subprocess.run(["python","make/scripts/resources.py"], cwd=repo_dir, check=True)

        src = f"{repo_dir}/make/~out"
        dst = f"{repo_dir}/src/flows"
        shutil.copytree(src, dst, dirs_exist_ok=True)

        return f"Built {args.protocol_name} succesfully"

    except subprocess.CalledProcessError as e:
        raise Exception(f"Build failed due to subprocess error. Error message: {e}")
    except git.GitError as e:
        raise Exception(f"Build failed due to error while generating Git diff. Error message: {e}")
    except Exception as e:
        raise Exception(f"Build failed due to unexpected exception. Error message: {e}")
    
@server.tool(description="Save protocol without releasing. Default to this over save and release. Save after building and before releasing.")
async def save_protocol(args: tool_args.buildSaveReleaseArgs, ctx: Context = CurrentContext()):
    utils.validate_user()
    
    # commit and push changes
    repo_dir = f'{os.getcwd()}/{args.protocol_name}'

    try:
        repo = git.Repository(path = repo_dir)

    except git.GitError:
        raise Exception(f"Protocol not found at path {repo_dir}. Use `get_protocol` first.")

    if(args.release_notes and args.release_message):
        commit_message = args.release_message
        release_notes = args.release_notes

    else:
        commit_message = await ctx.get_state(f'commit message {args.protocol_name}')
        release_notes = await ctx.get_state(f'release notes {args.protocol_name}')

        if not commit_message or not release_notes:
            raise Exception("No commit message or release notes found. Run `build_protocol` before saving.")
    
    try:

        # git add -a
        index = repo.index
        index.add_all()
        index.write()

        # git commit
        ref = repo.head.name
        author = git.Signature(name = "Digital Trails Auto-Commit Bot", email="placeholder@digitaltrails.org")
        committer = git.Signature(name = "Digital Trails Auto-Commit Bot", email="placeholder@digitaltrails.org")

        message = f"""{commit_message}

        {release_notes}
        """

        tree = index.write_tree()
        parents = [repo.head.target]

        commit = repo.create_commit(ref, author, committer, message, tree, parents)

        # git push
        remote = repo.remotes["origin"]
        remote.push(['refs/heads/main'], callbacks=GITHUB_CREDENTIALS)

    except git.GitError as e:
        raise RuntimeError(f"Failed to save due to git error.") from e

    return(f"Successfuly saved {args.protocol_name}")

@server.tool(description="Create a new release version of this protocol and push it to GitHub. Always build and save first")
async def release_protocol(args: tool_args.buildSaveReleaseArgs, ctx: Context = CurrentContext()):
    utils.validate_user()
    # create new release number and push release
    try:
        releases_response = requests.get(
            f"https://api.github.com/repos/{utils.get_repo_owner(args.protocol_name)}/releases",
            headers={
                "Authorization": f"Bearer {os.getenv('LEIA_PAT')}",
                "Accept": "application/vnd.github+json",
            },
            params={"per_page": 1},
        )
        releases_response.raise_for_status()
        releases = releases_response.json()

        last_release_number = releases[0]["tag_name"].strip() if releases else "0.0.0"
        if len(last_release_number) == 0:
            last_release_number = "0.0.0"

    except requests.HTTPError as e:
        raise RuntimeError("Release failed while fetching the previous release number from GitHub") from e
    
    except Exception as e:
        raise RuntimeError("Release failed due to unexpected `requests` error.") from e

    if args.release_notes:
        release_notes = args.release_notes
    else:
        release_notes = await ctx.get_state(f'release notes {args.protocol_name}')

    new_release_number = utils.increment_tag(last_release_number)

    # must use GitHub REST API to publish releases because it cannot be done via command line
    try:
        requests.post(
            f"https://api.github.com/repos/{utils.get_repo_owner(args.protocol_name)}/releases",
            headers={
                "Authorization": f"Bearer {os.getenv('LEIA_PAT')}",
                "Accept": "application/vnd.github+json",
            },
            json={
                "tag_name": new_release_number,
                "name": new_release_number,
                "target_commitish" : "main",
                "body": release_notes,
                "prerelease": not args.isLatest
            },
        ).raise_for_status()

    except requests.HTTPError as e:
        raise Exception(f"An error occurred while publishing release to GitHub. Error msg: {e}")
    
    except Exception as e:
        raise RuntimeError("Release failed due to unexpected `requests` error.") from e

    return f"{args.protocol_name} released successfully"



@server.tool(description="Create and publish new release for a protocol")
async def build_save_and_release_protocol(args: tool_args.buildSaveReleaseArgs):
    utils.validate_user()

    print(f"""
    protocol_name: {args.protocol_name}
    release_message: {args.release_message}
    release_notes: {args.release_notes}
    isLatest: {args.isLatest}
          """)
    
    if not os.access(args.protocol_name, mode=0):
        return f"Protocol '{args.protocol_name}' not found. Please use `get_protocol` first."
    
    # A failing sub-tool raises ToolError out of `call_tool` (it does not return a
    # ToolResult with is_error=True), so each stage is wrapped to short-circuit
    # with a clear message instead of falsely reporting success.
    try:
        await server.call_tool(name="build_protocol", arguments={'args':args})
        print('build done')
    except Exception as e:
        return f"Build failed for {args.protocol_name}. Error: {e}"

    try:
        await server.call_tool(name="save_protocol", arguments={'args':args})
        print('saved')
    except Exception as e:
        return f"Save failed for {args.protocol_name}. Error: {e}"

    try:
        await server.call_tool(name="release_protocol", arguments={'args':args})
        print('released!')
    except Exception as e:
        return f"Release failed for {args.protocol_name}. Error: {e}"

    return f"Successfully built, saved, and released {args.protocol_name}"

# return lists of paths to python scripts and CSVs
# There are far too many JSON files to be useful, and they will be regenerated by the scripts on release anyway
@server.tool(description="List file paths from a protocol",tags={'disable'})
def get_protocol_csv_list(args: tool_args.protocolArgs):

    if not os.access(args.protocol_name, mode=0): return f"Protocol {args.protocol_name} not found. Use `get_protocol` tool first."
    path = f"./{args.protocol_name}/make/CSV/"
    return [(path+file) for file in os.listdir(path) if (file.endswith(".csv") and "image" not in file)]

@server.tool(description="View list of available python scripts",tags={'disable'})
def get_protocol_python_script_list(args: tool_args.protocolArgs):
    if not os.access(args.protocol_name, mode=0): return f"Protocol {args.protocol_name} not found. Use `get_protocol` tool first."
    path = f"./{args.protocol_name}/make/scripts/"
    return [(path+file) for file in os.listdir(path) if (file.endswith(".py") and "image" not in file)]

@server.tool(description="View list of special json files such as instructions",tags={'disable'})
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

@server.tool(description="Replace the contents of an EXISTING CSV file in a protocol's make/CSV directory with uploaded text. Match-existing-names-only: an upload whose file_name has no matching file in the directory is rejected. Used by the web portal to swap in user-supplied CSVs before a build.")
def swap_csv(args: tool_args.swapCSVArgs):

    utils.validate_user()
    
    if not os.access(args.protocol_name, mode=0):
        return f"Protocol '{args.protocol_name}' not found. Please use `get_protocol` first."

    csv_dir = f"./{args.protocol_name}/make/CSV"
    target = os.path.join(csv_dir, args.file_name)

    # Match-existing-names-only: never create a new file from an upload, so a
    # mistyped name surfaces as an error instead of a stray CSV in the build.
    if not os.path.isfile(target):
        raise Exception(
            f"'{args.file_name}' does not match any existing CSV in {csv_dir}. "
            f"Upload rejected (match-existing-names-only)."
        )

    # newline="" so the uploaded file's own line endings are preserved verbatim.
    with open(target, "w", encoding="utf-8", newline="") as file:
        file.write(args.content)

    return f"Swapped {args.file_name} ({len(args.content)} characters written)"

@server.tool(description="Get file contents from a protocol", tags={'disable'})
def get_file_contents(args: tool_args.readProtocolArgs):

    file_contents = {}

    for path in args.file_paths:

        with open(path, encoding="utf-8", errors="replace") as file:
            file_contents[path] = file.read()

    return file_contents

@server.tool(description="Replace the entire contents of a Python script under <protocol>/make/scripts. The edit is rejected if the result is not valid Python. Prefer edit_protocol_script_lines for small, targeted changes.", tags={'disable'})
def edit_protocol_script(args: tool_args.editScriptArgs):

    try:
        with open(args.script_path, encoding='utf-8') as file:
            existing_contents = file.read()
    except UnicodeDecodeError as e:
        return f"Could not read {args.script_path} as UTF-8: {e}"

    if existing_contents == args.new_contents:
        return "No changes required; new contents are identical to the current file."

    syntax_error = utils._check_python_syntax(args.new_contents, args.script_path)
    if syntax_error:
        return syntax_error

    with open(args.script_path, 'w', encoding='utf-8', newline='\n') as file:
        file.write(args.new_contents)

    old_count = existing_contents.count('\n') + 1
    new_count = args.new_contents.count('\n') + 1
    return f"Replaced {args.script_path} ({old_count} -> {new_count} lines)."

@server.tool(description="Replace a 1-based, inclusive line range in a Python script under <protocol>/make/scripts. Use this for small, targeted edits. The edit is rejected if the result is not valid Python.", tags={'disable'})
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

    syntax_error = utils._check_python_syntax(new_source, args.script_path)
    if syntax_error:
        return syntax_error

    with open(args.script_path, 'w', encoding='utf-8', newline='\n') as file:
        file.write(new_source)

    # Show the updated region (with a little context) so the edit can be verified.
    region_start = args.start_line
    region_end = args.start_line + len(replacement_lines) - 1
    excerpt = utils._numbered_excerpt(new_lines, region_start - 3, region_end + 3)
    return (
        f"Replaced lines {args.start_line}-{args.end_line} of {args.script_path} "
        f"with {len(replacement_lines)} line(s). Updated region with context:\n{excerpt}"
    )

@server.tool(description="Read specific lines of a CSV", tags={'disable'})
def read_csv(args: tool_args.readCSVArgs):
    df = pandas.read_csv(args.csv_path, encoding="utf-8", encoding_errors="replace")
    return df.iloc[args.start:args.end].to_dict(orient='records')

@server.tool(description="Get CSV schema to make edits", tags={'disable'})
def get_csv_schema(args: tool_args.readCSVArgs):
    df = pandas.read_csv(args.csv_path, encoding="utf-8", encoding_errors="replace")
    if "LEIA Interventions, Resources, and Tips - Long Scenarios.csv" in args.csv_path: return list(df.head(1)) # This particular file is weird
    return list(df.head(0))

@server.tool(description="Get indices of CSV rows that contain a specific string", tags={'disable'})
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

@server.tool(description="Change a specific CSV cell", tags={'disable'})
def edit_csv_cell(args: tool_args.editCSVArgs):

    header = get_csv_schema(args=tool_args.readCSVArgs(protocol_name=args.protocol_name, csv_path=args.csv_path))

    if args.column_name not in header:
        raise Exception(f"Edit failed. {args.column_name} is not a valid column in this file. Check spelling and capitalization")

    try:
        df = pandas.read_csv(args.csv_path, encoding="utf-8", encoding_errors="replace")

        df.loc[args.row_index, args.column_name] = args.new_value

        df.to_csv(args.csv_path, index=False)

    except Exception as e:
        raise Exception(f"Unexpected exception encountered while editing CSV. Error msg: {e}")

    return f"Sucessfully changed row {args.row_index} of {args.column_name} to {args.new_value}"

@server.tool(description="Find and replace all occurrences of a string in a CSV file", tags={'disable'})
def find_and_replace_in_csv(args: tool_args.findAndReplaceArgs):

    header = get_csv_schema(args=tool_args.readCSVArgs(protocol_name=args.protocol_name, csv_path=args.csv_path))

    df = pandas.read_csv(args.csv_path, encoding="utf-8", encoding_errors="replace")

    df.replace(to_replace=args.old_value, value=args.new_value, inplace=True, regex=True)

    df.to_csv(args.csv_path, index=False, header=['' if ("Unnamed:" in str(h)) else str(h) for h in header])

    return f"Replaced {args.old_value} with {args.new_value}"


if __name__ == '__main__':
    server.run(transport="streamable-http", middleware=middleware, host='0.0.0.0', port=8000)