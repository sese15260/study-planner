// StudyMate의 화면 동작을 담당하는 파일입니다.
// 입력값을 확인한 뒤 /api/recommend로 보내고, AI가 만든 계획을 화면에 표시합니다.

const studyForm = document.getElementById("study-form");
const submitButton = document.getElementById("submit-button");
const formMessage = document.getElementById("form-message");
const resultArea = document.getElementById("result-area");
const loadingState = document.getElementById("loading-state");
const resultError = document.getElementById("result-error");
const resultErrorMessage = document.getElementById("result-error-message");
const planResult = document.getElementById("plan-result");
const planSummary = document.getElementById("plan-summary");
const planPeriod = document.getElementById("plan-period");
const todoList = document.getElementById("todo-list");
// 날짜별 계획은 AI가 길게 작성할 수 있어 충분한 응답 시간을 둡니다.
const REQUEST_TIMEOUT_MS = 90000;
const DEPLOYED_API_URL = "https://studymate-navy.vercel.app/api/recommend";

studyForm.addEventListener("submit", handlePlanSubmit);

async function handlePlanSubmit(event) {
  event.preventDefault();
  clearMessage();

  const formData = getFormValues();
  const validationMessage = validateForm(formData);

  if (validationMessage) {
    showMessage(validationMessage);
    return;
  }

  showLoading();
  setSubmitState(true);

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(getApiUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
      signal: controller.signal
    });

    const responseData = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(responseData.error || "AI 계획을 만드는 중 오류가 발생했습니다.");
    }

    if (!isValidPlan(responseData)) {
      throw new Error("AI 응답 형식이 올바르지 않습니다. 잠시 후 다시 시도해주세요.");
    }

    renderPlan({ ...formData, ...responseData });
  } catch (error) {
    const errorMessage = error.name === "AbortError"
      ? "AI 응답이 오래 걸리고 있습니다. 잠시 후 다시 시도해주세요."
      : error.message || "네트워크 연결을 확인한 뒤 다시 시도해주세요.";

    showResultError(errorMessage);
  } finally {
    window.clearTimeout(timeoutId);
    setSubmitState(false);
  }
}

// Live Server는 Python 파일을 실행할 수 없습니다.
// 따라서 localhost에서만 이미 배포된 API를 사용하고,
// Vercel 사이트에서는 현재 사이트의 /api/recommend를 그대로 사용합니다.
function getApiUrl() {
  const localHosts = ["localhost", "127.0.0.1"];

  if (localHosts.includes(window.location.hostname)) {
    return DEPLOYED_API_URL;
  }

  return "/api/recommend";
}

function getFormValues() {
  return {
    learnerType: document.getElementById("learner-type").value,
    subject: document.getElementById("subject").value.trim(),
    amount: document.getElementById("amount").value.trim(),
    startDate: document.getElementById("start-date").value,
    goalDate: document.getElementById("goal-date").value,
    studyTime: document.getElementById("study-time").value
  };
}

function validateForm(formData) {
  const hasEmptyValue = Object.values(formData).some((value) => !value);

  if (hasEmptyValue) {
    return "필수 정보를 입력해주세요.";
  }

  if (formData.goalDate < formData.startDate) {
    return "목표일은 시작일 이후로 선택해주세요.";
  }

  if (getStudyDays(formData.startDate, formData.goalDate) > 60) {
    return "계획 기간은 최대 60일까지 선택해주세요.";
  }

  return "";
}

function getStudyDays(startDate, goalDate) {
  const start = new Date(`${startDate}T00:00:00`);
  const goal = new Date(`${goalDate}T00:00:00`);
  return Math.floor((goal - start) / (1000 * 60 * 60 * 24)) + 1;
}

function showLoading() {
  resultArea.hidden = false;
  loadingState.hidden = false;
  resultError.hidden = true;
  planResult.hidden = true;
}

function showResultError(message) {
  resultArea.hidden = false;
  loadingState.hidden = true;
  planResult.hidden = true;
  resultErrorMessage.textContent = message;
  resultError.hidden = false;
  resultError.scrollIntoView({ behavior: "smooth", block: "center" });
  resultError.focus({ preventScroll: true });
}

function setSubmitState(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "AI 계획 생성 중..." : "공부 계획 만들기";
}

function isValidPlan(plan) {
  return Array.isArray(plan.dailyPlans)
    && plan.dailyPlans.length > 0
    && plan.dailyPlans.every((dailyPlan) => (
      typeof dailyPlan.date === "string"
      && Array.isArray(dailyPlan.tasks)
      && dailyPlan.tasks.length > 0
    ));
}

function renderPlan(plan) {
  loadingState.hidden = true;
  resultError.hidden = true;
  planResult.hidden = false;
  planSummary.textContent = `${plan.subject} · ${plan.learnerType} · 하루 ${plan.studyTime}`;
  planPeriod.textContent = `${formatFullDate(plan.startDate)} ~ ${formatFullDate(plan.goalDate)}`;
  todoList.replaceChildren();

  plan.dailyPlans.forEach((dailyPlan) => {
    const dayCard = document.createElement("article");
    dayCard.className = "todo-day";

    const dateTitle = document.createElement("strong");
    dateTitle.className = "todo-date";
    dateTitle.textContent = formatKoreanDate(dailyPlan.date);

    const tasks = document.createElement("ul");
    dailyPlan.tasks.forEach((task) => {
      const taskItem = document.createElement("li");
      taskItem.textContent = task;
      tasks.append(taskItem);
    });

    dayCard.append(dateTitle, tasks);
    todoList.append(dayCard);
  });

  resultArea.scrollIntoView({ behavior: "smooth", block: "start" });
}

function formatFullDate(dateString) {
  const [year, month, day] = dateString.split("-");
  return `${year}-${month}-${day}`;
}

function formatKoreanDate(dateString) {
  const [, month, day] = dateString.split("-");
  return `${Number(month)}월 ${Number(day)}일`;
}

function showMessage(message) {
  formMessage.textContent = message;
  document.getElementById("study-form").querySelector(":invalid")?.focus();
}

function clearMessage() {
  formMessage.textContent = "";
}
