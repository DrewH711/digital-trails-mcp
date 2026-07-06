async function send(mcpMethod, params, requestID=null, mcpSessionID=null){

    const body = {jsonrpc : "2.0", method: mcpMethod, "params": params};
    
    const mcpHeaders = new Headers();
    mcpHeaders.append("Content-Type", "application/json");
    mcpHeaders.append("Accept","application/json, text/event-stream");

    if(requestID!==null) body.id = requestID;
    if(mcpSessionID!==null) mcpHeaders.append('mcp-session-id',mcpSessionID);
    
    mcpHeaders.forEach((val, key) => {console.log(`${key} : ${val}`);})
    console.log(`${JSON.stringify(body)}`);
    
    const res = await fetch(url, {
        method: "POST",
        headers: mcpHeaders,
        body: JSON.stringify(body)
    });

    return res;
}

const url = "http://localhost:8000/mcp";

async function deployProtocol(protocol, files){

    //initialize
    const init = await send(
        "initialize", {

        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "my-client", version: "1.0.0" }}, 
        1
    );

    let mcpSessionID = init.headers.get('mcp-session-id');
    console.log(`mcp session ID recieved successfully: ${mcpSessionID}`);

    //initialized notification
    const initialized = await send("notifications/initialized", {}, null, mcpSessionID);

    if (initialized.ok) console.log("initialized notification sent");
    else console.log("initialized notification failed")

    //ensure protocol_existence
    const get_protocol = await send(
        "tools/call", {
            "name":"get_protocol",
            "arguments": {
                "args":{
                    "protocol_name":protocol
                }
            }
        }, 
        2, 
        mcpSessionID
    );

    //replace CSV files
    for (const [filename, contents] of Object.entries(fileContents)) {

        await send(
            "tools/call", {
                "name":"swap_csv",
                "arguments": {
                    "args":{
                        "protocol_name":protocol,
                        "file_name":filename,
                        "content":contents
                    }
                }
            },
            3,
            mcpSessionID
        );
    }

    //build/save/release

    const buildSaveRelease = await send(
        "tools/call", {
            "name":"build_save_and_release_protocol",
            "arguments": {
                "args": {
                    "protocol_name":protocol
                }
            }
        },
        4,
        mcpSessionID
    );

    if(buildSaveRelease.ok){
        console.log(`successfully built and released ${protocol}`)
        window.clearMessage();
        window.showMessage("Successfully deployed", "green");
    }

}

window.deployProtocol = deployProtocol;