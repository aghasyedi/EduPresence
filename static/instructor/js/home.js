
function initializeCarousel() {
    // Select the carousel inner container and all items
    const carouselInner = document.querySelector(".carousel-inner");
    const items = document.querySelectorAll(".carousel-item");
    if (!carouselInner || items.length === 0) return; // Prevent errors if carousel is missing

    const totalItems = items.length;
    let currentIndex = 0;
    let visibleItems = 3; // Default number (will be updated dynamically)
    let maxIndex = totalItems - visibleItems;

    // Determine the number of visible items based on window width.
    function calculateVisibleItems() {
      const width = window.innerWidth;
      if (width < 600) return 1;
      else if (width < 900) return 2;
      else return 3;
    }

    // Update each item's width and recalculate the max index.
    function updateVisibleItems() {
      visibleItems = calculateVisibleItems();
      items.forEach((item) => {
        item.style.flex = `0 0 ${100 / visibleItems}%`;
      });
      maxIndex = totalItems - visibleItems;
      if (currentIndex > maxIndex) {
        currentIndex = maxIndex;
      }
      updateCarousel();
    }

    // Update the carousel translation based on currentIndex.
    function updateCarousel() {
      carouselInner.style.transform = `translateX(-${currentIndex * (100 / visibleItems)}%)`;
    }

    // Auto-slide functionality (shift one image at a time)
    let interval = setInterval(() => {
      currentIndex++;
      if (currentIndex > maxIndex) {
        currentIndex = 0;
      }
      updateCarousel();
    }, 4000);

    // Left button click: move carousel one slide to the left.
    document.querySelector(".carousel-button.prev").addEventListener("click", () => {
      currentIndex--;
      if (currentIndex < 0) {
        currentIndex = maxIndex;
      }
      updateCarousel();
    });

    // Right button click: move carousel one slide to the right.
    document.querySelector(".carousel-button.next").addEventListener("click", () => {
      currentIndex++;
      if (currentIndex > maxIndex) {
        currentIndex = 0;
      }
      updateCarousel();
    });

    // Recalculate the number of visible items when the window is resized.
    window.addEventListener("resize", updateVisibleItems);

    // Stop auto-slide when navigating away
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) {
        clearInterval(interval);
      } else {
        interval = setInterval(() => {
          currentIndex++;
          if (currentIndex > maxIndex) {
            currentIndex = 0;
          }
          updateCarousel();
        }, 4000);
      }
    });

    // Initial setup
    updateVisibleItems();
  }

  // Reinitialize the carousel when new content is loaded
  $(document).on("DOMSubtreeModified", "#content", function () {
    initializeCarousel();
  });

  // Initialize carousel on page load
  $(document).ready(function () {
    initializeCarousel();
  });