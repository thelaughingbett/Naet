"use strict";
let regForm;
let fieldsets;
let progressCont;
let stepIndicators;
let progress;
let currentStep = 0;
let nextBtn;
let prevBtn;
let submitBtn;
let mainContainer;
let schoolSelect;
let departmentSelect;
let departmentsData;
let programmesData;
document.addEventListener("DOMContentLoaded", () => {
    regForm = document.getElementById("reg-form");
    fieldsets = regForm.querySelectorAll("fieldset");
    progressCont = regForm.querySelector("#progress-container");
    let ul = progressCont.querySelector("ul");
    let inputsFromForm = regForm.querySelectorAll("input");
    progress = document.getElementById("progress");
    mainContainer = regForm.querySelector("main");
    const updateProgress = () => {
        let width = currentStep / (fieldsets.length - 1);
        progress.style.transform = `scaleX(${width})`;
        mainContainer.style.height = fieldsets[currentStep].offsetHeight + "px";
        console.log(mainContainer.style.height);
        stepIndicators.forEach((indicator, index) => {
            indicator.classList.toggle("current", index === currentStep);
            indicator.classList.toggle("done", currentStep > index);
        });
        fieldsets.forEach((field, index) => {
            field.style.transform = `translateX(-${currentStep * 100}%)`;
            field.classList.toggle("current", index === currentStep);
        });
        updatebuttons();
    };
    const updatebuttons = () => {
        prevBtn.hidden = currentStep === 0;
        nextBtn.hidden = currentStep >= fieldsets.length - 1;
        submitBtn.hidden = !nextBtn.hidden;
    };
    nextBtn = document.querySelector(".next-btn");
    prevBtn = document.querySelector(".prev-btn");
    submitBtn = document.querySelector(".submit-btn");
    const isValid = () => {
        let inputs = fieldsets[currentStep].querySelectorAll("input");
        return [...inputs].every((input) => input.reportValidity());
    };
    nextBtn.addEventListener("click", (event) => {
        event.preventDefault();
        if (!isValid())
            return;
        if (currentStep < fieldsets.length - 1) {
            currentStep++;
            updateProgress();
        }
    });
    prevBtn.addEventListener("click", (event) => {
        event.preventDefault();
        if (currentStep > 0) {
            currentStep--;
            updateProgress();
        }
    });
    inputsFromForm.forEach((input) => {
        input.addEventListener("focus", (e) => {
            const focusedStep = [...fieldsets].findIndex((fieldset) => fieldset.contains(e.target));
            if (focusedStep !== -1 && focusedStep !== currentStep) {
                if (!isValid())
                    return;
                currentStep = focusedStep;
                updateProgress();
            }
            mainContainer.scrollTop = 0;
            mainContainer.scrollLeft = 0;
        });
    });
    (async () => {
        document.documentElement.style.setProperty("--steps", `${fieldsets.length}`);
        fieldsets.forEach((field, index) => {
            let legend = field.querySelector("legend");
            let li = document.createElement("li");
            if (index === 0) {
                li.classList.add("current");
                field.classList.add("current");
            }
            li.innerText = legend.innerText;
            ul.appendChild(li);
        });
        stepIndicators = ul.querySelectorAll("li");
        updatebuttons();
        updateProgress();
        selectEvents();
    })();
});
function selectEvents() {
    schoolSelect = document.getElementById("id_school");
    departmentSelect = document.getElementById("id_department");
    const programmeSelect = document.getElementById("id_programme");
    const tempDept = document.getElementById("departments-data")?.textContent ?? "[]";
    const tempProgramme = document.getElementById("programmes-data")?.textContent ?? "[]";
    departmentsData = JSON.parse(tempDept);
    programmesData = JSON.parse(tempProgramme);
    schoolSelect.addEventListener("change", function () {
        const selectedSchoolId = this.value;
        console.log(selectedSchoolId);
        const filtered = departmentsData.filter((d) => d.school_id === selectedSchoolId);
        // Clear and repopulate department dropdown
        departmentSelect.innerHTML = '<option value="">---------</option>';
        filtered.forEach((d) => {
            const option = new Option(d.department_name, d.record_id);
            departmentSelect.appendChild(option);
        });
    });
    departmentSelect.addEventListener("change", function () {
        const selectedDepartment = this.value;
        const filteredProgrammes = programmesData.filter((d) => d.department_id === selectedDepartment);
        programmeSelect.innerHTML = '<option value="">---------</option>';
        filteredProgrammes.forEach((programme) => {
            const option = new Option(programme.programme_name, programme.record_id);
            programmeSelect.appendChild(option);
        });
    });
}
// const pattern: RegExp = new RegExp("/\^w+@ \w+(\.\w{3}/", "g");
