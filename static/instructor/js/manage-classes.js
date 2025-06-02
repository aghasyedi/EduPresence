
$(document).ready(function () {
  let previousLeftPage = "/manage-classes";
  let defaultRightPage = "/manage-class-default-right";

  function loadContent(page) {
    let selectedBatch = $("#batchDropdown").val(); // Store selected batch
    let scrollPosition = $(window).scrollTop(); // Store scroll position

    $("#bcontentL").fadeOut(50, function () {
      $(this)
        .empty()
        .load(page, function () {
          $(this).fadeIn(50).css("min-height", "auto");

          let urlParams = new URLSearchParams(page.split("?")[1]);
          let hasClassId = urlParams.has("id");

          $("#back-batches").toggle(hasClassId);
          // $("#bcontentR").load(hasClassId ? "/right-course-videos" : defaultRightPage);
          $("#bcontentR").load(defaultRightPage);

          // Restore previous batch selection
          let selectedBatch = localStorage.getItem("selectedBatch");
          if (selectedBatch) {
            $("#batchDropdown").val(selectedBatch).change();
          } else {
            // Select the first available batch if nothing is stored
            let firstBatch = $("#batchDropdown option:not(:first)").first().val();
            if (firstBatch) {
              $("#batchDropdown").val(firstBatch).change();
            }
          }
        });
    });
  }

  // Load initial content
  $("#bcontentL").load("/manage-class-cards", function () {
    let selectedBatch = localStorage.getItem("selectedBatch");
    if (selectedBatch) {
      $("#batchDropdown").val(selectedBatch).change();
    } else {
      let firstBatch = $("#batchDropdown option:not(:first)").first().val();
      if (firstBatch) {
        $("#batchDropdown").val(firstBatch).change();
      }
    }
  });

  $("#bcontentR").load(defaultRightPage);

  // Handle course clicks
  $("#bcontentL").on("click", ".bcard-check", function () {
    previousLeftPage = "/manage-classes";
    loadContent($(this).data("page"));
  });

  // Handle back button click
  $(document).on("click", "#back-batches", function (e) {
    e.preventDefault();
    loadContent(previousLeftPage);
    $("#bcontentR").load(defaultRightPage);
  });

  // Handle batches click
  $("#batches").click(function (e) {
    e.preventDefault();
    loadContent("/manage-classes");
  });

  // Handle home button click
  $("#home-button").click(function () {
    window.location.href = "/dashboard#manage-classes";
  });
});

