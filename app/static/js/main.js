// Close alert boxes
document.querySelectorAll('.alert .close').forEach(btn => {
    btn.addEventListener('click', function() {
        this.parentElement.style.display = 'none';
    });
});

// Auto-close alerts after 5 seconds
document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
        alert.style.display = 'none';
    }, 5000);
});

// Toggle server nickname input
function toggleServerInput(checkbox) {
    const server = checkbox.value;
    const section = document.getElementById(`nickname_section_${server}`);
    if (checkbox.checked) {
        section.style.display = 'block';
    } else {
        section.style.display = 'none';
    }
}

// API request helper
async function apiRequest(url, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        alert('Ошибка при обращении к серверу');
        return null;
    }
}

// Remove friend function
function removeFriend(friendId) {
    if (confirm('Вы уверены, что хотите удалить друга?')) {
        apiRequest('/api/friends/remove', 'POST', { friend_id: friendId })
            .then(data => {
                if (data && data.success) {
                    location.reload();
                }
            });
    }
}

// Add friend function
function addFriend(friendId) {
    apiRequest('/api/friends/add', 'POST', { friend_id: friendId })
        .then(data => {
            if (data && data.success) {
                alert('Друг добавлен');
                location.reload();
            }
        });
}

// Form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;

    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('error');
            isValid = false;
        } else {
            field.classList.remove('error');
        }
    });

    return isValid;
}

// Initialize tooltips
function initTooltips() {
    document.querySelectorAll('[data-tooltip]').forEach(el => {
        el.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = this.dataset.tooltip;
            document.body.appendChild(tooltip);

            const rect = this.getBoundingClientRect();
            tooltip.style.top = (rect.top - tooltip.offsetHeight - 5) + 'px';
            tooltip.style.left = (rect.left + (rect.width - tooltip.offsetWidth) / 2) + 'px';

            this.addEventListener('mouseleave', function() {
                tooltip.remove();
            });
        });
    });
}

// Document ready
document.addEventListener('DOMContentLoaded', function() {
    initTooltips();
});

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Скопировано в буфер обмена');
    });
}

// Format number with thousand separator
function formatNumber(num) {
    return new Intl.NumberFormat('ru-RU').format(num);
}

// Format date
function formatDate(date) {
    return new Intl.DateTimeFormat('ru-RU').format(new Date(date));
}
