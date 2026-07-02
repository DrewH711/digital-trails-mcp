document.getElementById("fileProtocolForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const eventSource = new EventSource("http://localhost:8000/sse");

    let postUrl;

    eventSource.addEventListener("endpoint", async (e) => {
        console.log(e.data);
    })

    async function send(method, params, id=null){
        const body = {jsonrpc : "2.0", method, params};

        if(id!==null) body.id = id;

        const res = await fetch(postUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": ["application/json", "text/event-stream"]},
        body: JSON.stringify(body)
    });
    return res.json();
    }

    eventSource.addEventListener("endpoint", async(e) => {
        console.log("I am here!");
        postUrl = `http://localhost:8000/${e.data}`;
        console.log(postUrl);

        await send(
            "initialize", {

            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "my-client", version: "1.0.0" }}, 
            1
        );
        console.log("sent initialize request");
        await send("notifications/initialized", {});
        console.log("initialized");
        const tools = await send("tools/list", {}, 2);
        console.log(tools);
        
        }
    )
})