const STORAGE_KEY = "math-feedback-report-v2";
const FEEDBACK_HEADER = "문항 피드백 및 특이사항";

const blankRow = () => ({ question: "", feedback: "" });
const blankRound = (number) => ({
  title: `${number}회독`,
  time: "",
  rows: [blankRow()]
});

const defaultReport = {
  examTitle: "수학 실전 모의고사 분석 보고서",
  rawScore: "",
  cutScore: "",
  rounds: [
    {
      title: "1회독",
      time: "",
      rows: Array.from({ length: 7 }, blankRow)
    },
    {
      title: "2회독",
      time: "",
      rows: Array.from({ length: 3 }, blankRow)
    },
    {
      title: "3회독",
      time: "",
      rows: Array.from({ length: 1 }, blankRow)
    }
  ],
  notes: "",
  feedback: ""
};

const state = loadReport();
let activeRoundIndex = 0;
let generatedImageUrl = "";

const nodes = {
  reportRoot: document.getElementById("reportRoot"),
  overflowNotice: document.getElementById("overflowNotice"),
  saveStatus: document.getElementById("saveStatus"),
  resetButton: document.getElementById("resetButton"),
  printButton: document.getElementById("printButton"),
  addRowButton: document.getElementById("addRowButton"),
  roundTabs: document.getElementById("roundTabs"),
  roundEditor: document.getElementById("roundEditor"),
  examTitleInput: document.getElementById("examTitleInput"),
  rawScoreInput: document.getElementById("rawScoreInput"),
  cutScoreInput: document.getElementById("cutScoreInput"),
  notesInput: document.getElementById("notesInput"),
  feedbackInput: document.getElementById("feedbackInput")
};

function loadReport() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? mergeReport(JSON.parse(saved)) : clone(defaultReport);
  } catch {
    return clone(defaultReport);
  }
}

function mergeReport(saved) {
  const merged = clone(defaultReport);
  Object.assign(merged, saved);

  if (!Array.isArray(saved.rounds)) {
    return merged;
  }

  merged.rounds = defaultReport.rounds.map((round, index) => ({
    ...round,
    ...(saved.rounds[index] || {}),
    rows: Array.isArray(saved.rounds[index]?.rows) ? saved.rounds[index].rows : round.rows
  }));
  return merged;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function saveReport() {
  const now = new Intl.DateTimeFormat("ko-KR", {
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date());

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    nodes.saveStatus.textContent = `저장됨 ${now}`;
  } catch {
    nodes.saveStatus.textContent = `임시 편집 ${now}`;
  }
}

function setPath(path, value) {
  const parts = path.split(".");
  let target = state;
  parts.slice(0, -1).forEach((part) => {
    target = target[Number.isNaN(Number(part)) ? part : Number(part)];
  });
  const key = parts.at(-1);
  target[Number.isNaN(Number(key)) ? key : Number(key)] = value;
}

function createEditable(tagName, className, value, path) {
  const element = document.createElement(tagName);
  element.className = className;
  element.contentEditable = "true";
  element.spellcheck = false;
  element.dataset.path = path;
  element.textContent = value;
  element.addEventListener("input", () => {
    setPath(path, element.innerText.trimEnd());
    syncEditorFields();
    saveReport();
    checkOverflow();
  });
  return element;
}

function renderPreview() {
  nodes.reportRoot.replaceChildren();

  const report = document.createElement("section");
  report.className = "report-page report-long";
  report.append(
    createEditable("h2", "report-title", state.examTitle, "examTitle"),
    createSummary(),
    ...state.rounds.map((round, index) => createRoundSection(round, index)),
    createNoteBox("느낀 점", state.notes, "notes"),
    createNoteBox("FEEDBACK", state.feedback, "feedback", true)
  );

  nodes.reportRoot.append(createRoundManager(), report);
  checkOverflow();
}

function createSummary() {
  const grid = document.createElement("div");
  grid.className = "summary-grid";
  grid.append(createSummaryCard("원점수", state.rawScore, "rawScore"));
  grid.append(createSummaryCard("뇌피셜 등급컷", state.cutScore, "cutScore"));
  return grid;
}

function createRoundManager() {
  const tools = document.createElement("div");
  tools.className = "document-edit-bar screen-only";

  const addButton = document.createElement("button");
  addButton.className = "document-action-button";
  addButton.type = "button";
  addButton.textContent = "+ 회독";
  addButton.title = "회독 추가";
  addButton.setAttribute("aria-label", "회독 추가");
  addButton.dataset.action = "add-preview-round";

  const deleteButton = document.createElement("button");
  deleteButton.className = "document-action-button danger";
  deleteButton.type = "button";
  deleteButton.textContent = "- 회독";
  deleteButton.title = "가장 큰 회독 삭제";
  deleteButton.setAttribute("aria-label", "가장 큰 회독 삭제");
  deleteButton.disabled = state.rounds.length === 0;
  deleteButton.dataset.action = "delete-highest-preview-round";

  tools.append(addButton, deleteButton);
  return tools;
}

function createSummaryCard(label, value, path) {
  const card = document.createElement("div");
  card.className = "summary-card";

  const labelNode = document.createElement("div");
  labelNode.className = "summary-card-label";
  labelNode.textContent = label;

  const valueNode = createEditable("div", "summary-card-value", value, path);
  card.append(labelNode, valueNode);
  return card;
}

function createRoundSection(round, index) {
  const section = document.createElement("section");
  section.className = "attempt-section";

  const heading = document.createElement("div");
  heading.className = "attempt-heading";

  const headingContent = document.createElement("div");
  headingContent.className = "attempt-heading-content";
  headingContent.append(
    createEditable("div", "attempt-title", round.title, `rounds.${index}.title`),
    createEditable("div", "time-chip", round.time, `rounds.${index}.time`)
  );

  const table = document.createElement("table");
  table.className = "feedback-table";
  table.append(createTableHead(), createTableBody(round.rows, index));

  const sectionTools = document.createElement("div");
  sectionTools.className = "attempt-tools screen-only";

  const addButton = document.createElement("button");
  addButton.className = "section-action-button icon-only";
  addButton.type = "button";
  addButton.textContent = "+";
  addButton.title = "행 추가";
  addButton.setAttribute("aria-label", `${round.title || `${index + 1}회독`} 행 추가`);
  addButton.dataset.action = "add-preview-row";
  addButton.dataset.roundIndex = String(index);

  sectionTools.append(addButton);
  heading.append(headingContent, sectionTools);
  section.append(heading, table);
  return section;
}

function createTableHead() {
  const thead = document.createElement("thead");
  const row = document.createElement("tr");
  ["문항 번호", FEEDBACK_HEADER].forEach((label) => {
    const th = document.createElement("th");
    th.textContent = label;
    row.append(th);
  });
  thead.append(row);
  return thead;
}

function createTableBody(rows, roundIndex) {
  const tbody = document.createElement("tbody");
  rows.forEach((item, rowIndex) => {
    const tr = document.createElement("tr");

    const questionCell = document.createElement("td");
    const deleteButton = document.createElement("button");
    deleteButton.className = "row-delete-inline screen-only";
    deleteButton.type = "button";
    deleteButton.textContent = "-";
    deleteButton.title = "행 삭제";
    deleteButton.setAttribute("aria-label", `${rowIndex + 1}번째 행 삭제`);
    deleteButton.dataset.action = "delete-preview-row";
    deleteButton.dataset.roundIndex = String(roundIndex);
    deleteButton.dataset.rowIndex = String(rowIndex);
    const questionEditor = createEditable(
      "div",
      "cell-editable question-cell",
      item.question,
      `rounds.${roundIndex}.rows.${rowIndex}.question`
    );
    questionEditor.dataset.roundIndex = String(roundIndex);
    questionEditor.dataset.rowIndex = String(rowIndex);
    questionEditor.dataset.cellType = "question";
    questionCell.append(
      questionEditor,
      deleteButton
    );

    const feedbackCell = document.createElement("td");
    const feedbackEditor = createEditable(
      "div",
      "cell-editable feedback-cell",
      item.feedback,
      `rounds.${roundIndex}.rows.${rowIndex}.feedback`
    );
    feedbackEditor.dataset.roundIndex = String(roundIndex);
    feedbackEditor.dataset.rowIndex = String(rowIndex);
    feedbackEditor.dataset.cellType = "feedback";
    feedbackCell.append(feedbackEditor);

    tr.append(questionCell, feedbackCell);
    tbody.append(tr);
  });
  return tbody;
}

function createNoteBox(title, value, path, isFeedback = false) {
  const box = document.createElement("section");
  box.className = isFeedback ? "note-box feedback" : "note-box";

  const titleNode = document.createElement("div");
  titleNode.className = "note-title";
  titleNode.textContent = title;

  box.append(titleNode, createEditable("div", "note-body", value, path));
  return box;
}

function createPageNumber(label) {
  const pageNumber = document.createElement("div");
  pageNumber.className = "page-number";
  pageNumber.textContent = label;
  return pageNumber;
}

function renderEditor() {
  syncEditorFields();
  nodes.addRowButton.textContent = state.rounds.length === 0 ? "회독 추가" : "행 추가";
  renderRoundTabs();
  renderRoundEditor();
}

function syncEditorFields() {
  if (document.activeElement !== nodes.examTitleInput) nodes.examTitleInput.value = state.examTitle;
  if (document.activeElement !== nodes.rawScoreInput) nodes.rawScoreInput.value = state.rawScore;
  if (document.activeElement !== nodes.cutScoreInput) nodes.cutScoreInput.value = state.cutScore;
  if (document.activeElement !== nodes.notesInput) nodes.notesInput.value = state.notes;
  if (document.activeElement !== nodes.feedbackInput) nodes.feedbackInput.value = state.feedback;
}

function renderRoundTabs() {
  nodes.roundTabs.replaceChildren();
  if (state.rounds.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-row-message";
    empty.textContent = "회독이 없습니다.";
    nodes.roundTabs.append(empty);
    return;
  }

  state.rounds.forEach((round, index) => {
    const button = document.createElement("button");
    button.className = index === activeRoundIndex ? "round-tab is-active" : "round-tab";
    button.type = "button";
    button.role = "tab";
    button.textContent = round.title || `${index + 1}회독`;
    button.addEventListener("click", () => {
      activeRoundIndex = index;
      renderEditor();
    });
    nodes.roundTabs.append(button);
  });
}

function renderRoundEditor() {
  const round = state.rounds[activeRoundIndex];
  nodes.roundEditor.replaceChildren();

  if (!round) {
    const empty = document.createElement("div");
    empty.className = "empty-row-message";
    empty.textContent = "오른쪽 보고서에서 회독 추가를 누르면 새 회독 표가 생깁니다.";
    nodes.roundEditor.append(empty);
    return;
  }

  const timeField = document.createElement("label");
  timeField.className = "field time-field";

  const timeLabel = document.createElement("span");
  timeLabel.textContent = "소요시간";

  const timeInput = document.createElement("input");
  timeInput.className = "row-input";
  timeInput.type = "text";
  timeInput.value = round.time;
  timeInput.dataset.path = `rounds.${activeRoundIndex}.time`;

  timeField.append(timeLabel, timeInput);
  nodes.roundEditor.append(timeField);

  if (round.rows.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-row-message";
    empty.textContent = "표 행이 없습니다. 행 추가를 누르면 빈칸이 생깁니다.";
    nodes.roundEditor.append(empty);
  }

  round.rows.forEach((item, rowIndex) => {
    const row = document.createElement("div");
    row.className = "row-editor-item";

    const grid = document.createElement("div");
    grid.className = "row-editor-grid";

    const questionInput = document.createElement("input");
    questionInput.className = "row-input";
    questionInput.type = "text";
    questionInput.value = item.question;
    questionInput.placeholder = "문항 번호";
    questionInput.dataset.path = `rounds.${activeRoundIndex}.rows.${rowIndex}.question`;

    const feedbackInput = document.createElement("textarea");
    feedbackInput.className = "row-textarea";
    feedbackInput.rows = 2;
    feedbackInput.value = item.feedback;
    feedbackInput.placeholder = "피드백 및 특이사항";
    feedbackInput.dataset.path = `rounds.${activeRoundIndex}.rows.${rowIndex}.feedback`;

    const tools = document.createElement("div");
    tools.className = "row-tools";

    const deleteButton = document.createElement("button");
    deleteButton.className = "row-tool";
    deleteButton.type = "button";
    deleteButton.textContent = "행 삭제";
    deleteButton.dataset.action = "delete-row";
    deleteButton.dataset.index = String(rowIndex);

    tools.append(deleteButton);
    grid.append(questionInput, feedbackInput);
    row.append(grid, tools);
    nodes.roundEditor.append(row);
  });
}

function updateAndRender(path, value) {
  setPath(path, value);
  renderPreview();
  renderRoundTabs();
  saveReport();
}

function bindTopField(input, path) {
  input.addEventListener("input", () => {
    updateAndRender(path, input.value);
  });
}

function addRowToRound(roundIndex) {
  if (!state.rounds[roundIndex]) return;
  activeRoundIndex = roundIndex;
  state.rounds[roundIndex].rows.push(blankRow());
  renderPreview();
  renderEditor();
  saveReport();
}

function addBlankRow() {
  if (state.rounds.length === 0) {
    addRound();
    return;
  }
  addRowToRound(activeRoundIndex);
}

function deleteRow(roundIndex, rowIndex) {
  if (!state.rounds[roundIndex]) return;
  activeRoundIndex = roundIndex;
  state.rounds[roundIndex].rows.splice(rowIndex, 1);
  renderPreview();
  renderEditor();
  saveReport();
}

function commitEditableValue(element) {
  const path = element.dataset.path;
  if (!path) return;
  setPath(path, element.innerText.trimEnd());
}

function focusQuestionCell(roundIndex, rowIndex) {
  const selector = `.question-cell[data-round-index="${roundIndex}"][data-row-index="${rowIndex}"]`;
  const cell = nodes.reportRoot.querySelector(selector);
  if (!cell) return;

  cell.focus();
  const range = document.createRange();
  range.selectNodeContents(cell);
  range.collapse(false);

  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
}

function moveToNextQuestionCell(roundIndex, rowIndex) {
  const round = state.rounds[roundIndex];
  if (!round) return;

  const nextRowIndex = rowIndex + 1;
  if (nextRowIndex >= round.rows.length) {
    activeRoundIndex = roundIndex;
    round.rows.push(blankRow());
    renderPreview();
    renderEditor();
    saveReport();
    requestAnimationFrame(() => focusQuestionCell(roundIndex, nextRowIndex));
    return;
  }

  saveReport();
  focusQuestionCell(roundIndex, nextRowIndex);
}

function addRound() {
  const numbers = state.rounds
    .map((round, index) => getRoundNumber(round, index))
    .filter((number) => Number.isFinite(number));
  const nextNumber = numbers.length ? Math.max(...numbers) + 1 : state.rounds.length + 1;
  state.rounds.push(blankRound(nextNumber));
  activeRoundIndex = state.rounds.length - 1;
  renderPreview();
  renderEditor();
  saveReport();
}

function getRoundNumber(round, index) {
  const match = String(round?.title || "").match(/\d+/);
  return match ? Number(match[0]) : index + 1;
}

function getHighestRoundIndex() {
  if (state.rounds.length === 0) return -1;

  return state.rounds.reduce((highestIndex, round, index) => {
    const currentNumber = getRoundNumber(round, index);
    const highestNumber = getRoundNumber(state.rounds[highestIndex], highestIndex);
    return currentNumber >= highestNumber ? index : highestIndex;
  }, 0);
}

function deleteHighestRound() {
  const roundIndex = getHighestRoundIndex();
  if (roundIndex < 0) return;
  deleteRound(roundIndex);
}

function deleteRound(roundIndex) {
  if (!state.rounds[roundIndex]) return;
  state.rounds.splice(roundIndex, 1);
  activeRoundIndex = Math.min(activeRoundIndex, Math.max(state.rounds.length - 1, 0));
  renderPreview();
  renderEditor();
  saveReport();
}

function resetReport() {
  const fresh = clone(defaultReport);
  Object.keys(state).forEach((key) => delete state[key]);
  Object.assign(state, fresh);
  activeRoundIndex = 0;
  renderPreview();
  renderEditor();
  saveReport();
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function showGeneratedImage(blob) {
  if (generatedImageUrl) {
    URL.revokeObjectURL(generatedImageUrl);
  }

  generatedImageUrl = URL.createObjectURL(blob);
  const imageUrl = generatedImageUrl;
  const link = document.createElement("a");
  link.href = imageUrl;
  link.download = "math-feedback-report.png";
  document.body.append(link);
  link.click();
  link.remove();

  nodes.saveStatus.textContent = "다운로드됨";
  window.setTimeout(() => {
    if (generatedImageUrl !== imageUrl) return;
    URL.revokeObjectURL(imageUrl);
    generatedImageUrl = "";
  }, 30000);
}

function canvasToBlob(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error("이미지를 만들 수 없습니다."));
    }, "image/png");
  });
}

function setCanvasFont(context, size, weight = 400) {
  context.font = `${weight} ${size}px "Malgun Gothic", "Apple SD Gothic Neo", "Noto Sans KR", Arial, sans-serif`;
}

function normalizeText(value) {
  return String(value || "").replace(/\r\n/g, "\n");
}

function splitLongToken(context, token, maxWidth) {
  const chunks = [];
  let chunk = "";
  [...token].forEach((letter) => {
    const next = chunk + letter;
    if (chunk && context.measureText(next).width > maxWidth) {
      chunks.push(chunk);
      chunk = letter;
    } else {
      chunk = next;
    }
  });
  if (chunk) chunks.push(chunk);
  return chunks;
}

function wrapTextForCanvas(context, text, maxWidth) {
  const normalized = normalizeText(text);
  if (!normalized) return [];

  const lines = [];
  normalized.split("\n").forEach((paragraph) => {
    if (!paragraph) {
      lines.push("");
      return;
    }

    const words = paragraph.split(/(\s+)/).filter(Boolean);
    let currentLine = "";
    words.forEach((word) => {
      const nextLine = currentLine + word;
      if (context.measureText(nextLine).width <= maxWidth) {
        currentLine = nextLine;
        return;
      }

      if (currentLine.trim()) {
        lines.push(currentLine.trimEnd());
        currentLine = "";
      }

      if (context.measureText(word).width > maxWidth) {
        const chunks = splitLongToken(context, word, maxWidth);
        lines.push(...chunks.slice(0, -1));
        currentLine = chunks.at(-1) || "";
      } else {
        currentLine = word.trimStart();
      }
    });

    if (currentLine || paragraph === "") {
      lines.push(currentLine.trimEnd());
    }
  });

  return lines;
}

function drawTextLines(context, lines, x, y, lineHeight, options = {}) {
  context.fillStyle = options.color || "#152331";
  context.textAlign = options.align || "left";
  context.textBaseline = "top";

  lines.forEach((line, index) => {
    context.fillText(line, x, y + index * lineHeight);
  });
}

function drawRoundedRect(context, x, y, width, height, radius, fill, stroke) {
  context.beginPath();
  context.moveTo(x + radius, y);
  context.lineTo(x + width - radius, y);
  context.quadraticCurveTo(x + width, y, x + width, y + radius);
  context.lineTo(x + width, y + height - radius);
  context.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  context.lineTo(x + radius, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - radius);
  context.lineTo(x, y + radius);
  context.quadraticCurveTo(x, y, x + radius, y);
  context.closePath();

  if (fill) {
    context.fillStyle = fill;
    context.fill();
  }

  if (stroke) {
    context.strokeStyle = stroke;
    context.stroke();
  }
}

function drawCanvasReport(context, options = {}) {
  const draw = options.draw === true;
  const width = 1240;
  const marginX = 86;
  const contentWidth = width - marginX * 2;
  const navy = "#17354a";
  const navyDark = "#0e2434";
  const line = "#cfd6dc";
  const muted = "#52606d";
  const ink = "#111c27";
  let y = 42;

  if (draw) {
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, width, options.height || 1);
  }

  setCanvasFont(context, 32, 900);
  if (draw) {
    context.fillStyle = ink;
    context.textAlign = "center";
    context.textBaseline = "top";
    context.fillStyle = navyDark;
    context.fillRect(marginX, y, contentWidth, 5);
    context.fillText(normalizeText(state.examTitle), width / 2, y + 17);
    context.strokeStyle = navy;
    context.lineWidth = 2;
    context.beginPath();
    context.moveTo(marginX, y + 69);
    context.lineTo(width - marginX, y + 69);
    context.stroke();
  }
  y += 88;

  const cardWidth = contentWidth / 2;
  const cardHeight = 82;
  [
    ["원점수", state.rawScore],
    ["뇌피셜 등급컷", state.cutScore]
  ].forEach(([label, value], index) => {
    const x = marginX + index * cardWidth;
    if (!draw) return;
    context.fillStyle = "#ffffff";
    context.fillRect(x, y, cardWidth, cardHeight);
    context.strokeStyle = line;
    context.strokeRect(x, y, cardWidth, cardHeight);
    setCanvasFont(context, 16, 800);
    context.fillStyle = "#33404b";
    context.textAlign = "center";
    context.fillText(label, x + cardWidth / 2, y + 17);
    setCanvasFont(context, 28, 900);
    context.fillStyle = ink;
    context.fillText(normalizeText(value), x + cardWidth / 2, y + 45);
  });
  y += cardHeight + 24;

  state.rounds.forEach((round) => {
    if (draw) {
      context.fillStyle = navy;
      context.fillRect(marginX, y + 5, 6, 27);
      setCanvasFont(context, 25, 900);
      context.fillStyle = navyDark;
      context.textAlign = "left";
      context.fillText(normalizeText(round.title), marginX + 14, y);

      const time = normalizeText(round.time);
      if (time) {
        setCanvasFont(context, 16, 900);
        const chipX = marginX + 104;
        const chipWidth = Math.max(132, context.measureText(time).width + 28);
        context.strokeStyle = "#b9c3ca";
        context.beginPath();
        context.moveTo(chipX, y + 29);
        context.lineTo(chipX + chipWidth, y + 29);
        context.stroke();
        context.fillStyle = muted;
        context.fillText(time, chipX + 14, y + 7);
      }
      context.strokeStyle = navy;
      context.beginPath();
      context.moveTo(marginX, y + 42);
      context.lineTo(width - marginX, y + 42);
      context.stroke();
    }
    y += 43;

    const questionWidth = 205;
    const feedbackWidth = contentWidth - questionWidth;
    const headerHeight = 46;
    if (draw) {
      context.fillStyle = navy;
      context.fillRect(marginX, y, questionWidth, headerHeight);
      context.fillRect(marginX + questionWidth, y, feedbackWidth, headerHeight);
      context.strokeStyle = navy;
      context.strokeRect(marginX, y, contentWidth, headerHeight);
      context.strokeStyle = "#486474";
      context.beginPath();
      context.moveTo(marginX + questionWidth, y);
      context.lineTo(marginX + questionWidth, y + headerHeight);
      context.stroke();
      setCanvasFont(context, 16, 900);
      context.fillStyle = "#ffffff";
      context.textAlign = "center";
      context.fillText("문항 번호", marginX + questionWidth / 2, y + 14);
      context.fillText(FEEDBACK_HEADER, marginX + questionWidth + feedbackWidth / 2, y + 14);
    }
    y += headerHeight;

    round.rows.forEach((item) => {
      setCanvasFont(context, 18, 900);
      const questionLines = wrapTextForCanvas(context, item.question, questionWidth - 34);
      setCanvasFont(context, 18, 400);
      const feedbackLines = wrapTextForCanvas(context, item.feedback, feedbackWidth - 34);
      const rowHeight = Math.max(48, questionLines.length * 25 + 22, feedbackLines.length * 25 + 22);

      if (draw) {
        context.strokeStyle = line;
        context.lineWidth = 1;
        context.strokeRect(marginX, y, questionWidth, rowHeight);
        context.strokeRect(marginX + questionWidth, y, feedbackWidth, rowHeight);

        setCanvasFont(context, 18, 900);
        drawTextLines(context, questionLines, marginX + questionWidth / 2, y + Math.max(12, (rowHeight - questionLines.length * 25) / 2), 25, {
          align: "center",
          color: "#05070a"
        });

        setCanvasFont(context, 18, 400);
        drawTextLines(context, feedbackLines, marginX + questionWidth + 20, y + 14, 25, {
          color: "#101820"
        });
      }
      y += rowHeight;
    });

    y += 24;
  });

  function drawNoteBox(title, value, minBodyHeight) {
    setCanvasFont(context, 20, 400);
    const bodyLines = wrapTextForCanvas(context, value, contentWidth - 42);
    const bodyHeight = Math.max(minBodyHeight, bodyLines.length * 29);
    const boxHeight = bodyHeight + 64;

    if (draw) {
      context.fillStyle = "#ffffff";
      context.fillRect(marginX, y, contentWidth, boxHeight);
      context.strokeStyle = line;
      context.strokeRect(marginX, y, contentWidth, boxHeight);
      context.fillStyle = "#f5f7f8";
      context.fillRect(marginX, y, contentWidth, 46);
      context.strokeStyle = line;
      context.beginPath();
      context.moveTo(marginX, y + 46);
      context.lineTo(marginX + contentWidth, y + 46);
      context.stroke();
      setCanvasFont(context, 20, 900);
      context.fillStyle = navyDark;
      context.textAlign = "left";
      context.fillText(title, marginX + 18, y + 13);

      setCanvasFont(context, 19, 400);
      drawTextLines(context, bodyLines, marginX + 18, y + 62, 29, {
        color: ink
      });
    }

    y += boxHeight + 24;
  }

  drawNoteBox("느낀 점", state.notes, 112);
  drawNoteBox("FEEDBACK", state.feedback, 56);

  return Math.ceil(y + 44);
}

async function exportReportImage() {
  const exportButton = nodes.printButton;
  exportButton.disabled = true;
  exportButton.setAttribute("aria-busy", "true");
  nodes.saveStatus.textContent = "이미지 생성 중";

  try {
    const measureCanvas = document.createElement("canvas");
    const measureContext = measureCanvas.getContext("2d");
    const width = 1240;
    const height = drawCanvasReport(measureContext);
    const scale = Math.min(2, 16384 / Math.max(width, height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(width * scale);
    canvas.height = Math.ceil(height * scale);

    const context = canvas.getContext("2d");
    context.scale(scale, scale);
    drawCanvasReport(context, { draw: true, height });
    const blob = await canvasToBlob(canvas);
    showGeneratedImage(blob);
  } finally {
    exportButton.disabled = false;
    exportButton.removeAttribute("aria-busy");
  }
}

function bindEvents() {
  bindTopField(nodes.examTitleInput, "examTitle");
  bindTopField(nodes.rawScoreInput, "rawScore");
  bindTopField(nodes.cutScoreInput, "cutScore");
  bindTopField(nodes.notesInput, "notes");
  bindTopField(nodes.feedbackInput, "feedback");

  nodes.roundEditor.addEventListener("input", (event) => {
    const path = event.target.dataset.path;
    if (!path) return;
    setPath(path, event.target.value);
    renderPreview();
    renderRoundTabs();
    saveReport();
  });

  nodes.roundEditor.addEventListener("click", (event) => {
    const action = event.target.dataset.action;
    if (action !== "delete-row") return;
    deleteRow(activeRoundIndex, Number(event.target.dataset.index));
  });

  nodes.reportRoot.addEventListener("click", (event) => {
    const action = event.target.dataset.action;
    if (action === "add-preview-round") {
      addRound();
      return;
    }

    if (action === "delete-highest-preview-round") {
      deleteHighestRound();
      return;
    }

    if (action === "delete-preview-round") {
      deleteRound(Number(event.target.dataset.roundIndex));
      return;
    }

    if (action === "add-preview-row") {
      addRowToRound(Number(event.target.dataset.roundIndex));
      return;
    }

    if (action === "delete-preview-row") {
      deleteRow(Number(event.target.dataset.roundIndex), Number(event.target.dataset.rowIndex));
    }
  });

  nodes.reportRoot.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;

    const cell = event.target.closest(".cell-editable");
    if (!cell) return;

    event.preventDefault();
    commitEditableValue(cell);
    moveToNextQuestionCell(Number(cell.dataset.roundIndex), Number(cell.dataset.rowIndex));
  });

  nodes.addRowButton.addEventListener("click", addBlankRow);
  nodes.resetButton.addEventListener("click", resetReport);
  nodes.printButton.addEventListener("click", exportReportImage);
  window.addEventListener("resize", checkOverflow);
}

function checkOverflow() {
  requestAnimationFrame(() => {
    nodes.overflowNotice.hidden = true;
    nodes.overflowNotice.textContent = "";
  });
}

bindEvents();
renderPreview();
renderEditor();
saveReport();
