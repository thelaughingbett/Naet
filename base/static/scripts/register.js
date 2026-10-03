"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("reg-form");
  const fieldsets = [...form.querySelectorAll("main fieldset")];
  const progress = document.getElementById("progress");
  const stepsUl = form.querySelector("#progress-container ul");
  const prevBtn = form.querySelector(".prev-btn");
  const nextBtn = form.querySelector(".next-btn");
  const submitBtn = form.querySelector(".submit-btn");
  const controls = form.querySelector(".controls");

  const TOTAL = fieldsets.length;
  let current = 0;
  const visited = new Set([0]);

  stepsUl.innerHTML = "";
  fieldsets.forEach((fs, i) => {
    const li = document.createElement("li");
    li.dataset.step = String(i);
    li.textContent =
      fs.querySelector("legend")?.textContent.trim() || `Step ${i + 1}`;
    stepsUl.appendChild(li);
  });
  const pills = [...stepsUl.querySelectorAll("li")];

  function goTo(index, scroll = true) {
    if (index < 0 || index >= TOTAL) return;
    current = index;
    visited.add(index);
    fieldsets.forEach((fs, i) => fs.classList.toggle("active", i === current));
    progress.style.setProperty("--p", ((current + 1) / TOTAL) * 100 + "%");
    pills.forEach((li, i) => {
      li.classList.toggle("active", i === current);
      li.classList.toggle("done", visited.has(i) && i !== current);
    });
    const isLast = current === TOTAL - 1;
    prevBtn.disabled = current === 0;
    nextBtn.style.display = isLast ? "none" : "";
    submitBtn.classList.toggle("show", isLast);
    controls.classList.toggle("has-submit", isLast);
    if (scroll) form.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function isValidStep() {
    for (const f of fieldsets[current].querySelectorAll(
      "input, select, textarea",
    )) {
      if (!f.checkValidity()) {
        f.reportValidity();
        return false;
      }
    }
    return true;
  }

  nextBtn.addEventListener("click", (e) => {
    e.preventDefault();
    if (isValidStep() && current < TOTAL - 1) goTo(current + 1);
  });
  prevBtn.addEventListener("click", (e) => {
    e.preventDefault();
    if (current > 0) goTo(current - 1);
  });
  pills.forEach((li) =>
    li.addEventListener("click", () => goTo(Number(li.dataset.step))),
  );

  form.addEventListener("submit", (e) => {
    for (let i = 0; i < TOTAL; i++) {
      for (const f of fieldsets[i].querySelectorAll(
        "input, select, textarea",
      )) {
        if (!f.checkValidity()) {
          e.preventDefault();
          goTo(i);
          requestAnimationFrame(() => f.reportValidity());
          return;
        }
      }
    }
    // valid: let the browser POST to Django
  });

  // After a server-side validation failure, open the first step with errors
  const firstError = fieldsets.findIndex((fs) =>
    fs.querySelector(".errorlist"),
  );
  for (let i = 0; i <= firstError; i++) visited.add(i);
  goTo(Math.max(firstError, 0), false);
});
