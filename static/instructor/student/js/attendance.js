
$(document).ready(function () {
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
            $.ajax({
                url: event.data.qrCode,
                method: "GET",
                dataType: "json",
                success: function (response) {
                    if (response.success) {
                        $("#scannerResult").text("Attendance Marked Successfully!");
                        $("#verificationStatus").text("Verified").css("color", "#28a745");
                        $("#verificationInfo").fadeIn();
                        updateAttendanceSummary();
                    } else {
                        $("#scannerResult").text("Verification Failed: " + (response.message || "Unknown error"));
                        $("#verificationStatus").text("Not Verified").css("color", "#dc3545");
                        $("#verificationInfo").fadeIn();
                    }
                },
                error: function () {
                    $("#scannerResult").text("Error connecting to server.");
                    $("#verificationStatus").text("Error").css("color", "#dc3545");
                    $("#verificationInfo").fadeIn();
                }
            });
        }
    });

    function updateAttendanceSummary() {
        $.get("/get_attendance_summary", function (data) {
            if (data.success) {
                $("#totalAttended").text(data.total_attended);
                $("#totalClasses").text(data.total_classes);
                $("#attendancePercentage").text((data.total_attended / data.total_classes * 100).toFixed(2) + "%");
            }
        });
    }
});