$(document).ready(function () {
  const $dropdown = $("#batchDropdown");
  const $noBatchMessage = $("#noBatchMessage");
  const $coursesHeading = $("#coursesHeading");
  const $videosList = $("#videosList");
  const $videosHeading = $("#videosHeading");
  const $viewClassmatesBtn = $("#viewClassmatesBtn");
  const $modal = $("#classmatesModal");
  const $studentsList = $("#studentsList");
  const $closeBtn = $(".close");

  function updateCoursesList(batchId) {
      $noBatchMessage.toggle(batchId === "#");
      $(".batch-courses").hide().filter(`[data-batch="${batchId}"]`).show();
      
      if (batchId !== "#") {
          $coursesHeading.text(`Courses in ${$dropdown.find(":selected").text()}`);
          $viewClassmatesBtn.show();
      } else {
          $coursesHeading.text("Course List Here");
          $viewClassmatesBtn.hide();
      }

      $videosList.html("<p class='centered-text'>Select a course to view and manage videos.</p>");
      $videosHeading.text("Course Videos");
  }

  let savedBatch = localStorage.getItem("selectedBatch") || "#";
  if ($dropdown.find(`option[value="${savedBatch}"]`).length === 0) {
      savedBatch = "#";
      localStorage.setItem("selectedBatch", "#");
  }

  $dropdown.val(savedBatch);
  updateCoursesList(savedBatch);

  $dropdown.on("change", function () {
      const batchId = $(this).val();
      updateCoursesList(batchId);
      localStorage.setItem("selectedBatch", batchId);
  });

  $viewClassmatesBtn.on("click", () => {
      const batchId = $dropdown.val();
      if (batchId === "#") return;

      $.get(`/get_batch_students/${batchId}`, (data) => {
          if (data.error) {
              $studentsList.html("<p class='centered-text'>Error loading students</p>");
          } else {
              const studentsHtml = data.students
                  .map(
                      (student) => `
                      <div class="student-item">
                          <strong>${student.name}</strong><br>
                          <span>${student.email}</span>
                          <a title="Mail - ${student.name}" href="mailto:${student.email}">
                              <i class="fa-regular fa-envelope"></i>
                          </a>
                      </div>
                  `
                  )
                  .join("");
              $studentsList.html(studentsHtml || "<p class='centered-text'>No students found</p>");
          }
          $modal.show();
      }).fail(() => {
          $studentsList.html("<p class='centered-text'>Error loading students</p>");
          $modal.show();
      });
  });

  $closeBtn.on("click", () => {
      $modal.hide();
  });

  $(window).on("click", (e) => {
      if (e.target == $modal[0]) {
          $modal.hide();
      }
  });

  $("#addCourse, #addVideo").on("click", function () {
      const idParam = $(this).attr("id") === "addCourse" ? "course" : "video";
      window.open("/edit-course-video?id=" + idParam, "_blank");
  });

  $(document).on("click", ".course-card", function (e) {
      if ($(e.target).hasClass("edit-btn")) return;
      const courseId = $(this).data("course");
      const courseName = $(this).find(".course-title").text().trim();

      let videosHtml = videos
          .filter((video) => String(video[1]) === String(courseId))
          .map(
              (video) => `
              <div class="lecture-card" data-lecture="${video[0]}">
                  <img src="${video[5]}" alt="${video[2]}" onclick="window.open('/class?id=${video[0]}', '_blank'); event.stopPropagation();">
                  <div>
                      <h6>${video[2]}</h6>
                      <p>${video[3].slice(0, 26)}...</p>
                  </div>
                  <button class="edit-btn" onclick="window.open('/edit-course-video?id=${video[0]}', '_blank'); event.stopPropagation();">
                      <i class="fa fa-edit"></i> Edit
                  </button>
              </div>
          `
          )
          .join("");

      $videosList.html(videosHtml || "<p class='centered-text'>No videos available.</p>");
      $videosHeading.text(`Lectures | ${courseName}`);
  });

  $(document).on("click", ".lecture-card", function (e) {
      if ($(e.target).hasClass("edit-btn")) return;
      window.open("/class?id=" + $(this).data("lecture"), "_blank");
  });
});