document.getElementById("fileProtocolForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const files = document.getElementById("fileinput").files;
    const protocol = document.getElementById("protocol").value;
    console.log(protocol)

    
})
