from fastmcp import FastMCP, Context
from dotenv import load_dotenv
from os import getenv
import subprocess
import tool_args
import os
import shutil
import requests

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
    
    
@server.tool(description="Save all changes to a protocol")
async def save_protocol(args: tool_args.protocolArgs, ctx: Context):

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
async def save_and_release_protocol(args: tool_args.protocolArgs, ctx: Context):
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
    
    # must use GitHub REST API to publish releases because it cannot be done via command line
    requests.post(
        f"https://api.github.com/repos/{get_owner_repo(args.protocol_name)}/releases",
        headers={
            "Authorization": f"Bearer {getenv('GITHUB_PAT')}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "tag_name": new_release_number,
            "name": new_release_number,
            "body": release_notes,
        },
    ).raise_for_status()
    

if __name__ == '__main__':
    server.run(transport="streamable-http")