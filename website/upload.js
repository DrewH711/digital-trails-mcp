function showMessage(message, color='black'){
    messageDisplay = document.getElementById("messages");
    messageDisplay.textContent = message;
    messageDisplay.style.color = color;
}

function clearMessage(){
    document.getElementById("messages").textContent = "";
}

window.showMessage = showMessage;
window.clearMessage = clearMessage;

document.getElementById("protocol").addEventListener("change", () => {
    clearMessage();
    const protocol = document.getElementById("protocol").value;

    let fileSchemeText = '';

    allowedCSVNames[protocol].forEach(element => {
        fileSchemeText += `${element}<br>`
    });

    document.getElementById("protocolInfo").innerHTML = `File naming scheme for ${document.getElementById(protocol).textContent}:<br><br>${fileSchemeText}`;
})

//validate files on change
let filesValid = false;
document.getElementById("fileinput").addEventListener("change", (e) => {
    clearMessage();
    const protocol = document.getElementById("protocol").value;
    if(protocol!==""){

        const files = e.target.files;
        console.log(files)

        
        
        for(let i=0; i<files.length; i++){
            file = files.item(i);
            allowedNames = allowedCSVNames[protocol]
            
            if( !(allowedNames.includes(file.name)) ) {
                showMessage(`Error: ${file.name} does not match the naming scheme for ${document.getElementById(protocol).innerText}. Please refer to the naming scheme below.`, "red")
                document.getElementById("fileProtocolForm").reset();
                document.getElementById("protocol").value = protocol;
                return;
            }

        }

    }

    else{
        showMessage("Error: Please select a protocol before uploading CSV files", "red");
        document.getElementById("fileProtocolForm").reset();
        return;
    }

})

//deploy on file submission
document.getElementById("fileProtocolForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const protocol = document.getElementById("protocol").value;
    const files = document.getElementById("fileinput").files;

    if(files.length===0){
        showMessage("Error: no files uploaded", "red");
        return;
    }

    //get file contents and call deploy function from requests.js

    let fileContents = {};

    for(i=0;i<files.length;i++){
        reader = new FileReader();

        reader.onload = () => {
            fileContents[file.name] = reader.result;
        }
        reader.onerror = () =>{
            showMessage(`Error: Could not read file ${file.name}. Please try again`, "red");
            document.getElementById("fileProtocolForm").reset();
            document.getElementById("protocol").value = protocol;
            return;
        }
        reader.readAsText(file);

        }

        await window.deployProtocol(protocol, fileContents);
    }
    
)

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
