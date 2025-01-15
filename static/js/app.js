// app.js

let linksCount = 2; // default
let validLinksInfo = []; // Will store { url, is_valid, platform }

function generateLinkFields() {
    // Get the number from the select
    const select = document.getElementById("numLinks");
    linksCount = parseInt(select.value);

    // Show Step B, hide Step A
    document.getElementById("stepB").style.display = "block";
    document.getElementById("stepA").style.display = "none";

    // Create input fields
    const container = document.getElementById("linksContainer");
    container.innerHTML = "";
    for (let i = 0; i < linksCount; i++) {
        const input = document.createElement("input");
        input.type = "text";
        input.id = `link_${i}`;
        input.style.width = "70%";
        input.placeholder = "For example: https://twitter.com/....., https://instagram.com/..... or any other social media link";
        container.appendChild(input);

        const span = document.createElement("span");
        span.id = `validMark_${i}`;
        span.className = "valid-mark";
        container.appendChild(span);

        const br = document.createElement("br");
        container.appendChild(br);
    }

    // Hide 'Continue' until validation is done
    document.getElementById("continueBtn").style.display = "none";
}

function validateAllLinks() {
    // Gather links
    const links = [];
    for (let i = 0; i < linksCount; i++) {
        const val = document.getElementById(`link_${i}`).value.trim();
        links.push(val);
    }

    // Send to server for validation
    fetch("/validate_links", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ links }),
    })
        .then((res) => res.json())
        .then((data) => {
            // data.results => array of { url, is_valid, platform }
            // data.all_valid => boolean
            const results = data.results;
            const allValid = data.all_valid;

            validLinksInfo = []; // reset

            for (let i = 0; i < results.length; i++) {
                const markSpan = document.getElementById(`validMark_${i}`);
                if (results[i].is_valid) {
                    markSpan.textContent = " ✓";
                    markSpan.classList.remove("invalid");
                    markSpan.classList.add("valid");
                    validLinksInfo.push({
                        url: results[i].url,
                        platform: results[i].platform,
                    });
                } else {
                    markSpan.textContent = " ✗";
                    markSpan.classList.remove("valid");
                    markSpan.classList.add("invalid");
                }
            }

            // Show or hide the "Continue" button
            if (allValid) {
                document.getElementById("continueBtn").style.display = "inline-block";
            } else {
                document.getElementById("continueBtn").style.display = "none";
            }
        })
        .catch((err) => console.error("Error validating links:", err));
}

function showStepC() {
    document.getElementById("stepC").style.display = "block";
    document.getElementById("stepB").style.display = "none";
}

function analyzeAll() {
    // Show spinner
    document.getElementById("spinner").style.display = "block";

    // Hide any previous result
    document.getElementById("analysisResult").style.display = "none";
    document.getElementById("analysisText").innerHTML = "";

    // Get personal description
    const personalDesc = document.getElementById("personalDescription").value.trim();
    if (!personalDesc) {
        alert("Please provide a personal description before analyzing.");
        document.getElementById("spinner").style.display = "none";
        return;
    }

    // Send final data (links + personal description)
    const bodyData = {
        links_info: validLinksInfo,
        personal_description: personalDesc,
    };

    fetch("/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bodyData),
    })
        .then((res) => res.json())
        .then((data) => {
            // Hide spinner once we have a response
            document.getElementById("spinner").style.display = "none";

            // Show final result
            document.getElementById("analysisResult").style.display = "block";

            // If you receive the response as Markdown, render it using marked.js:
            const markdown = data.analysis || "";
            const htmlContent = marked.parse(markdown);
            document.getElementById("analysisText").innerHTML = htmlContent;
        })
        .catch((err) => {
            console.error("Error analyzing data:", err);
            // Hide spinner if there's an error
            document.getElementById("spinner").style.display = "none";
        });
}



















