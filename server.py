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
        
        subprocess.run(f"git clone {get_github_path(args.protocol_name)}")

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
        await ctx.report_progress(progress=25,total=100)
        subprocess.run(["python", "make/scripts/surveys.py"], cwd=repo_dir, check=True)
        await ctx.report_progress(progress=30,total=100)
        if os.access(f'{repo_dir}/make/scripts/resources.py', mode=0): subprocess.run(["python","make/scripts/resources.py"], cwd=repo_dir)

        src = f"{repo_dir}/make/~out"
        dst = f"{repo_dir}/src/flows"
        shutil.copytree(src, dst, dirs_exist_ok=True)
        await ctx.report_progress(progress=40,total=100)

    # get git diff and create changenotes
    git_diff_bytes = subprocess.run(f"git diff", cwd=repo_dir, capture_output=True, check=True).stdout
    git_diff = bytes.decode(git_diff_bytes, "utf-8", errors="ignore")

    release_notes_result = await ctx.sample(
        messages=f"Here is the git diff. Summarize the changes into release notes.\n {git_diff}",
        system_prompt="Provide a bulleted list of changes. Be brief",
        temperature=0.5,
        max_tokens=350
    )
    await ctx.report_progress(progress=60,total=100)

    release_notes = release_notes_result.text

    await ctx.set_state(key = 'release notes', value=release_notes)

    commit_message_result = await ctx.sample(
        messages = f"Here are some change notes: {release_notes}" 
        "Summarize these into a one-line commit message.",
        system_prompt="Be descriptive but brief",
        temperature=0.3,
        max_tokens=50
    )

    await ctx.report_progress(progress=80,total=100)

    # commit and push changes
    subprocess.run(['git', 'add', '-A'], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", f"{commit_message_result.text}", "-m", f"{release_notes}"], cwd=repo_dir, check=True)
    await ctx.report_progress(progress=90,total=100)
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

@server.tool(description="List file paths from a protocol")
def get_protocol_csv_list(args: tool_args.protocolArgs):
    # returns a list of paths to python scripts and CSVs
    # There are far too many JSON files to be useful, and they will be regenerated by the scripts on release anyway
    available_files = []
    for root, dirs, files in os.walk(f"./{args.protocol_name}/make/CSV"):
        for file in files:
            file_path = os.path.join(root, file)
            if not file_path.__contains__("image"):
                available_files.append(file_path)

    return available_files

@server.tool(description="Get file contents from a protocol")
def get_file_contents(args: tool_args.readProtocolArgs):

    file_contents = {}

    for path in args.file_paths:

        with open(path, encoding="utf-8", errors="replace") as file:
            file_contents[path] = file.read()

    return file_contents

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

    df.to_csv(args.csv_path)

@server.tool(description="Find and replace all occurrences of a string in a CSV file")
def find_and_replace_in_csv(args: tool_args.findAndReplaceArgs):
    df = pandas.read_csv(args.csv_path, encoding="utf-8", encoding_errors="replace")

    df.replace(to_replace=args.old_value, value=args.new_value, inplace=True, regex=True)
    
    df.to_csv(args.csv_path)

    return f"Replaced {args.old_value} with {args.new_value}"


@server.tool(description="Provides example JSON for flow screens with different input elements. Use this resource when generating JSON")
def get_flow_screen_json_examples() -> str:

    scheduler_element_json = json.dumps({
        "header_text": "",
        "header_icon": "assets/subtitle.png",
        "elements": [
            {
                "type": "Text",
                "text": "You are encouraged to complete 4 short surveys tomorrow, 2 of which can be at a pre-scheduled time. Thinking ahead to your day tomorrow, are there specific times you would like to receive a notification to complete a ~5 minute program to help manage a stressful or upsetting situation?"
            },
            {
                "type": "Scheduler",
                "days_ahead": 1,
                "action": "flow://flows/session",
                "count": 1,
                "message": "It's time for your session."
            }
        ]
    })

    slider_element_json = json.dumps(
            {
        "header_text": "",
        "header_icon": "assets/subtitle.png",
        "elements": [
            {
                "type": "Text",
                "text": "I was able to manage my emotions today."
            },
            {
                "type": "Text",
                "Text": "1. Not at all effectively\n\n7. Very effectively"
            },
            {
                "type": "Slider",
                "min": 1,
                "max": 7,
                "others": [],
                "name": "eodmanagefeelings",
                "variable_name": "eodmanagefeelings"
            }
        ]
    }
    )

    buttons_element_json = json.dumps(
            {
        "header_text": "",
        "header_icon": "assets/subtitle.png",
        "elements": [
            {
                "type": "Text",
                "text": "How would you describe your current social context?"
            },
            {
                "type": "Buttons",
                "buttons": [
                    "0::Alone - not around any other people",
                    "1::Around other people that I am not actively interacting with (e.g., eating lunch in a crowded cafeteria but sitting alone)",
                    "2::Around other people that I am actively interacting with (e.g., studying with a group of friends)"
                ],
                "ColumnCount": 1,
                "name": "socialcontext",
                "variable_name": "socialcontext"
            }
        ]
    }
    )

    buttons_element_with_condition_json = json.dumps(
            {
        "header_text": "",
        "header_icon": "assets/subtitle.png",
        "elements": [
            {
                "type": "Text",
                "text": "How vividly did you imagine the situation?"
            },
            {
                "type": "Buttons",
                "buttons": [
                    "0::Not at all vivid",
                    "1::Somewhat vivid",
                    "2::Moderately vivid",
                    "3::Very vivid",
                    "4::Totally vivid",
                    "5::Prefer not to answer"
                ],
                "ColumnCount": 1,
                "name": "imagery_vivid"
            }
        ],
        "condition": [
            "interest",
            "=",
            0,
            "&&",
            "preanxious",
            "<",
            3
        ]
    }
    )

    return f"JSON with scheduler input: {scheduler_element_json}\n JSON with slider input: {slider_element_json}\n JSON with buttons: {buttons_element_json}\n JSON with buttons and a condition: {buttons_element_with_condition_json}"
    
    

if __name__ == '__main__':
    server.run(transport="streamable-http")