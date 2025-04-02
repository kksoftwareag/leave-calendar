// Automatically scroll to today's column
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
  
  function toggleTheme() {
    document.body.classList.toggle("dark-mode");
    const themeToggle = document.getElementById("theme-toggle");
  
    if (document.body.classList.contains("dark-mode")) {
      themeToggle.innerText = "Light Mode ☀️";
      localStorage.setItem("theme", "dark-mode");
    } else {
      themeToggle.innerText = "Dark Mode 🌙";
      localStorage.removeItem("theme");
    }
  }
  
  const currentTheme = localStorage.getItem("theme");
  const themeToggleButton = document.getElementById("theme-toggle");
  
  if (currentTheme === "dark-mode") {
    document.body.classList.add("dark-mode");
    themeToggleButton.innerText = "Light Mode ☀️";
  } else {
    themeToggleButton.innerText = "Dark Mode 🌙";
  }
  
  themeToggleButton.addEventListener("click", toggleTheme);
  