const uploadBtn = document.getElementById("uploadBtn");
const fileInput = document.getElementById("fileInput");
const uploadStatus = document.getElementById("uploadStatus");
const docList = document.getElementById("docList");

const askBtn = document.getElementById("askBtn");
const questionInput = document.getElementById("questionInput");
const answerBox = document.getElementById("answerBox");
const answerText = document.getElementById("answerText");
const sourcesBox = document.getElementById("sourcesBox");

function setStatus(el, message, type) {
  el.textContent = message;
  el.className = `status ${type}`;
}

uploadBtn.addEventListener("click", async () => {
  const file = fileInput.files[0];
  if (!file) {
    setStatus(uploadStatus, "Please select a PDF file first.", "error");
    return;
  }

  uploadBtn.disabled = true;
  setStatus(uploadStatus, "Uploading and processing...", "loading");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      setStatus(uploadStatus, `Error: ${data.detail}`, "error");
      return;
    }

    setStatus(uploadStatus, `Processed successfully — ${data.chunks_created} chunks indexed.`, "success");

    const li = document.createElement("li");
    li.innerHTML = `<span>${data.filename}</span><span>${data.pages_extracted} pages · ${data.chunks_created} chunks</span>`;
    docList.appendChild(li);

    fileInput.value = "";
  } catch (err) {
    setStatus(uploadStatus, `Network error: ${err.message}`, "error");
  } finally {
    uploadBtn.disabled = false;
  }
});

askBtn.addEventListener("click", async () => {
  const question = questionInput.value.trim();
  if (!question) return;

  askBtn.disabled = true;
  askBtn.textContent = "Thinking...";
  answerBox.classList.add("hidden");

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });
    const data = await res.json();

    if (!res.ok) {
      answerText.textContent = `Error: ${data.detail}`;
      sourcesBox.innerHTML = "";
      answerBox.classList.remove("hidden");
      return;
    }

    answerText.textContent = data.answer;

    sourcesBox.innerHTML = "";
    data.sources.forEach((s, i) => {
      const div = document.createElement("div");
      div.className = "source-item";
      div.innerHTML = `
        <div class="source-meta">${s.source_file} — page ${s.page_number} (score: ${s.score.toFixed(2)})</div>
        <div class="source-snippet">${s.snippet}...</div>
      `;
      sourcesBox.appendChild(div);
    });

    answerBox.classList.remove("hidden");
  } catch (err) {
    answerText.textContent = `Network error: ${err.message}`;
    sourcesBox.innerHTML = "";
    answerBox.classList.remove("hidden");
  } finally {
    askBtn.disabled = false;
    askBtn.textContent = "Ask";
  }
});

questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") askBtn.click();
});