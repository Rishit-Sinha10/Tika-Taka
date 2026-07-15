// static/js/game.js
let score = 0;
let countdown = null;
let timeLeft = 10;
let currentQuestion = null;

const qtext = document.getElementById("qtext");
const qimg = document.getElementById("qimg");
const opts = document.querySelectorAll(".opt");
const feedback = document.getElementById("feedback");
const timerEl = document.getElementById("timer");
const scoreEl = document.getElementById("score");
const nextBtn = document.getElementById("nextBtn");
const categorySel = document.getElementById("category");
const difficultySel = document.getElementById("difficulty");

function startTimer() {
  clearInterval(countdown);
  timeLeft = 10;
  timerEl.textContent = timeLeft;
  countdown = setInterval(() => {
    timeLeft--;
    timerEl.textContent = timeLeft;
    if (timeLeft <= 0) {
      clearInterval(countdown);
      lockOptions();
      feedback.textContent = "Time's up!";
    }
  }, 1000);
}

async function fetchQuestion() {
  feedback.textContent = "";
  opts.forEach(b => { b.classList.remove("correct","wrong"); b.disabled = false; });
  const params = new URLSearchParams();
  if (categorySel.value) params.append("category", categorySel.value);
  if (difficultySel.value) params.append("difficulty", difficultySel.value);
  const res = await fetch(`/api/question?${params.toString()}`);
  const data = await res.json();
  if (data.error) { qtext.textContent = "No questions available."; return; }
  currentQuestion = data;
  qtext.textContent = data.text;
  const keys = ["A","B","C","D"];
  opts.forEach((b, i) => b.textContent = data.options[keys[i]]);
  if (data.image_url) {
    qimg.src = data.image_url; qimg.style.display = "block";
  } else {
    qimg.style.display = "none";
  }
  startTimer();
}

function lockOptions() { opts.forEach(b => b.disabled = true); }

async function submitAnswer(selected) {
  lockOptions();
  clearInterval(countdown);
  const res = await fetch("/api/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question_id: currentQuestion.id,
      selected_option: selected
    })
  });
  const data = await res.json();
  if (data.correct) {
    feedback.textContent = `Correct! +${data.points}`;
    score += data.points;
    document.querySelector(`.opt[data-opt="${selected}"]`).classList.add("correct");
  } else {
    feedback.textContent = `Wrong. +0`;
    document.querySelector(`.opt[data-opt="${selected}"]`).classList.add("wrong");
    // highlight correct
    const correctKey = Object.entries(currentQuestion.options)
      .find(([k, v]) => k === currentQuestion.correct)?.[0]; // optional if you expose correct
  }
  scoreEl.textContent = `Score: ${score}`;
}

opts.forEach(b => b.addEventListener("click", () => submitAnswer(b.dataset.opt)));
nextBtn.addEventListener("click", fetchQuestion);
window.addEventListener("load", fetchQuestion);