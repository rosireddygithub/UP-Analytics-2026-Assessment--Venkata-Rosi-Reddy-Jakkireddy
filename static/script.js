

function openTab(tabName){

    const tabs=document.getElementsByClassName("content");

    for(let i=0;i<tabs.length;i++){

        tabs[i].classList.remove("active");

    }

    const buttons=document.getElementsByClassName("tab");

    for(let i=0;i<buttons.length;i++){

        buttons[i].classList.remove("active");

    }

    document.getElementById(tabName).classList.add("active");

    if(tabName==="single")
        buttons[0].classList.add("active");

    else if(tabName==="batch")
        buttons[1].classList.add("active");

    else
        buttons[2].classList.add("active");

}



async function predictSingle() {

    const data = {

        "Age": parseInt(document.getElementById("Age").value),

        "Workclass": document.getElementById("Workclass").value,

        "Education": document.getElementById("Education").value,

        "Education-num": parseInt(document.getElementById("EducationNum").value),

        "Marital status": document.getElementById("MaritalStatus").value,

        "Occupation": document.getElementById("Occupation").value,

        "Relationship": document.getElementById("Relationship").value,

        "Race": document.getElementById("Race").value,

        "Sex": document.getElementById("Sex").value,

        "Capital-gain": parseInt(document.getElementById("CapitalGain").value),

        "Capital-loss": parseInt(document.getElementById("CapitalLoss").value),

        "Hours-per-week": parseInt(document.getElementById("HoursPerWeek").value),

        "Native-country": document.getElementById("NativeCountry").value

    };


    const response = await fetch("/predict", {

        method: "POST",

        headers: {

            "Content-Type": "application/json"

        },

        body: JSON.stringify(data)

    });


    const result = await response.json();


    document.getElementById("singleResult").innerHTML = `

    <div class="result-card">

        <h3>Prediction Result</h3>

        <p><b>Prediction :</b> ${result.prediction}</p>

        <p><b>Probability :</b> ${(result.probability*100).toFixed(2)}%</p>

        <p><b>Priority Tier :</b> ${result.priority_tier}</p>

        <p><b>Recommended :</b>
        ${result.recommended ? "✅ YES" : "❌ NO"}
        </p>

    </div>

    `;

}





async function predictBatch(){

    const jsonText=document.getElementById("batchInput").value;

    const payload=JSON.parse(jsonText);

    const response=await fetch("/predict/batch",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify(payload)

    });

    const result=await response.json();

    renderBatchTable(result);

}

function renderBatchTable(result){

    let html = `

    <div class="summary">

        <h2>Batch Prediction Summary</h2>

        <p><b>Total Customers :</b> ${result["Total Customers"]}</p>

        <p><b>Top 20% Recommended :</b> ${result["Top20 Recommended"]}</p>

    </div>

    <table>

        <thead>

            <tr>

                <th>Rank</th>
                <th>Age</th>
                <th>Occupation</th>
                <th>Prediction</th>
                <th>Probability</th>
                <th>Tier</th>
                <th>Recommended</th>

            </tr>

        </thead>

        <tbody>

    `;

    result.Predictions.forEach(customer => {

        let badge = customer.Recommended === "YES"
            ? '<span class="badge yes">YES</span>'
            : '<span class="badge no">NO</span>';

        html += `

            <tr>

                <td>${customer.Rank}</td>

                <td>${customer.Age}</td>

                <td>${customer.Occupation}</td>

                <td>${customer.Prediction}</td>

                <td>${(customer.Probability*100).toFixed(2)}%</td>

                <td>${customer["Priority Tier"]}</td>

                <td>${badge}</td>

            </tr>

        `;

    });

    html += `

        </tbody>

    </table>

    `;

    document.getElementById("batchResult").innerHTML = html;

}



async function uploadCSV() {

    const file = document.getElementById("csvFile").files[0];

    if (!file) {
        alert("Please select a CSV file.");
        return;
    }

    const status = document.getElementById("csvResult");

   status.innerHTML = `
<div class="loading-container">

    <div class="spinner"></div>

    <h3>Generating Predictions...</h3>

    <p>Please wait while our AI model processes your data.</p>

    <small>Your CSV file will download automatically.</small>

</div>
`;

    const formData = new FormData();
    formData.append("file", file);

    try {

        const response = await fetch("/predict/csv", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error("Prediction failed.");
        }

        const blob = await response.blob();

        const url = window.URL.createObjectURL(blob);

        const a = document.createElement("a");

        a.href = url;

        a.download = "swiftprime_predictions.csv";

        document.body.appendChild(a);

        a.click();

        a.remove();

        window.URL.revokeObjectURL(url);

        status.innerHTML = `
        <div class="success-box">

            ✅ <h3>Prediction Completed</h3>

            <p>Your prediction file has been downloaded successfully.</p>

        </div>
        `;

    } catch (err) {

        status.innerHTML = `
            <div class="error-box">
                ❌ ${err.message}
            </div>
        `;
    }
}





function showLoading(id){

    document.getElementById(id).innerHTML=`

        <div class="result-card">

            <h3>Predicting...</h3>

            <p>Please wait.</p>

        </div>

    `;

}





function showError(id,message){

    document.getElementById(id).innerHTML=`

        <div class="result-card">

            <h3 style="color:red;">Error</h3>

            <p>${message}</p>

        </div>

    `;

}





function clearResults(){

    document.getElementById("singleResult").innerHTML="";

    document.getElementById("batchResult").innerHTML="";

    document.getElementById("csvResult").innerHTML="";

}




window.onload=function(){

    openTab("single");

};