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

// ==================== LOBBY AUTO-UPDATE SYSTEM ====================

// Lobby update interval (in milliseconds)
const LOBBY_UPDATE_INTERVAL = 2000; // 2 seconds
const CHAT_UPDATE_INTERVAL = 2000; // 2 seconds
const TICKET_UPDATE_INTERVAL = 3000; // 3 seconds

// Store last message ID for incremental updates
let lastLobbyMessageId = 0;
let lastTicketMessageId = 0;
let lobbyUpdateIntervalId = null;
let chatUpdateIntervalId = null;
let ticketUpdateIntervalId = null;

// Start lobby auto-update
function startLobbyAutoUpdate(lobbyId) {
    if (lobbyUpdateIntervalId) clearInterval(lobbyUpdateIntervalId);
    
    lobbyUpdateIntervalId = setInterval(async () => {
        try {
            const response = await apiRequest(`/api/lobby/${lobbyId}/members`, 'GET');
            if (response && response.success) {
                const isCreator = document.querySelector('[data-is-creator]')?.dataset.isCreator === 'true';
                updateLobbyMembers(response.members, response.status, response.mode, isCreator, lobbyId);
            }
        } catch (error) {
            console.error('Error updating lobby members:', error);
        }
    }, LOBBY_UPDATE_INTERVAL);
}

// Stop lobby auto-update
function stopLobbyAutoUpdate() {
    if (lobbyUpdateIntervalId) {
        clearInterval(lobbyUpdateIntervalId);
        lobbyUpdateIntervalId = null;
    }
}

// Update lobby members in DOM
function updateLobbyMembers(members, status, mode, is_creator, lobby_id) {
    const membersList = document.querySelector('.members-list');
    if (!membersList) return;
    
    // Store current members
    const currentMemberIds = Array.from(document.querySelectorAll('.member-item')).map(el => 
        parseInt(el.dataset.userId)
    );
    
    const newMemberIds = members.map(m => m.user_id);
    
    // Remove members that left
    currentMemberIds.forEach(id => {
        if (!newMemberIds.includes(id)) {
            const memberEl = document.querySelector(`.member-item[data-user-id="${id}"]`);
            if (memberEl) memberEl.remove();
        }
    });
    
    // Group by team if team mode
    if (['2x2', '3x3', '5x5'].includes(mode)) {
        const team1 = members.filter(m => m.team_number === 1);
        const team2 = members.filter(m => m.team_number === 2);
        
        // Clear and rebuild with team sections
        membersList.innerHTML = '';
        
        // Team 1
        if (team1.length > 0) {
            const team1Section = document.createElement('div');
            team1Section.className = 'team-section team-1';
            team1Section.innerHTML = '<h3>🔵 Команда 1</h3>';
            
            team1.forEach(member => {
                team1Section.appendChild(createMemberElement(member, is_creator, lobby_id));
            });
            membersList.appendChild(team1Section);
        }
        
        // Team 2
        if (team2.length > 0) {
            const team2Section = document.createElement('div');
            team2Section.className = 'team-section team-2';
            team2Section.innerHTML = '<h3>🔴 Команда 2</h3>';
            
            team2.forEach(member => {
                team2Section.appendChild(createMemberElement(member, is_creator, lobby_id));
            });
            membersList.appendChild(team2Section);
        }
    } else {
        // For 1x1 mode, just show members
        membersList.innerHTML = '';
        members.forEach(member => {
            membersList.appendChild(createMemberElement(member, is_creator, lobby_id));
        });
    }
}

// Create a member element
function createMemberElement(member, is_creator, lobby_id) {
    const memberEl = document.createElement('div');
    memberEl.className = 'member-item';
    memberEl.dataset.userId = member.user_id;
    
    let html = `
        <div class="member-avatar">${member.username[0].toUpperCase()}</div>
        <div class="member-info">
            <div class="member-name">
                ${member.username}
                ${member.is_creator ? '<span class="badge-creator">Создатель</span>' : ''}
            </div>
            <div class="member-stats">
                <span class="stat">⭐ ${member.level}</span>
                <span class="stat">💰 ${formatNumber(member.ggp)}</span>
            </div>
        </div>
    `;
    
    if (is_creator && member.user_id !== parseInt(document.querySelector('[data-current-user-id]')?.dataset.currentUserId || 0)) {
        html += `
            <div class="member-actions">
                <button class="btn-icon" onclick="swapMember(${member.user_id})" title="Поменять местами">⇅</button>
                <button class="btn-icon" onclick="kickMember(${member.user_id})" title="Кикнуть">✕</button>
                <button class="btn-icon btn-danger" onclick="banMember(${member.user_id})" title="Забанить">🚫</button>
        `;
        
        // Add team switch buttons for team modes
        const mode = document.querySelector('[data-lobby-mode]')?.dataset.lobbyMode;
        if (['2x2', '3x3', '5x5'].includes(mode)) {
            const otherTeam = member.team_number === 1 ? 2 : 1;
            html += `<button class="btn-icon btn-primary" onclick="moveToTeam(${member.user_id}, ${otherTeam})" title="Перейти в команду ${otherTeam}">👥</button>`;
        }
        
        html += `</div>`;
    }
    
    memberEl.innerHTML = html;
    return memberEl;
}

// Kick member from lobby
function kickMember(userId) {
    const lobbyId = document.querySelector('[data-lobby-id]')?.dataset.lobbyId;
    if (!lobbyId) return;
    
    if (!confirm('Вы уверены что хотите выкинуть этого игрока?')) return;
    
    apiRequest(`/api/lobby/${lobbyId}/kick`, 'POST', {
        user_id: userId
    }).then(data => {
        if (data && data.success) {
            // Members will be updated automatically by the polling
        } else {
            alert('❌ Ошибка: ' + (data?.error || 'Не удалось выкинуть игрока'));
        }
    }).catch(err => alert('❌ Ошибка сети: ' + err.message));
}

// Ban member from lobby
function banMember(userId) {
    const lobbyId = document.querySelector('[data-lobby-id]')?.dataset.lobbyId;
    if (!lobbyId) return;
    
    if (!confirm('Вы уверены что хотите забанить этого игрока?')) return;
    
    apiRequest(`/api/lobby/${lobbyId}/ban`, 'POST', {
        user_id: userId
    }).then(data => {
        if (data && data.success) {
            // Members will be updated automatically by the polling
        } else {
            alert('❌ Ошибка: ' + (data?.error || 'Не удалось забанить игрока'));
        }
    }).catch(err => alert('❌ Ошибка сети: ' + err.message));
}

// Swap member (no-op for now, can be used for team swapping)
function swapMember(userId) {
    // Future implementation for swapping teams
}

// Move player to different team
function moveToTeam(userId, teamNumber) {
    const lobbyId = document.querySelector('[data-lobby-id]')?.dataset.lobbyId;
    if (!lobbyId) return;
    
    apiRequest(`/api/lobby/${lobbyId}/move-team`, 'POST', {
        user_id: userId,
        team_number: teamNumber
    }).then(data => {
        if (data && data.success) {
            // Members will be updated automatically by the polling
        }
    });
}

// Start ticket auto-update
function startTicketAutoUpdate(ticketId) {
    if (ticketUpdateIntervalId) clearInterval(ticketUpdateIntervalId);
    
    // Get current max message ID
    const messageElements = document.querySelectorAll('.ticket-message');
    if (messageElements.length > 0) {
        const lastElement = messageElements[messageElements.length - 1];
        lastTicketMessageId = parseInt(lastElement.dataset.messageId || 0);
    }
    
    ticketUpdateIntervalId = setInterval(async () => {
        try {
            const response = await apiRequest(`/api/ticket/${ticketId}/messages?since_id=${lastTicketMessageId}`, 'GET');
            if (response && response.success) {
                if (response.messages.length > 0) {
                    addNewMessages(response.messages, 'ticket-messages');
                    lastTicketMessageId = response.messages[response.messages.length - 1].id;
                }
                // Update ticket status if changed
                updateTicketStatus(response.status);
            }
        } catch (error) {
            console.error('Error updating ticket:', error);
        }
    }, TICKET_UPDATE_INTERVAL);
}

// Stop ticket auto-update
function stopTicketAutoUpdate() {
    if (ticketUpdateIntervalId) {
        clearInterval(ticketUpdateIntervalId);
        ticketUpdateIntervalId = null;
    }
}

// Update ticket status
function updateTicketStatus(status) {
    const statusEl = document.querySelector('.ticket-status');
    if (statusEl) {
        statusEl.textContent = status;
        statusEl.className = `ticket-status status-${status}`;
    }
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize auto-update on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on lobby page
    const lobbyId = document.querySelector('[data-lobby-id]')?.dataset.lobbyId;
    if (lobbyId) {
        startLobbyAutoUpdate(lobbyId);
    }
    
    // Check if we're on ticket detail page
    const ticketId = document.querySelector('[data-ticket-id]')?.dataset.ticketId;
    if (ticketId) {
        startTicketAutoUpdate(ticketId);
    }
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        stopLobbyAutoUpdate();
        stopChatAutoUpdate();
        stopTicketAutoUpdate();
    });
});
