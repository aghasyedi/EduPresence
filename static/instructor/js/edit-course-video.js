
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.copy-btn').forEach(b => b.addEventListener('click', () => copyText(b.dataset.target, b)));
    document.getElementById('videoThumbnail').addEventListener('input', e => document.getElementById('videoThumbnailPreview').src = e.target.value);
    document.getElementById('addVideoThumbnail').addEventListener('input', e => document.getElementById('addVideoThumbnailPreview').src = e.target.value);


    document.getElementById('editFormContent').addEventListener('submit', function(e) {
      e.preventDefault();
      let formData = new FormData(this);
      const isCourseVisible = document.getElementById('courseEditForm').style.display === 'block';
      const isVideoVisible = document.getElementById('videoEditForm').style.display === 'block';

      if (isCourseVisible) {
          const courseId = document.querySelector('#courseList li.selected')?.dataset.courseId;
          if (courseId) {
              const courseTitle = document.getElementById('courseTitle').value.trim();
              const courseDescription = document.getElementById('courseDescription').value.trim();
              const instructorAdditional = document.getElementById('instructorAdditional').value.trim();

              if (!courseTitle || !courseDescription) {
                  showToast('Please fill all required course fields.', 'warning');
                  return;
              }

              formData.append('courseId', courseId);
              formData.append('courseTitle', courseTitle);
              formData.append('courseDescription', courseDescription);
              formData.append('instructorAdditional', instructorAdditional);
              
          } else {
              showToast('No course selected.', 'warning');
              return;
          }
      } else if (isVideoVisible) {
          const videoId = document.querySelector('#videos li.selected')?.dataset.videoId;
          if (videoId) {
              const videoTitle = document.getElementById('videoTitle').value.trim();
              const videoDescription = document.getElementById('videoDescription').value.trim();
              const videoUrl = document.getElementById('videoUrl').value.trim();
              const videoThumbnail = document.getElementById('videoThumbnail').value.trim();
              const videoDuration = document.getElementById('videoDuration').value.trim();
              

              if (!videoTitle || !videoDescription || !videoUrl || !videoThumbnail || !videoDuration) {
                  showToast('Please fill all required video fields.', 'warning');
                  return;
              }

              formData.append('videoId', videoId);
              formData.append('videoTitle', videoTitle);
              formData.append('videoDescription', videoDescription);
              formData.append('videoUrl', videoUrl);
              formData.append('videoThumbnail', videoThumbnail);
              formData.append('videoDuration', videoDuration);
          } else {
              showToast('No video selected.', 'warning');
              return;
          }
      } else {
          showToast('No form visible to submit.', 'warning');
          return;
      }

      fetch('/edit-course-video', {
          method: 'POST',
          body: formData,
          headers: {
              'X-CSRF-Token': csrfToken
          }
      })
      .then(response => {
          if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
      })
      .then(data => {
          document.getElementById('formMessage').textContent = data.message;
          showToast(data.message, data.message.includes('success') ? 'success' : 'warning');
          if (data.message.includes('success')) setTimeout(() => location.reload(), 1500);
      })
      .catch(error => {
          console.error('Error:', error);
          showToast('An error occurred: ' + error.message, 'warning');
      });
  });

    ['addCourseForm', 'addVideoForm'].forEach(id => {
      document.getElementById(id).addEventListener('submit', e => {
        e.preventDefault();
        if (!validateForm(id)) return;
        const formData = new FormData(e.target);
        fetch('/add-video-course', {
          method: 'POST',
          body: formData
        })
          .then(r => {
            if (!r.ok) throw new Error(`HTTP error! status: ${r.status}`);
            return r.json();
          })
          .then(d => {
            const msgEl = document.getElementById(`${id === 'addCourseForm' ? 'addCourse' : 'addVideo'}Message`);
            msgEl.textContent = d.message;
            showToast(d.message, d.message.includes('success') ? 'success' : 'warning');
            if (d.message.includes('success')) setTimeout(() => { closeModal(`${id === 'addCourseForm' ? 'addCourse' : 'addVideo'}Modal`); location.reload(); }, 1500);
          })
          .catch(e => {
            console.error('Error:', e);
            showToast('An error occurred: ' + e.message, 'warning');
          });
      });
    });

    // Auto-scroll logic for selected course or video
    if (urlId) {
      if (urlId === 'course' || urlId === 'video') {
        openModal(urlId === 'course' ? 'addCourseModal' : 'addVideoModal');
      } else {
        const course = courses.find(c => c[0] == urlId);
        const video = videos.find(v => v[0] == urlId);

        if (course) {
          const courseElement = document.querySelector(`[data-course-id='${urlId}']`);
          selectCourse(urlId, courseElement);
          // Scroll to the selected course
          if (courseElement) {
            courseElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        } else if (video) {
          const courseId = video[1];
          const courseElement = document.querySelector(`[data-course-id='${courseId}']`);
          if (courseElement) {
            selectCourse(courseId, courseElement);
            // Scroll to the selected course first
            courseElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Then scroll to the selected video after a short delay
            setTimeout(() => {
              const videoElement = document.querySelector(`#videos li[data-video-id='${urlId}']`);
              if (videoElement) {
                toggleVideoSelection(urlId, videoElement, courseId);
                videoElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }
            }, 100);
          }
        }
      }
    }

  });

let selectedVideoId = null, originalCourseData = null, originalVideoData = null;

function truncateText(text, limit) { return text.length > limit ? text.slice(0, limit) + '...' : text; }
function computeBatchDuration(start, end) {
const diffDays = Math.ceil(Math.abs(new Date(end) - new Date(start)) / (1000 * 60 * 60 * 24));
return diffDays < 2 ? `${diffDays} Day` : diffDays < 7 ? `${diffDays} Days` : diffDays < 30 ? `${Math.round(diffDays / 7)} Week${diffDays < 14 ? '' : 's'}` : diffDays < 365 ? `${Math.round(diffDays / 30)} Month${diffDays < 60 ? '' : 's'}` : `${Math.round(diffDays / 365)} Yr${diffDays < 730 ? '' : 's'}`;
}
const getBatchInfo = id => batches.find(b => b[0] === id);

function selectCourse(id, el) {
selectedVideoId = null;
document.querySelectorAll('#videos li').forEach(li => li.classList.remove('selected'));
document.querySelectorAll('.course-item').forEach(item => item.classList.remove('selected', 'video-selected'));
el.classList.add('selected');
loadVideos(id);
history.pushState({}, '', `?id=${id}`);
}

function loadVideos(courseId) {
const list = document.getElementById('videos');
list.innerHTML = '';
const filtered = videos.filter(v => v[1] === courseId);
if (!filtered.length) list.innerHTML = '<p style="text-align:center;color:var(--gray)">No videos found.</p>';
else filtered.forEach(v => {
const li = document.createElement('li');
li.dataset.videoId = v[0];
li.innerHTML = `<strong>${v[2]}</strong><p>${truncateText(v[3], 26)}</p>`;
li.onclick = () => toggleVideoSelection(v[0], li, courseId);
list.appendChild(li);
});
loadEditForm('course', courseId);
}

function toggleVideoSelection(id, el, courseId) {
if (selectedVideoId === id) {
el.classList.remove('selected');
selectedVideoId = null;
document.querySelector(`[data-course-id='${courseId}']`).classList.remove('video-selected');
loadEditForm('course', courseId);
} else {
document.querySelectorAll('#videos li').forEach(li => li.classList.remove('selected'));
el.classList.add('selected');
selectedVideoId = id;
document.querySelector(`[data-course-id='${courseId}']`).classList.add('video-selected');
loadEditForm('video', id);
}
history.pushState({}, '', `?id=${id}`);
}


function loadEditForm(type, id) {
const form = document.getElementById('editFormContent');
form.style.display = 'block';
document.getElementById('formMessage').textContent = '';
const cForm = document.getElementById('courseEditForm'), vForm = document.getElementById('videoEditForm');
if (type === 'course') {
  const course = courses.find(c => c[0] === id);
  if (!course) {
      console.error(`Course with ID ${id} not found`);
      return;
  }

  ['courseId', 'courseTitle', 'courseDescription', 'batchId', 'instructorAdditional'].forEach((f, i) => {
      const element = document.getElementById(f);
      if (element) {
          element.value = course[i] || '';
      } else {
          console.error(`Element with ID ${f} not found`);
      }
  });

  (e=>e&&(e.value=course[4]||''))(document.getElementById("instructorDropdown"))

  originalCourseData = { courseId: course[0], courseTitle: course[1], courseDescription: course[2], batchId: course[3], instructorAdditional: course[4] };
  const batch = getBatchInfo(course[3]);
  const batchInfoElement = document.getElementById('batchInfo');
  if (batchInfoElement) {
      batchInfoElement.value = batch ? `${batch[1]} (${computeBatchDuration(batch[2], batch[3])})` : 'Not available';
  }
  cForm.style.display = 'block';
  vForm.style.display = 'none';
} else {
  const video = videos.find(v => v[0] === id);
  if (!video) {
      console.error(`Video with ID ${id} not found`);
      return;
  }
  ['videoId', 'videoCourseId', 'videoTitle', 'videoDescription', 'videoUrl', 'videoThumbnail', 'videoDuration'].forEach((f, i) => {
      const element = document.getElementById(f);
      if (element) {
          element.value = video[i] || '';
      } else {
          console.error(`Element with ID ${f} not found`);
      }
  });
  document.getElementById('videoThumbnailPreview').src = video[5] || '';
  originalVideoData = { videoId: video[0], videoCourseId: video[1], videoTitle: video[2], videoDescription: video[3], videoUrl: video[4], videoThumbnail: video[5], videoDuration: video[6] };
  cForm.style.display = 'none';
  vForm.style.display = 'block';
}
}

function resetCourseForm() {
if (originalCourseData) Object.entries(originalCourseData).forEach(([k, v]) => document.getElementById(k).value = v);
const batch = getBatchInfo(originalCourseData.batchId);
document.getElementById('batchInfo').value = batch ? `${batch[1]} (${computeBatchDuration(batch[2], batch[3])})` : 'Not available';
}

function resetVideoForm() {
if (originalVideoData) {
Object.entries(originalVideoData).forEach(([k, v]) => document.getElementById(k).value = v);
document.getElementById('videoThumbnailPreview').src = originalVideoData.videoThumbnail;
}
}


function deleteVideoCourse(type) {
let id;

if (type === 'video') {
    id = document.getElementById('videoId')?.value;
    if (!id) return showToast('No video selected to delete.', 'warning');
} else if (type === 'course') {
    id = document.getElementById('courseId')?.value;
    if (!id) return showToast('No course selected to delete.', 'warning');
} else {
    return showToast('Invalid delete type.', 'warning');
}

if (confirm(`Are you sure you want to delete this ${type}? This action cannot be undone.`)) {
    fetch('/delete-course-video', {
        method: 'POST',
        body: new URLSearchParams({ id: id, type:type }),
        headers: {
            'X-CSRF-Token': csrfToken  // Ensure CSRF token is available
        }
    })
    .then(r => r.json())
    .then(d => {
        showToast(d.message, d.message.includes('success') ? 'success' : 'warning');
        if (d.message.includes('success')) setTimeout(() => location.reload(), 1500);
    })
    .catch(e => {
        console.error(e);
        showToast('An error occurred while deleting.', 'warning');
    });
}
}




function logout() {
if (confirm("Are you sure you want to logout?")) {
fetch("/logout", {
method: "POST",
headers: {
    'X-CSRF-Token': csrfToken  // Include CSRF token
}
})
.then(() => (location.href = "/login"))
.catch((e) => console.error("Logout failed:", e));
}
}

function copyText(targetId, btn) {
const el = document.getElementById(targetId);
if (!el) return;

const textToCopy = el.value;

if (navigator.clipboard && navigator.clipboard.writeText) {
    // Modern Clipboard API
    navigator.clipboard.writeText(textToCopy)
        .then(() => {
            const orig = btn.innerHTML;
            btn.innerHTML = '<i class="fa-regular fa-copy"></i>';
            showToast(`Copied ${targetId}!`, 'success');
            setTimeout(() => btn.innerHTML = orig, 2000);
        })
        .catch(err => {
            console.error('Clipboard API failed:', err);
            showToast('Failed to copy text.', 'warning');
        });
} else {
    // Fallback for older browsers or non-secure contexts
    try {
        const textArea = document.createElement('textarea');
        textArea.value = textToCopy;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);

        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="fa-regular fa-copy"></i>';
        showToast(`Copied ${targetId}!`, 'success');
        setTimeout(() => btn.innerHTML = orig, 2000);
    } catch (err) {
        console.error('Fallback copy failed:', err);
        showToast('Copy not supported in this browser.', 'warning');
    }
}
}



function openModal(id) {
const modal = document.getElementById(id);
modal.style.display = 'block';
if (id === 'addVideoModal') {
const selected = document.querySelector('#courseList li.selected')?.dataset.courseId;
document.getElementById('addVideoCourseId').value = selected || '';
}
history.pushState({}, '', `?id=${id === 'addCourseModal' ? 'course' : 'video'}`);
}

function closeModal(id) {
const modal = document.getElementById(id);
modal.style.display = 'none';
const msg = document.getElementById(`${id === 'addCourseModal' ? 'addCourse' : 'addVideo'}Message`);
msg.textContent = '';
modal.querySelector('form').reset();
if (id === 'addVideoModal') document.getElementById('addVideoThumbnailPreview').src = '';
history.pushState({}, '', window.location.pathname);
}

window.onclick = e => {
['addVideoModal', 'addCourseModal'].forEach(id => { if (e.target === document.getElementById(id)) closeModal(id); });
};
document.querySelectorAll('.modal-content').forEach(c => c.addEventListener('click', e => e.stopPropagation()));

function logout() {
if (confirm("Are you sure you want to logout?")) {
fetch("/logout", { method: "POST" })
.then(() => (location.href = "/login"))
.catch((e) => console.error("Logout failed:", e));
}
}

document.getElementById("searchInput").addEventListener("input", function (e) {
const query = e.target.value.toLowerCase();
document.querySelectorAll("#courses li, #videos li").forEach((item) => {
const text = item.textContent.toLowerCase();
item.style.display = text.includes(query) ? "block" : "none";
});
});

document.querySelector(".notification-bell").addEventListener("click", () => {
showToast("Notifications not implemented yet!", "warning");
});

function showToast(message, type = "success") {
const toast = document.getElementById("toast");
toast.textContent = message;
toast.className = `toast ${type}`;
toast.style.opacity = "1";
setTimeout(() => (toast.style.opacity = "0"), 3000);
}

document.getElementById("editFormContent").addEventListener("input", () => {
showToast("Changes detected. Save to apply.", "warning");
});

function toggleDarkMode() {
document.body.classList.toggle("dark-mode");
const isDark = document.body.classList.contains("dark-mode");
document.documentElement.style.setProperty("--primary", isDark ? "#8a80ff" : "#605ae9");
document.documentElement.style.setProperty("--dark", isDark ? "#333" : "#1d186f");
document.documentElement.style.setProperty("--gray", isDark ? "#aaa" : "#777");
localStorage.setItem("darkMode", isDark);
}

document.addEventListener("keydown", (e) => {
if (e.ctrlKey && e.key === "s") {
e.preventDefault();
document.getElementById("editFormContent").requestSubmit();
showToast("Form submitted!");
}
});

function validateForm(formId) {
const form = document.getElementById(formId);
let valid = true;
form.querySelectorAll("[required]").forEach((input) => {
if (!input.value.trim()) {
input.style.borderColor = "red";
valid = false;
} else {
input.style.borderColor = "#ccc";
}
});
return valid;
}

["addCourseForm", "addVideoForm"].forEach((id) => {
const original = document.getElementById(id).onsubmit;
document.getElementById(id).onsubmit = function (e) {
e.preventDefault();
if (!validateForm(id)) {
showToast("Please fill all required fields.", "warning");
return;
}
original.call(this, e);
};
});

document.addEventListener("DOMContentLoaded", () => {
if (localStorage.getItem("darkMode") === "true") toggleDarkMode();
setInterval(() => {
document.getElementById("lastUpdated").textContent = new Date().toLocaleString();
}, 60000);
});

document
.querySelector(".nav-links")
.insertAdjacentHTML(
"beforeend",
'<button onclick="toggleDarkMode()">Toggle Dark Mode</button>'
);