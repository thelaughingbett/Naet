let regForm!: HTMLFormElement;
let fieldsets!: NodeListOf<HTMLFieldSetElement>;
let progressCont!: HTMLDivElement;
let stepIndicators!: NodeListOf<HTMLLIElement>;
let progress!: HTMLDivElement;
let currentStep = 0;
let nextBtn!: HTMLButtonElement;
let prevBtn!: HTMLButtonElement;
let submitBtn!: HTMLButtonElement;
let mainContainer!: HTMLElement;
let schoolSelect!: HTMLSelectElement;
let departmentSelect!: HTMLSelectElement;
let departmentsData!: object[];
let programmesData!: object[];

document.addEventListener("DOMContentLoaded", () => {
  regForm = document.getElementById("reg-form") as HTMLFormElement;
  fieldsets = regForm.querySelectorAll(
    "fieldset",
  ) as NodeListOf<HTMLFieldSetElement>;
  progressCont = regForm.querySelector("#progress-container") as HTMLDivElement;
  let ul = progressCont.querySelector("ul") as HTMLUListElement;

  let inputsFromForm = regForm.querySelectorAll("input");

  progress = document.getElementById("progress") as HTMLDivElement;
  mainContainer = regForm.querySelector("main") as HTMLElement;

  const updateProgress = () => {
    let width = currentStep / (fieldsets.length - 1);

    progress.style.transform = `scaleX(${width})`;

    mainContainer.style.height = fieldsets[currentStep].offsetHeight + "px";

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

  nextBtn = document.querySelector(".next-btn") as HTMLButtonElement;

  prevBtn = document.querySelector(".prev-btn") as HTMLButtonElement;
  submitBtn = document.querySelector(".submit-btn") as HTMLButtonElement;

  const isValid = () => {
    let inputs = fieldsets[currentStep].querySelectorAll("input");
    return [...inputs].every((input) => input.reportValidity());
  };

  nextBtn.addEventListener("click", (event) => {
    event.preventDefault();

    if (!isValid()) return;

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
      const focusedStep = [...fieldsets].findIndex((fieldset) =>
        fieldset.contains(e.target as HTMLElement),
      );

      if (focusedStep !== -1 && focusedStep !== currentStep) {
        if (!isValid()) return;
        currentStep = focusedStep;
        updateProgress();
      }

      mainContainer.scrollTop = 0;
      mainContainer.scrollLeft = 0;
    });
  });

  (async () => {
    document.documentElement.style.setProperty(
      "--steps",
      `${fieldsets.length}`,
    );

    fieldsets.forEach((field, index) => {
      let legend = field.querySelector("legend") as HTMLLegendElement;
      let li = document.createElement("li");
      if (index === 0) {
        li.classList.add("current");
        field.classList.add("current");
      }
      li.innerText = legend.innerText;
      ul.appendChild(li);
    });

    stepIndicators = ul.querySelectorAll("li") as NodeListOf<HTMLLIElement>;

    updatebuttons();
  })();
  selectEvents();
});

function selectEvents() {
  schoolSelect = document.getElementById("id_school") as HTMLSelectElement;

  departmentSelect = document.getElementById(
    "id_department",
  ) as HTMLSelectElement;

  const programmeSelect = document.getElementById(
    "id_programme",
  ) as HTMLSelectElement;

  const tempDept =
    document.getElementById("departments-data")?.textContent ?? "[]";
  const tempProgramme =
    document.getElementById("programmes-data")?.textContent ?? "[]";
  departmentsData = JSON.parse(tempDept);
  programmesData = JSON.parse(tempProgramme);

  schoolSelect.addEventListener("change", function () {
    const selectedSchoolId = this.value;
    console.log(selectedSchoolId);
    const filtered = departmentsData.filter(
      (d: any) => d.school_id === selectedSchoolId,
    );

    // Clear and repopulate department dropdown
    departmentSelect.innerHTML = '<option value="">---------</option>';
    filtered.forEach((d: any) => {
      const option = new Option(d.department_name, d.record_id);
      departmentSelect!.appendChild(option);
    });
  });

  departmentSelect.addEventListener("change", function () {
    const selectedDepartment = this.value;
    const filteredProgrammes = programmesData.filter(
      (d: any) => d.department_id === selectedDepartment,
    );

    programmeSelect!.innerHTML = '<option value="">---------</option>';
    filteredProgrammes.forEach((programme: any) => {
      const option = new Option(programme.programme_name, programme.record_id);
      programmeSelect.appendChild(option);
    });
  });
}

// const pattern: RegExp = new RegExp("/\^w+@ \w+(\.\w{3}/", "g");
