async function send(mcpMethod, params, requestID=null, mcpSessionID=null){
    const access_token = sessionStorage.getItem('access_token');

    const body = {jsonrpc : "2.0", method: mcpMethod, "params": params};
    
    const mcpHeaders = new Headers();
    mcpHeaders.append("Content-Type", "application/json");
    mcpHeaders.append("Accept","application/json, text/event-stream");
    mcpHeaders.append("Authorization", `Bearer ${access_token}`);

    if(requestID!==null) body.id = requestID;
    if(mcpSessionID!==null) mcpHeaders.append('mcp-session-id',mcpSessionID);
    
    const res = await fetch(url, {
        method: "POST",
        headers: mcpHeaders,
        body: JSON.stringify(body)
    });

    // Notifications (no id) get 202 with no meaningful body — nothing to await.
    if (requestID === null) return { res, result: null };

    const contentType = res.headers.get("content-type") || "";

    // Plain JSON: the whole result is the body.
    if (contentType.includes("application/json")) {
        return { res, result: await res.json() };
    }

    if (contentType.includes("text/event-stream")){
        const text = await res.text();

        const lines = text.split(/\r?\n/);

        for (const line of lines) {
            if (!line.startsWith("data:")) continue;
            
            const msg = JSON.parse(line.slice(5).trim());
            
            if (msg.id === requestID) {
                return { res, result: msg };
            }
        }
    }
    

    return {res, result: null};
}

const url = "http://localhost:8000/mcp";

async function deployProtocol(protocol, fileContents, commitMessage, releaseNotes, isLatest){
    let id = 1;
    //initialize
    const init = await send(
        "initialize", {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "my-client", version: "1.0.0" }}, 
        id
    );

    if(!(init.res.ok)) {
        showMessage("Error: Could not connect to the server", "red");
        return;
    }
    showMessage("Connected to the server", "green");



    let mcpSessionID = init.res.headers.get('mcp-session-id');

    //initialized notification
    const initialized = await send("notifications/initialized", {}, null, mcpSessionID);

    if (!initialized.res.ok) {
        showMessage("Error: could not initialize", "red");
        return;
    }
    showMessage("Initialized", "green");

    id++;
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
        id, 
        mcpSessionID
    );

    if (get_protocol.result["isError"]){
        showMessage("Failed to retrieve protocol on server", "red");
        return;
    }
    showMessage("Retrieved protocol...", "green");

    //replace CSV files
    for (const [filename, contents] of Object.entries(fileContents)) {
        id++;
        let get_protocol = await send(
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
            id,
            mcpSessionID
        );

        if (get_protocol.result["isError"]){
            showMessage(`Failed to read file ${filename}. Please try again`, "red");
            return;
        }
        
    }

    showMessage("Files read succesfully", "green");
    id++;

    //build/save/release
    const buildSaveRelease = await send(
        "tools/call", {
            "name":"build_save_and_release_protocol",
            "arguments": {
                "args": {
                    "protocol_name": protocol,
                    "release_message" : commitMessage,
                    "release_notes" : releaseNotes,
                    "isLatest" : isLatest
                },
            }
        },
        id,
        mcpSessionID
    );

    if (buildSaveRelease.result["isError"]){
        showMessage(`Release failed: ${buildSaveRelease.result}`);
    }

    showMessage("Succesfully deployed protocol!");

}

window.deployProtocol = deployProtocol;