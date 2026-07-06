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

document.getElementById("fileProtocolForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const protocol = document.getElementById("protocol").value;
    // initialize

    const init = await send(
        "initialize", {

        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "my-client", version: "1.0.0" }}, 
        1
    );

    let mcpSessionID = init.headers.get('mcp-session-id');
    console.log(`mcp session ID recieved successfully: ${mcpSessionID}`);

    const initialized = await send("notifications/initialized", {}, null, mcpSessionID);

    if (initialized.ok) console.log("initialized notification sent");
    else console.log("initialized notification failed")

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

    if (get_protocol.ok) console.log("success i think");
    console.log(`body: ${get_protocol.body}`)

    // replace CSV files

    // Release
    
    }

)