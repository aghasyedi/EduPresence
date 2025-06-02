window.addEventListener("scroll", function () {
    const navbar = document.querySelector(".navbar");
    if (window.scrollY > 50) {
      navbar.classList.add("scrolled"); // Adds transparency
    } else {
      navbar.classList.remove("scrolled"); // Resets to solid
    }
  });
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("mouseenter", function () {
      const next = this.nextElementSibling; // Get the next nav-item
      const beforeElement = this.querySelector("b:nth-child(1)");
      const nextBeforeElement = next ? next.querySelector("b:nth-child(1)") : null;

      if (beforeElement) {
        beforeElement.style.setProperty("--before-bg", "rgba(255, 255, 255, 0.8)"); // Change background
      }
      if (nextBeforeElement) {
        nextBeforeElement.style.setProperty("--before-bg", "rgba(255, 255, 255, 0.8)");
      }
    });

    item.addEventListener("mouseleave", function () {
      const next = this.nextElementSibling; // Get the next nav-item
      const beforeElement = this.querySelector("b:nth-child(1)");
      const nextBeforeElement = next ? next.querySelector("b:nth-child(1)") : null;

      if (beforeElement) {
        beforeElement.style.setProperty("--before-bg", ""); // Reset background
      }
      if (nextBeforeElement) {
        nextBeforeElement.style.setProperty("--before-bg", "");
      }
    });
  });