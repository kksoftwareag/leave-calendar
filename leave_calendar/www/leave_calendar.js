function today() {
  const currentDay = document.getElementById("today");
  if (currentDay) {
    currentDay.scrollIntoView({
      inline: "center",
      block: "nearest",
    });
  }
}
today();

function changeYear(direction) {
  var currentYear = parseInt(
    document.querySelector(".current-year-display").textContent,
  );
  var newYear = currentYear + direction;

  var department = document.getElementById("departmentFilter").value;
  var url = new URL(window.location.href);
  url.searchParams.set("year", newYear);
  if (department !== "all") {
    url.searchParams.set("department", department);
  } else {
    url.searchParams.delete("department");
  }

  window.location.href = url.toString();
}

function updateDepartmentFilter() {
  var department = document.getElementById("departmentFilter").value;
  var url = new URL(window.location.href);

  if (department !== "all") {
    url.searchParams.set("department", department);
  } else {
    url.searchParams.delete("department");
  }
  window.location.href = url.toString();
}

function applyThemeBasedOnUserSetting() {
  const deskTheme = document.getElementById("desk-theme")?.value;

  if (deskTheme === "D") {
    document.body.classList.add("dark-mode");
  } else if (deskTheme === "L") {
    document.body.classList.remove("dark-mode");
  } else if (deskTheme === "A") {
    const prefersDark =
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (prefersDark) {
      document.body.classList.add("dark-mode");
    } else {
      document.body.classList.remove("dark-mode");
    }
  }
}

applyThemeBasedOnUserSetting();
