$(document).ready(function () {
    let selectedDate = $("#datePicker").val();
    let selectedBatch = $("#batchDropdown").val();
    let selectedCourse = $("#courseDropdown").val();
  
    function loadStudents() {
        let url = `/get-students?date=${selectedDate}&batch=${selectedBatch}&course=${selectedCourse}`;
        
        $.get(url, function (data) {
            console.log("Received data:", data); // Debug: Check the response
    
            if (data.success && data.students.length > 0) {
                // Load students into QR & Face Scanner section (only attended: true)
                let qrStudentsHtml = '';
                const attendedStudents = data.students.filter(student => student.attended === true);
                if (attendedStudents.length > 0) {
                    attendedStudents.forEach(student => {
                        qrStudentsHtml += `
                            <div class="course-card" data-student="${student.id}">
                                <div class="card-content">
                                    <h5 class="student-name">${student.name} (${student.username})</h5>
                                    <p class="student-email">${student.email}</p>
                                </div>
                                <div class="attendance-options">
                                    <button class="show-qr-btn action-btn"
                                            data-student-id="${student.id}"
                                            data-student-name="${student.name}"
                                            style="background-color: #605ae9; color: white; border: none; padding: 10px 15px; font-size: 16px; cursor: pointer; border-radius: 5px; width: 100%; margin-top: 5px;">
                                        <i class="fa fa-qrcode"></i>
                                    </button>
                                </div>
                            </div>
                        `;
                    });
                    $("#studentList").fadeOut(50, function () {
                        $(this).html(qrStudentsHtml).fadeIn(50);
                    });
                } else {
                    $("#studentList").fadeOut(50, function () {
                        $(this).html('<p class="centered-text">No attended students for QR & Face Scanner.</p>').fadeIn(50);
                    });
                }
    
                // Load all students into Manual Attendance section (regardless of attended status)
                let manualStudentsHtml = '';
                data.students.forEach(student => {
                    manualStudentsHtml += `
                        <div class="course-card" data-student="${student.id}">
                            <div class="card-content">
                                <h5 class="student-name">${student.name} (${student.username})</h5>
                                <p class="student-email">${student.email}</p>
                            </div>
                            <div class="attendance-options">
                                <button class="present-btn action-btn"
                                        data-student="${student.id}"
                                        data-status="present"
                                        style="background-color: #28a745; color: white; border: none; padding: 7px 12px; font-size: 13px; cursor: pointer; border-radius: 5px; ${student.attended ? 'opacity: 0.5; cursor: not-allowed;' : ''}"
                                        ${student.attended ? 'disabled' : ''}>
                                    <i class="fa fa-check"></i>
                                </button>
                                <button class="absent-btn action-btn"
                                        data-student="${student.id}"
                                        data-status="absent"
                                        style="background-color: #dc3545; color: white; border: none; padding: 7px 12px; font-size: 13px; cursor: pointer; border-radius: 5px; ${student.attended ? 'opacity: 0.5; cursor: not-allowed;' : ''}"
                                        ${student.attended ? 'disabled' : ''}>
                                    <i class="fa fa-times"></i>
                                </button>
                                <br />
                                <button class="show-qr-btn action-btn"
                                        data-student-id="${student.id}"
                                        data-student-name="${student.name}"
                                        style="background-color: #605ae9; color: white; border: none; padding: 10px 15px; font-size: 16px; cursor: pointer; border-radius: 5px; width: 100%; margin-top: 5px;">
                                    <i class="fa fa-qrcode"></i>
                                </button>
                            </div>
                        </div>
                    `;
                });
                $("#coursesContainer").fadeOut(50, function () {
                    $(this).html(manualStudentsHtml).fadeIn(50);
                });
            } else {
                $("#studentList").fadeOut(50, function () {
                    $(this).html('<p class="centered-text">No students available in QR & Face Scanner.</p>').fadeIn(50);
                });
                $("#coursesContainer").fadeOut(50, function () {
                    $(this).html('<p class="centered-text">No students found for selected filters.</p>').fadeIn(50);
                });
            }
        }).fail(function (jqXHR, textStatus, errorThrown) {
            console.error("Error fetching students:", textStatus, errorThrown); // Debug: Catch errors
        });
    }
  
    $("#datePicker, #batchDropdown, #courseDropdown").change(function () {
      selectedDate = $("#datePicker").val();
      selectedBatch = $("#batchDropdown").val();
      selectedCourse = $("#courseDropdown").val();
      loadStudents();
    });
  
    // Manual Attendance Button Handlers
    $("#coursesContainer").on("click", ".present-btn, .absent-btn", function () {
        $("#coursesContainer").on("click", ".present-btn, .absent-btn", function () {
            let studentId = $(this).data("student");
            let status = $(this).data("status");
        
            $.post(
                "/mark-attendance",
                {
                    student_id: studentId,
                    date: selectedDate,
                    status: status,
                    csrf_token: "{{ csrf_token }}"
                },
                function (response) {
                    if (response.success) {
                        loadStudents(); // Refresh the list
                    } else {
                        alert("Failed to mark attendance. Try again.");
                    }
                }
            );
        });
    });

    $(document).on("click", ".show-qr-btn", function () {
      const studentId = $(this).data("student-id");
      const studentName = $(this).data("student-name");
  
      $("#qrStudentName").text(studentName);
      $("#qrModal").fadeIn();
  
      const qrContainer = $("#qrCodeContainer");
      qrContainer.empty();
  
      $.ajax({
          url: `/qr/${studentId}`,
          method: "GET",
          dataType: "json",  // Expect JSON response
          success: function (data) {
              const hmacCode = data.hmac_code;  // Use short_hmac_code from JSON
              const student_id = data.student_id
              if (hmacCode) {
                  new QRCode(qrContainer[0], {
                      text: "/verify/student/"+student_id+hmacCode,  // e.g., "7f8b2a1c9d3e4f5a"
                      width: 200,
                      height: 200,
                  });
              } else {
                  qrContainer.text("Error: No HMAC code received.");
              }
          },
          error: function (xhr, status, error) {
              qrContainer.text("Error loading QR code: " + error);
          }
      });
  });

    // Close QR Modal
    $(".close-btn").click(function () {
        $("#qrModal").fadeOut();
    });

    // Close modal when clicking outside
    $(window).click(function (event) {
        if ($(event.target).is("#qrModal")) {
            $("#qrModal").fadeOut();
        }
    });
    // QR Code Popup Functionality
    $(".show-qr-btn").click(function () {
      const studentId = $(this).data("student-id");
      const studentName = $(this).data("student-name");
  
      $("#qrStudentName").text(studentName);
      $("#qrModal").fadeIn();
  
      const qrContainer = $("#qrCodeContainer");
      qrContainer.empty();
  
      new QRCode(qrContainer[0], {
        text: `/verify/student/${studentId}/_verify.edupresence`,
        width: 200,
        height: 200,
      });
    });
  
    $(".close-btn").click(function () {
      $("#qrModal").fadeOut();
    });
  
    $(window).click(function (event) {
      if ($(event.target).is("#qrModal")) {
        $("#qrModal").fadeOut();
      }
    });
  
    // QR Scanner Button (unchanged)
    $("#startScan").click(function () {
      let popup = window.open("", "QRScanner", "width=600,height=600");
      if (!popup) {
        alert("Please allow popups for this site.");
        return;
      }
      popup.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>QR Code Scanner</title>
          <script src="https://cdn.jsdelivr.net/npm/jsqr/dist/jsQR.js"></script>
          <style>
            body { margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: #f0f0f0; }
            video, canvas { max-width: 100%; max-height: 80vh; }
            #scannerResult { text-align: center; color: #333; margin-top: 10px; }
          </style>
        </head>
        <body>
          <video id="video" autoplay></video>
          <canvas id="canvas" style="display: none;"></canvas>
          <div id="scannerResult">Scanning for QR code...</div>
          <script>
            let video = document.getElementById("video");
            let canvas = document.getElementById("canvas");
            let context = canvas.getContext("2d");
            let resultDiv = document.getElementById("scannerResult");
  
            navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
              .then((stream) => {
                video.srcObject = stream;
                video.play();
              })
              .catch((err) => {
                resultDiv.innerText = "Error accessing camera: " + err;
              });
  
            function scanQR() {
              if (!video.videoWidth) {
                requestAnimationFrame(scanQR);
                return;
              }
              canvas.width = video.videoWidth;
              canvas.height = video.videoHeight;
              context.drawImage(video, 0, 0, canvas.width, canvas.height);
              const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
              const code = jsQR(imageData.data, imageData.width, imageData.height);
  
              if (code) {
                resultDiv.innerText = "QR Code Detected: " + code.data;
                window.opener.postMessage({ qrCode: code.data }, "*");
                setTimeout(() => { window.close(); }, 2000);
              }
              requestAnimationFrame(scanQR);
            }
  
            video.addEventListener("play", () => requestAnimationFrame(scanQR));
          </script>
        </body>
        </html>
      `);
    });
  
    window.addEventListener("message", (event) => {
      if (event.data.qrCode) {
        $("#scannerResult").text("QR Code Detected, Verifying...");
        setTimeout(() => {
          openFaceVerificationPopup(event.data.qrCode);
        }, 1000);
      }
    });
  
    function openFaceVerificationPopup(url) {
      let popup = window.open(url, "Face Verification", "width=500,height=600");
      if (!popup) {
        alert("Please allow popups for this site.");
      }
    }
  
    $("#imageInput").change(function (event) {
      const file = event.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
          $("#previewImg").attr("src", e.target.result);
          $("#imagePreview").fadeIn();
        };
        reader.readAsDataURL(file);
      }
    });
  
    loadStudents();
  });