let rowsPerPage = 20;
let currentPage = 1;
let lastAction = null;

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

document.addEventListener('DOMContentLoaded', () => {
    // console.log('DOM fully loaded, rendering table');
    if (!users || !Array.isArray(users)) {
        console.error('Users data is invalid or missing');
        showMessage('error', 'Failed to load user data');
        users = [];
    }
    renderTable();
    initializeChart();
    updatePagination();

    const debouncedFilter = debounce(filterTable, 300);
    document.getElementById('searchInput').addEventListener('input', debouncedFilter);
    document.getElementById('roleFilter').addEventListener('change', debouncedFilter);

    document.getElementById('rowsPerPage').addEventListener('change', (e) => {
        rowsPerPage = parseInt(e.target.value) || 20;
        console.log('Rows per page set to:', rowsPerPage);
        currentPage = 1;
        renderTable();
    });

    document.getElementById('selectAll').addEventListener('change', (e) => {
        document.querySelectorAll('.selectUser').forEach(cb => cb.checked = e.target.checked);
    });

    document.getElementById('applyBulk').addEventListener('click', applyBulkAction);
    document.getElementById('darkModeToggle').addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
    });
    if (localStorage.getItem('darkMode') === 'true') document.body.classList.add('dark-mode');
    

    document.getElementById('refreshBtn').addEventListener('click', fetchUsers);
    document.getElementById('exportBtn').addEventListener('click', exportToCSV);
    document.getElementById('importBtn').addEventListener('click', () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.csv';
        input.onchange = (e) => importFromCSV(e.target.files[0]);
        input.click();
    });

    document.getElementById('undoBtn').addEventListener('click', undoLastAction);
    document.getElementById('highlightBtn').addEventListener('click', highlightRecentChanges);

    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderTable(); // Re-render table with new page
        }
    });

    document.getElementById('nextPage').addEventListener('click', () => {
        const totalPages = Math.ceil(getVisibleRows().length / rowsPerPage);
        if (currentPage < totalPages) {
            currentPage++;
            renderTable(); // Re-render table with new page
        }
    });

    document.getElementById('userModal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('userModal')) {
            closeModal();
        }
    });

    document.querySelector('.close').addEventListener('click', closeModal);
});

window.addEventListener('unload', () => {
    document.querySelectorAll('.editable').forEach(cell => {
        cell.removeEventListener('click', handleEdit);
    });
});

function fetchUsers() {
    const csrfToken = document.getElementById('csrf_token').value;
    fetch('/admin/users', {
        method: 'GET',
        headers: { 
            'X-CSRF-Token': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 403 || response.status === 401) {
                window.location.href = '/login';
                return;
            }
            throw new Error('Failed to fetch users: ' + response.statusText);
        }
        return response.json();
    })
    .then(data => {
        if (data.users) {
            users = data.users;
            renderTable();
            showMessage('success', 'Users refreshed successfully');
        } else {
            throw new Error('Invalid data format');
        }
    })
    .catch(error => {
        console.error('Fetch Users Error:', error);
        showMessage('error', error.message);
    });
}

function sanitizeInput(input) {
    const div = document.createElement('div');
    div.textContent = input;
    return div.innerHTML;
}

function copyText(targetId, btn) {
    const textToCopy = targetId; // Use the data-target value directly

    if (!textToCopy) {
        showToast('No ID to copy', 'warning');
        return;
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
        // Modern Clipboard API
        navigator.clipboard.writeText(textToCopy)
            .then(() => {
                const orig = btn.innerHTML;
                btn.innerHTML = '<i class="fa-solid fa-clipboard-check"></i>'; // Change to checkmark on success
                showToast(`Copied ID: ${textToCopy}`, 'success');
                setTimeout(() => btn.innerHTML = orig, 2000);
            })
            .catch(err => {
                console.error('Clipboard API failed:', err);
                showToast('Failed to copy ID', 'warning');
            });
    } else {
        // Fallback for older browsers
        try {
            const textArea = document.createElement('textarea');
            textArea.value = textToCopy;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);

            const orig = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-clipboard-check"></i>';
            showToast(`Copied ID: ${textToCopy}`, 'success');
            setTimeout(() => btn.innerHTML = orig, 2000);
        } catch (err) {
            console.error('Fallback copy failed:', err);
            showToast('Copy not supported in this browser', 'warning');
        }
    }
}

function showToast(message, type) {
    const element = document.getElementById(type === 'success' ? 'successMessage' : 'errorMessage');
    element.textContent = message;
    element.style.display = 'block';
    element.classList.add('fade-in');
    setTimeout(() => {
        element.style.display = 'none';
        element.classList.remove('fade-in');
    }, 2000); // Match the button reset timeout
}

function createUserRow(user) {
    const row = document.createElement('tr');
    row.dataset.userId = user.id;
    row.innerHTML = `
        <td><input type="checkbox" class="selectUser" aria-label="Select user"></td>
        <td>
            ${sanitizeInput(user.id || '')}
             <button type="button" class="copy-btn" data-target="${user.id}" title="Copy ID">
                <i class="fa-regular fa-copy"></i>
            </button>
        </td>
        <td class="editable" data-field="username" data-user-id="${user.id}"  style="display: flex; justify-content: center; align-items: center; flex-direction: column;">
            <img src="${sanitizeInput(user.profile_picture || '/static/default.jpg')}" alt="User avatar" class="avatar" onerror="this.src='/static/default.jpg'; this.onerror=null;">
            <span class="username-text">${sanitizeInput(user.username || '')}</span>
        </td>
        <td class="editable" data-field="email" data-user-id="${user.id}">${sanitizeInput(user.email || '')}</td>
        <td>
            <select class="role-select" data-user-id="${user.id}" aria-label="User role">
                <option value="student" ${user.role === 'student' ? 'selected' : ''}>Student</option>
                <option value="instructor" ${user.role === 'instructor' ? 'selected' : ''}>Instructor</option>
                <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Admin</option>
            </select>
        </td>
        <td>
            <button class="delete-btn" onclick="deleteUser('${user.id}')" aria-label="Delete user">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    return row;
}

function renderTable() {
    requestAnimationFrame(() => {
        const tbody = document.getElementById('userTableBody');
        tbody.innerHTML = '';
        const fragment = document.createDocumentFragment();
        const visibleRows = getVisibleRows();
        const start = (currentPage - 1) * rowsPerPage;
        const end = Math.min(start + rowsPerPage, visibleRows.length);
        // console.log('Rendering page:', currentPage, 'Rows:', start, 'to', end, 'Total visible:', visibleRows.length);

        visibleRows.slice(start, end).forEach(user => {
            fragment.appendChild(createUserRow(user));
        });

        tbody.appendChild(fragment);
        attachEditableListeners();
        attachEventListeners(tbody);
        updatePagination();
    });
}

function attachEventListeners(tbody) {
    // Handle role dropdown changes and prevent click bubbling
    tbody.querySelectorAll('.role-select').forEach(select => {
        select.removeEventListener('change', updateRoleHandler);
        select.addEventListener('change', updateRoleHandler);
        select.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    });

    // Trigger modal on ID column click (excluding the button)
    tbody.querySelectorAll('tr td:nth-child(2)').forEach(cell => {
        cell.removeEventListener('click', showModalHandler);
        cell.addEventListener('click', (e) => {
            if (e.target.classList.contains('copy-btn') || e.target.tagName === 'I') {
                return; // Don’t open modal if clicking the copy button or its icon
            }
            showModalHandler(e);
        });
    });

    // Attach copy button listeners
    tbody.querySelectorAll('.copy-btn').forEach(btn => {
        btn.removeEventListener('click', handleCopyClick);
        btn.addEventListener('click', handleCopyClick);
    });
}

function handleCopyClick(e) {
    e.stopPropagation(); // Prevent modal from opening when clicking the button
    const btn = e.currentTarget;
    const targetId = btn.getAttribute('data-target');
    copyText(targetId, btn);
}

function updateRoleHandler(e) {
    const userId = e.target.dataset.userId;
    const newRole = e.target.value;
    if (userId && newRole) {
        updateUserRole(userId, newRole);
    } else {
        showMessage('error', 'Invalid user ID or role');
    }
}

function showModalHandler(e) {
    const row = e.target.closest('tr');
    showUserModal(row.dataset.userId);
}

function attachEditableListeners() {
    document.querySelectorAll('.editable').forEach(cell => {
        cell.removeEventListener('click', handleEdit);
        cell.addEventListener('click', handleEdit);
    });
}

function handleEdit(e) {
    if (e.target.tagName === 'IMG') return;
    const field = e.currentTarget.dataset.field;
    const userId = e.currentTarget.dataset.userId;
    const currentText = e.currentTarget.querySelector(`.${field}-text`)?.textContent.trim() || e.currentTarget.textContent.trim();

    const input = document.createElement('input');
    input.value = currentText;
    input.style.width = '100%';
    input.addEventListener('blur', () => {
        const newValue = input.value.trim();
        if (newValue !== currentText) {
            updateUserField(userId, field, newValue);
        } else {
            renderTable();
        }
    });
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') input.blur();
    });
    const cell = e.currentTarget;
    if (cell.querySelector(`.${field}-text`)) {
        cell.querySelector(`.${field}-text`).textContent = '';
        cell.querySelector(`.${field}-text`).appendChild(input);
    } else {
        cell.textContent = '';
        cell.appendChild(input);
    }
    input.focus();
}

function updateUserField(userId, field, value) {
    if (!userId || !field || !value) {
        showMessage('error', 'Invalid input data');
        return;
    }
    if (field === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        showMessage('error', 'Invalid email format');
        return;
    }

    const csrfToken = document.getElementById('csrf_token').value;
    fetch('/admin/update-user-field', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRF-Token': csrfToken
        },
        body: `user_id=${encodeURIComponent(userId)}&field=${encodeURIComponent(field)}&value=${encodeURIComponent(value)}`,
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to update user: ' + response.statusText);
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const user = users.find(u => u.id == userId);
            if (user) {
                lastAction = { type: 'update', userId, field, oldValue: user[field], newValue: value };
                user[field] = value;
                document.getElementById('undoBtn').style.display = 'block';
                renderTable();
                showMessage('success', data.message);
            }
        } else {
            showMessage('error', data.message);
        }
    })
    .catch(error => {
        console.error('Update User Field Error:', error);
        showMessage('error', 'Failed to update user field: ' + error.message);
    });
}

function getCsrfToken() {
    const tokenElement = document.getElementById('csrf_token');
    return tokenElement ? tokenElement.value : '';
}

function updateUserRole(userId, newRole) {
    const csrfToken = getCsrfToken();
    if (!csrfToken) {
        showMessage('error', 'CSRF token missing. Please refresh the page.');
        return;
    }

    fetch('/admin/update-user', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRF-Token': csrfToken
        },
        body: `user_id=${encodeURIComponent(userId)}&role=${encodeURIComponent(newRole)}`,
        credentials: 'include'
    })
    .then(response => response.json().catch(() => { throw new Error('Invalid JSON response'); }))
    .then(data => {
        if (data.success) {
            const user = users.find(u => u.id == userId);
            if (user) {
                lastAction = { type: 'role', userId, oldRole: user.role, newRole };
                user.role = newRole;
                document.getElementById('undoBtn').style.display = 'block';
                renderTable();
                showMessage('success', data.message || 'Role updated successfully');
            }
        } else {
            throw new Error(data.message || 'Role update failed');
        }
    })
    .catch(error => {
        console.error('Update Role Error:', error);
        showMessage('error', `Failed to update role: ${error.message}`);
    });
}

function deleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user?')) return;
    const csrfToken = document.getElementById('csrf_token').value;
    fetch('/admin/delete-user', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRF-Token': csrfToken
        },
        body: `user_id=${encodeURIComponent(userId)}`,
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to delete user: ' + response.statusText);
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const deletedUser = users.find(u => u.id == userId);
            users = users.filter(u => u.id != userId);
            lastAction = { type: 'delete', user: { ...deletedUser } };
            document.getElementById('undoBtn').style.display = 'block';
            renderTable();
            showMessage('success', data.message);
        } else {
            showMessage('error', data.message);
        }
    })
    .catch(error => {
        console.error('Delete User Error:', error);
        showMessage('error', 'Failed to delete user: ' + error.message);
    });
}

function getVisibleRows() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const roleFilter = document.getElementById('roleFilter').value;
    return users.filter(user => {
        const text = `${user.id} ${user.username} ${user.email} ${user.role}`.toLowerCase();
        return text.includes(searchTerm) && (!roleFilter || user.role === roleFilter);
    });
}

function filterTable() {
    renderTable();
}

function applyBulkAction() {
    const action = document.getElementById('bulkAction').value;
    const selectedUsers = Array.from(document.querySelectorAll('.selectUser:checked')).map(cb => cb.closest('tr').dataset.userId);
    if (!selectedUsers.length) return showMessage('error', 'No users selected');

    if (action === 'delete') {
        if (confirm(`Delete ${selectedUsers.length} users?`)) {
            Promise.all(selectedUsers.map(id => deleteUser(id)))
                .then(() => showMessage('success', 'Bulk delete completed'))
                .catch(() => showMessage('error', 'Bulk delete failed'));
        }
    } else if (action === 'changeRole') {
        const newRole = prompt('Enter new role (student/instructor/admin):');
        if (newRole && ['student', 'instructor', 'admin'].includes(newRole)) {
            Promise.all(selectedUsers.map(id => updateUserRole(id, newRole)))
                .then(() => showMessage('success', 'Bulk role change completed'))
                .catch(() => showMessage('error', 'Bulk role change failed'));
        } else {
            showMessage('error', 'Invalid role');
        }
    }
}

function exportToCSV() {
    const headers = "ID,Username,Email,Role\n";
    const rows = users.map(user => `${user.id},${user.username},${user.email},${user.role}`).join('\n');
    const csv = headers + rows;
    const link = document.createElement('a');
    link.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
    link.download = 'users.csv';
    link.click();
}

function importFromCSV(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const text = e.target.result;
        const rows = text.split('\n').slice(1).filter(row => row.trim());
        const newUsers = rows.map(row => {
            const [id, username, email, role] = row.split(',').map(item => item.trim());
            if (username && email && ['student', 'instructor', 'admin'].includes(role)) {
                return { id: id || Date.now().toString(), username, email, role };
            }
            return null;
        }).filter(user => user);
        if (newUsers.length) {
            users = [...users, ...newUsers];
            renderTable();
            showMessage('success', `Imported ${newUsers.length} users`);
        } else {
            showMessage('error', 'No valid users found in CSV');
        }
    };
    reader.onerror = () => showMessage('error', 'Failed to read CSV file');
    reader.readAsText(file);
}

function undoLastAction() {
    if (!lastAction) return showMessage('error', 'No action to undo');
    if (lastAction.type === 'update') {
        updateUserField(lastAction.userId, lastAction.field, lastAction.oldValue);
    } else if (lastAction.type === 'role') {
        updateUserRole(lastAction.userId, lastAction.oldRole);
    } else if (lastAction.type === 'delete') {
        users.push(lastAction.user);
        renderTable();
        showMessage('success', 'User restored');
    }
    document.getElementById('undoBtn').style.display = 'none';
    lastAction = null;
}

function highlightRecentChanges() {
    const recentRows = document.querySelectorAll('#userTableBody tr');
    recentRows.forEach(row => {
        row.classList.add('highlight');
        setTimeout(() => row.classList.remove('highlight'), 2000);
    });
}

function showUserModal(userId) {
    const user = users.find(u => u.id == userId);
    if (!user) return;
    document.getElementById('modalId').textContent = user.id || '';
    document.getElementById('modalUsername').textContent = user.username || '';
    document.getElementById('modalEmail').textContent = user.email || '';
    document.getElementById('modalRole').textContent = user.role || '';
    const modal = document.getElementById('userModal');
    modal.style.display = 'block';
    setTimeout(() => document.querySelector('.modal-content').classList.add('show'), 10);
}

function closeModal() {
    const modal = document.getElementById('userModal');
    document.querySelector('.modal-content').classList.remove('show');
    setTimeout(() => modal.style.display = 'none', 400);
}

function sortTable(columnIndex) {
    const isAscending = document.querySelector('.user-table').dataset.sortDirection !== 'asc';
    document.querySelector('.user-table').dataset.sortDirection = isAscending ? 'asc' : 'desc';
    const fields = ['id', 'username', 'email', 'role'];
    const field = fields[columnIndex - 1];
    users.sort((a, b) => {
        const aText = (a[field] || '').toString().toLowerCase();
        const bText = (b[field] || '').toString().toLowerCase();
        return isAscending ? aText.localeCompare(bText) : bText.localeCompare(aText);
    });
    renderTable();
}

function updatePagination() {
    const visibleRows = getVisibleRows();
    const totalPages = Math.max(1, Math.ceil(visibleRows.length / rowsPerPage));
    currentPage = Math.min(currentPage, totalPages); // Cap currentPage to max pages
    currentPage = Math.max(1, currentPage); // Ensure at least page 1

    document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('prevPage').disabled = currentPage === 1;
    document.getElementById('nextPage').disabled = currentPage === totalPages;

    updateStats(); // Update dashboard stats
}

function updateStats() {
    const visibleRows = getVisibleRows();
    document.getElementById('totalUsers').textContent = visibleRows.length;
    document.getElementById('studentCount').textContent = visibleRows.filter(user => user.role === 'student').length;
    document.getElementById('instructorCount').textContent = visibleRows.filter(user => user.role === 'instructor').length;
    document.getElementById('adminCount').textContent = visibleRows.filter(user => user.role === 'admin').length;
}

function initializeChart() {
const roleCounts = {
student: users.filter(u => u.role === 'student').length,
instructor: users.filter(u => u.role === 'instructor').length,
admin: users.filter(u => u.role === 'admin').length
};

const ctx = document.getElementById('userActivityChart').getContext('2d');
new Chart(ctx, {
type: 'bar',
data: {
    labels: ['Students', 'Instructors', 'Admins'],
    datasets: [{
        label: 'User Roles',
        data: [roleCounts.student, roleCounts.instructor, roleCounts.admin],
        backgroundColor: ['#2ecc71', '#605ae9', '#e74c3c'],
        borderWidth: 1
    }]
},
options: {
    responsive: true,
    maintainAspectRatio: false, /* Fits container without distortion */
    scales: {
        y: { 
            beginAtZero: true,
            ticks: { stepSize: 1 } /* Whole numbers */
        }
    },
    plugins: {
        legend: {
            display: false /* Hides legend to save space */
        },
        title: {
            display: true,
            text: 'User Role Distribution',
            font: { size: 14 }
        }
    }
}
});
}

function showMessage(type, message) {
    const element = document.getElementById(type === 'success' ? 'successMessage' : 'errorMessage');
    element.textContent = message;
    element.style.display = 'block';
    element.classList.add('fade-in');
    setTimeout(() => {
        element.style.display = 'none';
        element.classList.remove('fade-in');
    }, 3000);
}

function showTooltip(e) {
    const tooltip = document.getElementById('tooltip');
    const field = e.target.dataset.field || 'Role';
    tooltip.textContent = `Edit ${field}`;
    tooltip.style.display = 'block';
    tooltip.style.left = `${e.pageX + 10}px`;
    tooltip.style.top = `${e.pageY + 10}px`;
}

function hideTooltip() {
    document.getElementById('tooltip').style.display = 'none';
}



const select = document.getElementById("rowsPerPage");
const customInput = document.getElementById("customRows");
let previousCustomOption = null;

// Handle select change
select.addEventListener("change", function() {
    if (select.value === "custom") {
        customInput.style.display = "inline-block";
        customInput.focus();
    } else {
        customInput.style.display = "none";
    }
    // Your existing JS should pick up the value here
});

// Handle custom input
customInput.addEventListener("change", function() {
    const customValue = customInput.value.trim();
    if (!customValue || isNaN(customValue) || customValue <= 0) {
        alert('Please enter a valid positive number');
        return;
    }
    if (customValue && !isNaN(customValue) && customValue > 0) {
        // Remove previous custom option if it exists
        if (previousCustomOption) {
            select.removeChild(previousCustomOption);
        }

        // Create and add the new custom option
        const newOption = document.createElement("option");
        newOption.value = customValue;
        newOption.text = `${customValue} rows(custom)`;
        select.insertBefore(newOption, select.querySelector('option[value="custom"]'));
        previousCustomOption = newOption;

        // Select the new custom option and trigger change event
        select.value = customValue;
        select.dispatchEvent(new Event("change")); // Manually trigger change event

        // Hide and reset input
        customInput.style.display = "none";
        customInput.value = "";
    }
});

// Handle initial load
if (select.value === "custom") {
    customInput.style.display = "inline-block";
    customInput.focus();
}