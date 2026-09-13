// Keep drafts when moving back through the three-step form.
let linksCount = 2;
let linkDrafts = [];
let validLinksInfo = [];
let busy = false;
let llmConfig = null;
let configurationLoading = true;
let configurationError = "";
let configurationRequest = 0;
let providerChosen = false;
let modelsLoading = false;
let modelsError = "";
let installedModels = [];
let modelsRequest = 0;
let openaiError = "";

const byId = (id) => document.getElementById(id);
const steps = ["stepA", "stepB", "stepC"];

function providerReady() {
  if (configurationLoading || !llmConfig) return false;
  return byId("llmProvider").value === "openai"
    ? llmConfig.openai.configured && !openaiError
    : !modelsLoading && !modelsError && installedModels.includes(byId("ollamaModel").value);
}

function updateControls() {
  document.querySelectorAll("form input, form select, form textarea, form button")
    .forEach((control) => { control.disabled = busy; });
  byId("llmProvider").disabled = busy || configurationLoading;
  byId("ollamaModel").disabled = busy || configurationLoading || modelsLoading || !installedModels.length;
  byId("refreshModels").disabled = busy || configurationLoading || modelsLoading;
  byId("checkConfiguration").disabled = busy || configurationLoading || modelsLoading;
  byId("setupContinue").disabled = busy || !providerReady();
  byId("analyzeBtn").disabled = busy || !providerReady();
}

function renderProviderState() {
  const provider = byId("llmProvider").value;
  byId("ollamaSettings").hidden = provider !== "ollama";
  let message;
  let state = "";
  if (configurationLoading) {
    message = "Checking analysis configuration…";
  } else if (configurationError) {
    message = configurationError;
    state = "error";
  } else if (provider === "openai") {
    if (openaiError || !llmConfig.openai.configured) {
      message = openaiError || "OpenAI API key required. Set OPENAI_API_KEY on the Flask server and restart the app, then check again, or choose Ollama.";
      state = "error";
    } else {
      message = `OpenAI (${llmConfig.openai.model}) is configured. Analysis sends profile content and your description to OpenAI.`;
      state = "success";
    }
  } else if (modelsLoading) {
    message = "Checking installed Ollama models…";
  } else if (modelsError) {
    message = modelsError;
    state = "error";
  } else if (providerReady()) {
    message = "Ollama is ready. No OpenAI API key is needed.";
    state = "success";
  } else {
    message = "Choose an installed Ollama model to continue.";
  }
  setMessage("providerStatus", message, state);
  byId("providerSummary").textContent = provider === "ollama"
    ? `Analysis engine: Ollama · ${byId("ollamaModel").value || "No model selected"}`
    : `Analysis engine: OpenAI · ${llmConfig?.openai.model || "gpt-4o"}`;
  byId("refreshModels").textContent = modelsLoading ? "Checking models…" : "Refresh models";
  byId("checkConfiguration").hidden = state === "success";
  updateControls();
}

async function loadConfiguration() {
  const request = ++configurationRequest;
  ++modelsRequest;
  configurationLoading = true;
  configurationError = "";
  modelsLoading = false;
  renderProviderState();
  try {
    const data = await readJsonResponse(await fetch("/api/llm-config"));
    if (request !== configurationRequest) return;
    if (!["openai", "ollama"].includes(data.default_provider) ||
        typeof data.openai?.configured !== "boolean" || typeof data.openai?.model !== "string" ||
        typeof data.ollama?.configured_model !== "string") {
      throw new Error("Invalid configuration response");
    }
    llmConfig = data;
    openaiError = "";
    if (!providerChosen) byId("llmProvider").value = data.default_provider;
    configurationLoading = false;
    if (byId("llmProvider").value === "ollama") {
      await loadOllamaModels();
    }
  } catch {
    if (request !== configurationRequest) return;
    llmConfig = null;
    configurationError = "Couldn't check the analysis configuration. Check that the app server is running, then check again.";
  } finally {
    if (request === configurationRequest) {
      configurationLoading = false;
      renderProviderState();
    }
  }
}

async function loadOllamaModels() {
  if (byId("llmProvider").value !== "ollama" || configurationLoading || !llmConfig) return;
  const request = ++modelsRequest;
  const previousModel = byId("ollamaModel").value;
  modelsLoading = true;
  modelsError = "";
  renderProviderState();
  try {
    const data = await readJsonResponse(await fetch("/api/ollama/models"));
    if (request !== modelsRequest || byId("llmProvider").value !== "ollama") return;
    if (!Array.isArray(data.models) || data.models.some((name) => typeof name !== "string" || !name.trim())) {
      throw new Error("Invalid model response");
    }
    installedModels = [...new Set(data.models)];
    byId("ollamaModel").replaceChildren();
    installedModels.forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      byId("ollamaModel").append(option);
    });
    byId("ollamaModel").value = installedModels.includes(previousModel) ? previousModel :
      installedModels.includes(data.default_model) ? data.default_model : installedModels[0] || "";
    if (!installedModels.length) modelsError = "No Ollama models are installed. Pull a model on the app server, then refresh models.";
  } catch (error) {
    if (request !== modelsRequest || byId("llmProvider").value !== "ollama") return;
    installedModels = [];
    byId("ollamaModel").replaceChildren();
    modelsError = error.publicMessage || "Couldn't reach Ollama. Start Ollama on the app server, then refresh models.";
  } finally {
    if (request === modelsRequest && byId("llmProvider").value === "ollama") {
      modelsLoading = false;
      renderProviderState();
    }
  }
}

function setMessage(id, text = "", state = "") {
  const element = byId(id);
  element.textContent = text;
  element.dataset.state = state;
  element.hidden = !text;
}

function clearResult() {
  byId("analysisResult").hidden = true;
  byId("analysisText").replaceChildren();
  setMessage("analysisError");
}

function showStep(number) {
  steps.forEach((id, index) => {
    byId(id).hidden = index !== number - 1;
  });
  byId("stepStatus").textContent = `Step ${number} of 3`;
  document.querySelectorAll("[data-step]").forEach((item) => {
    const itemNumber = Number(item.dataset.step);
    item.dataset.state = itemNumber === number ? "current" :
      itemNumber < number ? "complete" : "upcoming";
    if (itemNumber === number) {
      item.setAttribute("aria-current", "step");
    } else {
      item.removeAttribute("aria-current");
    }
  });
  clearResult();
  byId(`${steps[number - 1]}Title`).focus();
}

function setBusy(value, buttonId, label) {
  busy = value;
  updateControls();
  byId(buttonId).textContent = label;
  byId(buttonId).closest("form").setAttribute("aria-busy", String(value));
}

function saveLinkDrafts() {
  document.querySelectorAll("#linksContainer input").forEach((input, index) => {
    linkDrafts[index] = input.value;
  });
}

function generateLinkFields() {
  saveLinkDrafts();
  linksCount = Number(byId("numLinks").value);
  validLinksInfo = [];
  byId("linksContainer").replaceChildren();
  setMessage("validationResults");

  for (let index = 0; index < linksCount; index++) {
    const field = document.createElement("div");
    field.className = "field";

    const label = document.createElement("label");
    label.className = "field-label";
    label.htmlFor = `link_${index}`;
    label.textContent = `Profile link ${index + 1}`;

    const input = document.createElement("input");
    input.className = "form-control";
    input.type = "url";
    input.inputMode = "url";
    input.id = `link_${index}`;
    input.name = `link_${index}`;
    input.placeholder = "https://instagram.com/username";
    input.value = linkDrafts[index] || "";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.required = true;
    input.setAttribute("aria-describedby", `linkStatus_${index}`);
    input.addEventListener("input", () => {
      validLinksInfo = [];
      input.removeAttribute("aria-invalid");
      setMessage(`linkStatus_${index}`);
      setMessage("validationResults");
    });

    const status = document.createElement("p");
    status.id = `linkStatus_${index}`;
    status.className = "field-message";
    status.hidden = true;
    field.append(label, input, status);
    byId("linksContainer").append(field);
  }
  showStep(2);
}

async function readJsonResponse(response) {
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("Invalid server response");
  }
  if (!response.ok) {
    const error = new Error("Request failed");
    if (typeof data.error?.message === "string") error.publicMessage = data.error.message;
    if (typeof data.error?.code === "string") error.code = data.error.code;
    throw error;
  }
  return data;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return readJsonResponse(response);
}

async function validateAllLinks() {
  if (busy) return;
  saveLinkDrafts();
  validLinksInfo = [];
  const links = linkDrafts.slice(0, linksCount).map((link) => link.trim());
  let firstInvalid = null;

  links.forEach((link, index) => {
    const input = byId(`link_${index}`);
    const isValid = link && input.validity.valid;
    input.setAttribute("aria-invalid", String(!isValid));
    setMessage(`linkStatus_${index}`, isValid ? "" :
      "Enter a complete profile URL, starting with https://.", "error");
    if (!isValid && !firstInvalid) firstInvalid = input;
  });
  if (firstInvalid) {
    setMessage("validationResults", "Check the highlighted profile links.", "error");
    firstInvalid.focus();
    return;
  }

  setBusy(true, "continueBtn", "Checking links…");
  setMessage("validationResults", "Checking your profile links…");
  try {
    const data = await postJson("/validate_links", { links });
    if (!Array.isArray(data.results) || data.results.length !== links.length) {
      throw new Error("Invalid validation response");
    }
    data.results.forEach((result, index) => {
      const input = byId(`link_${index}`);
      const isValid = result.is_valid === true && Boolean(result.platform);
      input.setAttribute("aria-invalid", String(!isValid));
      setMessage(`linkStatus_${index}`, isValid ? `${result.platform} link validated.` :
        "This link isn't supported. Check the URL or try another social profile.",
      isValid ? "success" : "error");
      if (isValid) {
        validLinksInfo.push({ url: links[index], platform: result.platform });
      } else if (!firstInvalid) {
        firstInvalid = input;
      }
    });
    if (data.all_valid === true && validLinksInfo.length === links.length) {
      setMessage("validationResults");
      showStep(3);
    } else {
      validLinksInfo = [];
      setMessage("validationResults", "Check the highlighted profile links and continue again.", "error");
    }
  } catch {
    validLinksInfo = [];
    setMessage("validationResults", "We couldn't validate your links. Please try again.", "error");
  } finally {
    setBusy(false, "continueBtn", "Continue");
    if (firstInvalid) firstInvalid.focus();
  }
}

async function analyzeAll() {
  if (busy) return;
  if (!providerReady()) {
    showStep(1);
    renderProviderState();
    return;
  }
  clearResult();
  const description = byId("personalDescription");
  const personalDescription = description.value.trim();
  if (!personalDescription) {
    description.setAttribute("aria-invalid", "true");
    setMessage("descriptionError", "Add a short description before analyzing.", "error");
    description.focus();
    return;
  }
  if (validLinksInfo.length !== linksCount) {
    showStep(2);
    setMessage("validationResults", "Validate your profile links before analyzing.", "error");
    return;
  }

  setMessage("descriptionError");
  description.removeAttribute("aria-invalid");
  setBusy(true, "analyzeBtn", "Analyzing…");
  byId("analysisStatus").hidden = false;
  byId("analysisStatusText").textContent = "Analyzing profiles. This may take a moment.";
  try {
    const data = await postJson("/analyze", {
      links_info: validLinksInfo,
      personal_description: personalDescription,
      provider: byId("llmProvider").value,
      ...(byId("llmProvider").value === "ollama" ? { model: byId("ollamaModel").value } : {}),
    });
    if (typeof data.analysis !== "string" || !data.analysis.trim()) {
      throw new Error("Analysis unavailable");
    }
    if (typeof window.renderAnalysisMarkdown === "function") {
      window.renderAnalysisMarkdown(byId("analysisText"), data.analysis);
    } else {
      byId("analysisText").textContent = data.analysis;
    }
    byId("analysisResult").hidden = false;
    byId("resultTitle").focus();
  } catch (error) {
    if (["openai_key_missing", "openai_auth_error"].includes(error.code)) {
      llmConfig.openai.configured = false;
      openaiError = error.code === "openai_auth_error"
        ? "OpenAI rejected the API key. Update OPENAI_API_KEY on the Flask server and restart the app, then check again, or choose Ollama."
        : "OpenAI API key required. Set OPENAI_API_KEY on the Flask server and restart the app, then check again, or choose Ollama.";
      showStep(1);
      renderProviderState();
    } else if (["ollama_unavailable", "ollama_no_models", "ollama_model_missing"].includes(error.code)) {
      installedModels = [];
      modelsError = error.publicMessage || "Ollama is unavailable. Check the app server and refresh models.";
      showStep(1);
      renderProviderState();
    } else {
      setMessage("analysisError", error.publicMessage || "We couldn't complete the analysis. Your entries are saved here—please try again.", "error");
    }
  } finally {
    byId("analysisStatus").hidden = true;
    setBusy(false, "analyzeBtn", "Analyze profiles");
  }
}

byId("stepA").addEventListener("submit", (event) => {
  event.preventDefault();
  if (!busy && providerReady()) generateLinkFields();
});
byId("stepB").addEventListener("submit", (event) => {
  event.preventDefault();
  validateAllLinks();
});
byId("stepC").addEventListener("submit", (event) => {
  event.preventDefault();
  analyzeAll();
});
byId("linksBack").addEventListener("click", () => {
  if (!busy) {
    saveLinkDrafts();
    showStep(1);
  }
});
byId("descriptionBack").addEventListener("click", () => {
  if (!busy) showStep(2);
});
byId("personalDescription").addEventListener("input", () => {
  byId("personalDescription").removeAttribute("aria-invalid");
  setMessage("descriptionError");
  clearResult();
});
byId("llmProvider").addEventListener("change", () => {
  if (busy) return;
  providerChosen = true;
  ++modelsRequest;
  modelsLoading = false;
  clearResult();
  if (byId("llmProvider").value === "ollama") loadOllamaModels();
  renderProviderState();
});
byId("ollamaModel").addEventListener("change", () => {
  if (!busy) {
    clearResult();
    renderProviderState();
  }
});
byId("refreshModels").addEventListener("click", () => {
  if (!busy && !modelsLoading) loadOllamaModels();
});
byId("checkConfiguration").addEventListener("click", () => {
  if (!busy && !configurationLoading && !modelsLoading) loadConfiguration();
});
loadConfiguration();
