async function send(method, params, requestID=null, mcpSessionID=null){

    const body = {jsonrpc : "2.0", method, params};
    
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

const allowedCSVNames = {
    "protocol-leia": [
        "LEIA Interventions, Resources, and Tips - Long Scenarios.csv",
        "LEIA Interventions, Resources, and Tips - Resources.csv",
        "LEIA Interventions, Resources, and Tips - Short Scenarios.csv",
        "LEIA Interventions, Resources, and Tips - Strategies.csv",
        "LEIA Interventions, Resources, and Tips - Surveys.csv",
        "LEIA Interventions, Resources, and Tips - Tips.csv",
        "LEIA long scenarios structure.csv",
        "dose1_scenarios - HTC.csv",
        "images.csv"
    ],

    "protocol-uma": [
        "Discrimination.csv",
        "ER Strategies.csv",
        "Final Long Scenarios.csv",
        "Resources for On-Demand Library.csv",
        "UMA Resources.csv",
        "dose1_scenarios.csv",
        "htc_long_scenarios_structure.csv",
        "lessons_learned_text.csv",
        "short_scenarios.csv",
        "survey_questions.csv",
        "tips.csv",
        "write_your_own.csv"
    ],

    "mindtrails_spanish": [
        "Discrimination.csv",
        "ER_Strategies.csv",
        "MTSpanish_on-demand.csv",
        "MTSpanish_survey_questions.csv",
        "Reminders.csv",
        "Spanish Images.csv",
        "Spanish htc_long_scenarios_structure.csv",
        "Spanish lessons_learned_text.csv",
        "Spanish_Long_Scenarios.csv",
        "Spanish_Resources.csv",
        "Spanish_Short_Scenarios.csv",
        "Spanish_dose1_scenarios.csv",
        "Spanish_write_your_own.csv",
        "tips.csv"
    ],

    "mindtrails_movement": [
        "MT Movement Final Long Scenarios - MTM Long Scenarios-HD FOR APP.csv",
        "MT Movement Final Long Scenarios - MTM Long Scenarios-PD FOR APP.csv",
        "MT Movement Ranked Statements and Tips (post-session recommendations) - ER Strategies- HD.csv",
        "MT Movement Ranked Statements and Tips (post-session recommendations) - ER Strategies- PD.csv",
        "MT Movement Ranked Statements and Tips (post-session recommendations) - New HD Motivational Statements.csv",
        "MT Movement Ranked Statements and Tips (post-session recommendations) - New PD Motivational Statements.csv",
        "MT Movement Ranked Statements and Tips (post-session recommendations) - Tips to Apply Lessons Learned.csv",
        "MT Movement Resources for On-Demand Library - HD Resources.csv",
        "MT Movement Resources for On-Demand Library - PD Resources.csv",
        "MTM Discrimination - MTM (HD).csv",
        "MTM Discrimination - MTM (PD).csv",
        "MTM Short Scenarios by Session - Images.csv",
        "MTM Short Scenarios by Session - MTM HD Final for app_old.csv",
        "MTM Short Scenarios by Session - MTM PD Final for app_old.csv",
        "MTM dose1_scenarios.csv",
        "MTM lessons_learned_text - HD.csv",
        "MTM lessons_learned_text - PD.csv",
        "MTM_long_scenarios_structure.csv",
        "MTM_survey_questions - Final_HD MTM_survey_questions.csv",
        "MTM_survey_questions - Final_PD MTM_survey_questions.csv",
        "MTM_write_your_own.csv",
        "Reminders.csv"
    ]
}

let mcpSessionID=0;
let initialized = false;
const url = "http://localhost:8000/mcp";

document.getElementById("fileProtocolForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    // initialize
    if(!initialized){

        init = await send(
            "initialize", {

            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "my-client", version: "1.0.0" }}, 
            1
        );
        mcpSessionID = init.headers.get('mcp-session-id');
        console.log("sent initialize request");
        await send("notifications/initialized", {}, null, mcpSessionID);
        console.log("initialized");

        initialized=true;
    }    
    
    // replace CSV files

    // Release

    const tools = await send("tools/list", {}, 2);
    console.log(tools);
    
    }

)