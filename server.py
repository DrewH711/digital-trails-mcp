from fastmcp import FastMCP, Context
from dotenv import load_dotenv
from os import getenv
from typing import Literal
import subprocess
import tool_args
import os
import shutil

load_dotenv("keys.env")

server = FastMCP(name="digital-trails-autodeploy", instructions="Use tools from this server to deploy a digital trails-based project such as Leia, Mindtrails-Movement, Mindtrails-Spanish, or UMA")

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
        
        # subprocess.run(f"gh auth login --with-token {pat}")
        subprocess.run(f"git clone {get_github_path(args.protocol_name)}")

        return f"Protocol '{args.protocol_name}' retrieved"
    
    except Exception as e:
        return f"Exception occurred: {e}"
    
    
@server.tool(description="Save all changes to a protocol")
async def save_protocol(args: tool_args.protocolArgs, ctx: Context):

    if not os.access(args.protocol_name, mode=0):
        return f"Protocol '{args.protocol_name}' not found. Please use `get_protocol` first."
    
    repo_dir = args.protocol_name

    # subprocess.run(["python", "make/scripts/sessions.py"], cwd=repo_dir)
    # subprocess.run(["python", "make/scripts/surveys.py"], cwd=repo_dir)
    # if os.access(f'{repo_dir}/make/scripts/resources.py', mode=0): subprocess.run(["python","make/scripts/resources.py"], cwd=repo_dir)

    src = f"{repo_dir}/make/~out"
    dst = f"{repo_dir}/src/flows"
    shutil.copytree(src, dst, dirs_exist_ok=True)
    print("files copied")

    # get git diff and create changenotes
    git_diff_bytes = subprocess.run(f"git diff", cwd=repo_dir, capture_output=True).stdout
    git_diff = bytes.decode(git_diff_bytes, "utf-8", errors="ignore")
    print("git diff recieved")

    release_notes_result = await ctx.sample(
        messages=f"Here is the git diff. Summarize the changes into release notes.\n {git_diff}",
        system_prompt="Provide a bulleted list of changes. Be brief",
        temperature=0.5,
        max_tokens=350
    )
    print("release notes recieved")

    release_notes = release_notes_result.text

    commit_message_result = await ctx.sample(
        messages = f"Here are some change notes: {release_notes}" 
        "Summarize these into a one-line commit message.",
        system_prompt="Be descriptive but brief",
        temperature=0.3,
        max_tokens=100
    )
    print("commit message recieved")

    # commit and push changes
    subprocess.run(['git', 'add', '-A'], cwd=repo_dir, check=True)
    print("git add done")
    subprocess.run(["git", "commit", "-m", f"{commit_message_result.text}", "-m", f"{release_notes}"], cwd=repo_dir, check=True)
    print('git commit done')
    subprocess.run(["git", "push"], cwd=repo_dir, check=True)
    print('git push done')
    

# @server.tool(description="Create and publish new release for a protocol. Always run `get_protocol` first to ensure existence")
async def release_protocol(args: tool_args.protocolArgs, ctx: Context):
    release_notes=""
    # ensure existence of protocol
    try:
        if not os.access(args.protocol_name, mode=0):
            return f"Protocol '{args.protocol_name}' not found. Please use `get_protocol` first."
    
    except Exception as e:
        return f"Exception occurred: {e}"

    # pull?


    # delete and regenerate `out` folder

    # create new release number and push release
    last_release_number_bytes = subprocess.run(f"gh release list --repo {get_owner_repo(args.protocol_name)} --limit 1 --json tagName --jq '.[0].tagName'", capture_output=True).stdout

    try:
        last_release_number = bytes.decode(last_release_number_bytes, 'utf-8')
        if(len(last_release_number)==0):
            last_release_number = "0.0.0"

    except UnicodeDecodeError:
        last_release_number = "0.0.0"

    print(f"last release={last_release_number}")


    release_number_result = await ctx.sample(
        messages=f"The previous release was numbered {last_release_number}. The release description are: {release_notes}. Based on the previous release number and description, give the new semantic versioning number. Normally, only the `patch` number should be incremented. If there are significant changes, you may increment the `minor` number. Never increment the `major` version number unless specifically instructed.",
        system_prompt="Only provide the semantic versioning number and nothing else.",
        temperature=0.05,
        max_tokens=5
    )

    new_release_number = release_number_result.text

    print(f"next release={new_release_number}")

    subprocess.run(["git", 'tag', '-a' ,f'{new_release_number}', '-m ',f'{release_notes}'])
    subprocess.run(["git", "push", "origin", f"{new_release_number}"])
    


if __name__ == '__main__':
    server.run(transport="streamable-http")