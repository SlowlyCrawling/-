document.addEventListener('DOMContentLoaded', function() {
    if (api.isAuthenticated()) {
        showDashboard();
    } else {
        showLogin();
    }

    initAuthTabs();
    initForms();
});

let currentMasterId = null;
let currentDate = null;
let currentTime = null;

function initAuthTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const forms = document.querySelectorAll('.auth-form');
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            forms.forEach(form => {
                form.classList.remove('active');
                if (form.id === `${tab}Form`) {
                    form.classList.add('active');
                }
            });
        });
    });
}

function initForms() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;
            
            showNotification('info', 'Вход в систему...');
            
            try {
                const result = await api.login(email, password);
                
                if (result.success) {
                    showNotification('success', 'Вход выполнен успешно!');
                    setTimeout(() => showDashboard(), 1000);
                } else {
                    showNotification('error', result.error || 'Ошибка входа');
                }
            } catch (error) {
                showNotification('error', 'Ошибка соединения с сервером');
            }
        });
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const name = document.getElementById('regName').value;
            const email = document.getElementById('regEmail').value;
            const password = document.getElementById('regPassword').value;
            
            showNotification('info', 'Регистрация...');
            
            try {
                const result = await api.register(name, email, password);
                
                if (result.success) {
                    showNotification('success', 'Регистрация успешна!');
                    setTimeout(() => showDashboard(), 1000);
                } else {
                    showNotification('error', result.error || 'Ошибка регистрации');
                }
            } catch (error) {
                showNotification('error', 'Ошибка соединения с сервером');
            }
        });
    }
}

function showLogin() {
    document.body.innerHTML = '';
    
    const loginHTML = `
        <div class="container" id="loginContainer">
            <div class="logo">
                <i class="fas fa-cut"></i>
                <h1>Парикмахерский салон "Стиль"</h1>
            </div>
            
            <div class="auth-box">
                <div class="tabs">
                    <button class="tab-btn active" data-tab="login">Вход</button>
                    <button class="tab-btn" data-tab="register">Регистрация</button>
                </div>
                
                <form id="loginForm" class="auth-form active">
                    <div class="form-group">
                        <label for="loginEmail"><i class="fas fa-envelope"></i> Email</label>
                        <input type="email" id="loginEmail" placeholder="admin@admin.com" required>
                    </div>
                    <div class="form-group">
                        <label for="loginPassword"><i class="fas fa-lock"></i> Пароль</label>
                        <input type="password" id="loginPassword" placeholder="admin123" required>
                    </div>
                    <button type="submit" class="btn-primary">
                        <i class="fas fa-sign-in-alt"></i> Войти
                    </button>
                    <div class="demo-credentials">
                        <p><strong>Демо доступ:</strong></p>
                        <p>Админ: admin@admin.com / admin123</p>
                        <p>Мастер Анна: anna@master.com / masterpass</p>
                        <p>Мастер Борис: boris@master.com / masterpass</p>
                    </div>
                </form>
                
                <form id="registerForm" class="auth-form">
                    <div class="form-group">
                        <label for="regName"><i class="fas fa-user"></i> Имя</label>
                        <input type="text" id="regName" placeholder="Ваше имя" required>
                    </div>
                    <div class="form-group">
                        <label for="regEmail"><i class="fas fa-envelope"></i> Email</label>
                        <input type="email" id="regEmail" placeholder="email@example.com" required>
                    </div>
                    <div class="form-group">
                        <label for="regPassword"><i class="fas fa-lock"></i> Пароль</label>
                        <input type="password" id="regPassword" placeholder="Пароль" required>
                    </div>
                    <button type="submit" class="btn-primary">
                        <i class="fas fa-user-plus"></i> Зарегистрироваться
                    </button>
                </form>
            </div>
        </div>
    `;
    
    document.body.innerHTML = loginHTML;
    initAuthTabs();
    initForms();
}

async function showDashboard() {
    const user = api.getCurrentUser();
    
    // Сбрасываем флаг рекомендаций при каждом входе
    localStorage.removeItem('recommendationShown');
    
    let dashboardHTML = '';
    
    if (api.isAdmin()) {
        dashboardHTML = await getAdminDashboardHTML();
    } else if (api.isMaster()) {
        dashboardHTML = await getMasterDashboardHTML();
    } else {
        dashboardHTML = await getClientDashboardHTML();
    }
    
    document.body.innerHTML = dashboardHTML;
    
    initDashboardNavigation();
    
    if (api.isMaster()) {
        loadMasterData();
    } else {
        loadClientData();
        // Проверяем рекомендации с задержкой
        setTimeout(() => checkRecommendations(), 2000);
    }
    
    initNotifications();
}

// ФУНКЦИИ КЛИЕНТА
async function getClientDashboardHTML() {
    const user = api.getCurrentUser();
    
    return `
        <div class="container">
            <div class="dashboard-header">
                <div class="user-info">
                    <div class="user-avatar">
                        <i class="fas fa-user"></i>
                    </div>
                    <div class="user-details">
                        <h3>${user.name}</h3>
                        <span class="role-badge">Клиент</span>
                    </div>
                </div>
                <button class="btn-secondary" onclick="logout()">
                    <i class="fas fa-sign-out-alt"></i> Выйти
                </button>
            </div>
            
            <div class="dashboard-nav">
                <button class="nav-btn active" data-section="booking">
                    <i class="fas fa-calendar-plus"></i> Записаться
                </button>
                <button class="nav-btn" data-section="history">
                    <i class="fas fa-history"></i> История сеансов
                </button>
                <button class="nav-btn" data-section="my-bookings">
                    <i class="fas fa-clipboard-list"></i> Мои записи
                </button>
            </div>
            
            <div class="dashboard-content">
                <div id="bookingSection" class="content-section active">
                    <h2><i class="fas fa-calendar-alt"></i> Выберите мастера и время</h2>
                    <div id="mastersList" class="loading">
                        <div class="spinner"></div>
                        <p>Загрузка мастеров...</p>
                    </div>
                    <div id="calendarSection" style="display: none;">
                        <div class="calendar-controls">
                            <div class="current-week" id="currentWeek"></div>
                            <div class="week-navigation">
                                <button class="btn-secondary" onclick="prevWeek()">
                                    <i class="fas fa-chevron-left"></i> Предыдущая
                                </button>
                                <button class="btn-secondary" onclick="todayWeek()">
                                    Сегодня
                                </button>
                                <button class="btn-secondary" onclick="nextWeek()">
                                    Следующая <i class="fas fa-chevron-right"></i>
                                </button>
                            </div>
                        </div>
                        <div id="calendarGrid" class="calendar-grid"></div>
                    </div>
                </div>
                
                <div id="historySection" class="content-section">
                    <h2><i class="fas fa-history"></i> История сеансов</h2>
                    <div id="sessionsList" class="sessions-list">
                        <div class="loading">
                            <div class="spinner"></div>
                            <p>Загрузка истории...</p>
                        </div>
                    </div>
                </div>
                
                <div id="myBookingsSection" class="content-section">
                    <h2><i class="fas fa-clipboard-list"></i> Мои записи</h2>
                    <div id="bookingsList" class="sessions-list">
                        <div class="loading">
                            <div class="spinner"></div>
                            <p>Загрузка записей...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="confirmModal" class="modal-overlay">
            <div class="modal">
                <div class="modal-header">
                    <h2>Подтверждение записи</h2>
                    <button class="close-modal" onclick="closeModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <p id="modalMessage"></p>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="closeModal()">Отмена</button>
                    <button class="btn-primary" onclick="confirmBooking()">Подтвердить</button>
                </div>
            </div>
        </div>
        
        <div id="recommendationModal" class="modal-overlay">
            <div class="modal">
                <div class="modal-header">
                    <h2><i class="fas fa-bell"></i> Рекомендация</h2>
                    <button class="close-modal" onclick="closeRecommendationModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div id="recommendationContent"></div>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="closeRecommendationModal()">Позже</button>
                    <button class="btn-primary" onclick="acceptRecommendation()">Записаться</button>
                </div>
            </div>
        </div>
    `;
}

function initDashboardNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const sections = document.querySelectorAll('.content-section');
    
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const sectionId = btn.dataset.section;
            
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            sections.forEach(section => {
                section.classList.remove('active');
                if (section.id === `${sectionId}Section`) {
                    section.classList.add('active');
                }
            });
            
            if (sectionId === 'history') {
                loadUserSessions();
            } else if (sectionId === 'my-bookings') {
                loadUserBookings();
            } else if (sectionId === 'booking') {
                loadMasters();
            }
        });
    });
}

async function loadClientData() {
    await loadMasters();
    await loadUserSessions();
    await loadUserBookings();
}

async function loadMasters() {
    try {
        const masters = await api.getMasters();
        const mastersList = document.getElementById('mastersList');
        
        if (!mastersList) return;
        
        if (Object.keys(masters).length > 0) {
            mastersList.innerHTML = '';
            
            Object.entries(masters).forEach(([id, name]) => {
                const masterCard = document.createElement('div');
                masterCard.className = 'master-card';
                masterCard.innerHTML = `
                    <div class="master-avatar">
                        <i class="fas fa-cut"></i>
                    </div>
                    <div class="master-info">
                        <h3>${name}</h3>
                        <p>Мастер-парикмахер</p>
                    </div>
                    <button class="btn-primary" style="margin-top: 15px;" onclick="selectMaster(${id}, '${name}')">
                        <i class="fas fa-calendar-check"></i> Выбрать время
                    </button>
                `;
                mastersList.appendChild(masterCard);
            });
            
            mastersList.className = 'masters-grid';
        } else {
            mastersList.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-users" style="font-size: 48px; margin-bottom: 20px; opacity: 0.3;"></i>
                    <p>Мастера не найдены</p>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('mastersList').innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #dc3545; margin-bottom: 20px;"></i>
                <p style="color: #666;">Ошибка загрузки мастеров</p>
                <button class="btn-secondary" onclick="loadMasters()">Повторить</button>
            </div>
        `;
    }
}

function selectMaster(masterId, masterName) {
    currentMasterId = masterId;
    
    document.getElementById('calendarSection').style.display = 'block';
    document.getElementById('mastersList').style.display = 'none';
    
    document.querySelector('#bookingSection h2').innerHTML = 
        `<i class="fas fa-user"></i> Запись к ${masterName}`;
    
    generateCalendar();
}

let currentWeekStart = new Date();
currentWeekStart.setDate(currentWeekStart.getDate() - currentWeekStart.getDay() + 1);

function generateCalendar() {
    if (!currentMasterId) return;
    
    const calendarGrid = document.getElementById('calendarGrid');
    if (!calendarGrid) return;
    
    calendarGrid.innerHTML = '';
    
    const endDate = new Date(currentWeekStart);
    endDate.setDate(endDate.getDate() + 6);
    
    const weekTitle = formatDate(currentWeekStart) + ' - ' + formatDate(endDate);
    document.getElementById('currentWeek').textContent = weekTitle;
    
    for (let i = 0; i < 7; i++) {
        const date = new Date(currentWeekStart);
        date.setDate(date.getDate() + i);
        
        const dayCard = document.createElement('div');
        dayCard.className = 'calendar-day';
        
        if (date.toDateString() === new Date().toDateString()) {
            dayCard.classList.add('today');
        }
        
        const dateString = date.toISOString().split('T')[0];
        
        dayCard.innerHTML = `
            <div class="calendar-day-header">
                <div class="day-name">${getDayName(date.getDay())}</div>
                <div class="date-number">${date.getDate()}</div>
            </div>
            <div class="day-slots" id="slots-${dateString}">
                <div class="loading">
                    <div class="spinner" style="width: 20px; height: 20px;"></div>
                </div>
            </div>
        `;
        
        calendarGrid.appendChild(dayCard);
        
        loadDaySlots(dateString);
    }
}

async function loadDaySlots(dateString) {
    try {
        const schedule = await api.getMasterSchedule(currentMasterId, dateString);
        const slotsContainer = document.getElementById(`slots-${dateString}`);
        
        if (!slotsContainer) return;
        
        slotsContainer.innerHTML = '';
        
        const timeSlots = [];
        for (let hour = 10; hour < 18; hour++) {
            timeSlots.push(`${hour.toString().padStart(2, '0')}:00`);
        }
        
        timeSlots.forEach(time => {
            const isBooked = schedule.booked_times?.includes(time) || false;
            
            const slot = document.createElement('div');
            slot.className = `day-slot ${isBooked ? 'busy' : 'free'}`;
            slot.textContent = time;
            
            if (!isBooked) {
                slot.onclick = () => selectTime(dateString, time);
            }
            
            slotsContainer.appendChild(slot);
        });
        
    } catch (error) {
        document.getElementById(`slots-${dateString}`).innerHTML = 
            '<span style="color: #666;">Ошибка загрузки</span>';
    }
}

function selectTime(date, time) {
    currentDate = date;
    currentTime = time;
    
    checkAvailability(date, time);
}

async function checkAvailability(date, time) {
    try {
        const result = await api.checkAvailability(currentMasterId, date, time);
        
        if (result.available) {
            showConfirmModal(result.master_name, date, time);
        } else {
            showNotification('error', 'Время занято');
        }
    } catch (error) {
        showNotification('error', 'Ошибка проверки доступности');
    }
}

function showConfirmModal(masterName, date, time) {
    const modal = document.getElementById('confirmModal');
    const message = document.getElementById('modalMessage');
    
    message.innerHTML = `
        <p>Вы хотите записаться к <strong>${masterName}</strong></p>
        <p>Дата: <strong>${formatDate(new Date(date))}</strong></p>
        <p>Время: <strong>${time}</strong></p>
    `;
    
    modal.style.display = 'flex';
}

function closeModal() {
    document.getElementById('confirmModal').style.display = 'none';
}

function closeRecommendationModal() {
    document.getElementById('recommendationModal').style.display = 'none';
}

async function confirmBooking() {
    try {
        showNotification('info', 'Бронирование...');
        
        const result = await api.bookAppointment(currentMasterId, currentDate, currentTime);
        
        if (result.success) {
            showNotification('success', 'Запись успешно создана!');
            
            loadDaySlots(currentDate);
            loadUserBookings();
            
            closeModal();
        } else {
            showNotification('error', result.error || 'Ошибка бронирования');
        }
    } catch (error) {
        showNotification('error', 'Ошибка соединения с сервером');
    }
}

function prevWeek() {
    currentWeekStart.setDate(currentWeekStart.getDate() - 7);
    generateCalendar();
}

function nextWeek() {
    currentWeekStart.setDate(currentWeekStart.getDate() + 7);
    generateCalendar();
}

function todayWeek() {
    currentWeekStart = new Date();
    currentWeekStart.setDate(currentWeekStart.getDate() - currentWeekStart.getDay() + 1);
    generateCalendar();
}

async function loadUserSessions() {
    try {
        const user = api.getCurrentUser();
        const sessions = await api.getUserSessions(user.id);
        
        const sessionsList = document.getElementById('sessionsList');
        if (!sessionsList) return;
        
        if (sessions.success && sessions.sessions && sessions.sessions.length > 0) {
            sessionsList.innerHTML = sessions.sessions.map(session => `
                <div class="session-card">
                    <div class="session-info">
                        <h4>${session.master_name || 'Мастер'}</h4>
                        <p>${session.date} в ${session.time}</p>
                        <p>Статус: <span class="session-status ${session.status}">${
                            session.status === 'pending' ? 'Ожидается' :
                            session.status === 'completed' ? 'Завершен' : 'Отменен'
                        }</span></p>
                    </div>
                    ${session.status === 'pending' ? `
                        <div class="session-actions">
                            <button class="btn-success" onclick="completeSession(${session.id}, ${session.master_id}, '${session.date}', '${session.time}')">
                                <i class="fas fa-check"></i> Завершить
                            </button>
                            <button class="btn-danger" onclick="cancelSession(${session.id})">
                                <i class="fas fa-times"></i> Отменить
                            </button>
                        </div>
                    ` : ''}
                </div>
            `).join('');
        } else {
            sessionsList.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-history" style="font-size: 48px; margin-bottom: 20px; opacity: 0.3;"></i>
                    <p>История сеансов пуста</p>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('sessionsList').innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #dc3545; margin-bottom: 20px;"></i>
                <p style="color: #666;">Ошибка загрузки истории</p>
            </div>
        `;
    }
}

async function loadUserBookings() {
    try {
        const user = api.getCurrentUser();
        const bookings = await api.getUserBookings(user.id);
        
        const bookingsList = document.getElementById('bookingsList');
        if (!bookingsList) return;
        
        if (bookings.success && bookings.user_bookings && bookings.user_bookings.length > 0) {
            bookingsList.innerHTML = bookings.user_bookings.map(booking => `
                <div class="session-card">
                    <div class="session-info">
                        <h4>${booking.master || 'Мастер'}</h4>
                        <p>${booking.date} в ${booking.time}</p>
                        <p>Запись создана: ${new Date(booking.created_at).toLocaleDateString()}</p>
                    </div>
                    <div class="session-actions">
                        <button class="btn-danger" onclick="cancelUserBooking(${booking.id}, ${booking.master_id}, '${booking.date}', '${booking.time}')">
                            <i class="fas fa-times"></i> Отменить запись
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            bookingsList.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-clipboard-list" style="font-size: 48px; margin-bottom: 20px; opacity: 0.3;"></i>
                    <p>У вас нет активных записей</p>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('bookingsList').innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #dc3545; margin-bottom: 20px;"></i>
                <p style="color: #666;">Ошибка загрузки записей</p>
            </div>
        `;
    }
}

async function completeSession(sessionId, masterId, date, time) {
    if (!confirm('Подтвердить завершение сеанса?')) return;
    
    try {
        const user = api.getCurrentUser();
        
        // 1. Обновляем статус сеанса
        await api.updateSession(sessionId, 'completed');
        
        // 2. Добавляем в историю посещений
        await api.completeVisit({
            user_id: user.id,
            master_id: masterId,
            date: date,
            time: time,
            status: 'completed'
        });
        
        // 3. Добавляем в историю мастера
        const masterResponse = await fetch('http://localhost:5001/add_master_visit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                master_id: masterId,
                client_id: user.id,
                client_name: user.name,
                date: date,
                time: time,
                status: 'completed'
            })
        });
        
        // 4. Освобождаем слот
        await api.freeSlot(masterId, date, time);
        
        showNotification('success', 'Сеанс завершен успешно!');
        
        setTimeout(() => {
            loadUserSessions();
            loadUserBookings();
        }, 500);
        
    } catch (error) {
        showNotification('error', 'Ошибка завершения сеанса: ' + error.message);
    }
}

async function cancelSession(sessionId) {
    if (!confirm('Вы уверены, что хотите отменить этот сеанс?')) return;
    
    try {
        await api.updateSession(sessionId, 'cancelled');
        showNotification('success', 'Сеанс отменен');
        loadUserSessions();
    } catch (error) {
        showNotification('error', 'Ошибка отмены сеанса');
    }
}

async function cancelUserBooking(bookingId, masterId, date, time) {
    if (!confirm('Вы уверены, что хотите отменить эту запись?')) return;
    
    try {
        await api.cancelBooking(bookingId);
        await api.freeSlot(masterId, date, time);
        
        showNotification('success', 'Запись отменена');
        loadUserBookings();
    } catch (error) {
        showNotification('error', 'Ошибка отмены записи');
    }
}

async function checkRecommendations() {
    const recommendationShown = localStorage.getItem('recommendationShown');
    if (recommendationShown === 'true') return;
    
    try {
        const user = api.getCurrentUser();
        const recommendation = await api.getRecommendation(user.id);
        
        if (recommendation.success && recommendation.has_recommendation) {
            localStorage.setItem('recommendationShown', 'true');
            
            setTimeout(() => {
                showRecommendationModal(recommendation.recommendation);
            }, 2000);
        }
    } catch (error) {
        console.error('Ошибка проверки рекомендаций:', error);
    }
}

function showRecommendationModal(recommendation) {
    const modal = document.getElementById('recommendationModal');
    const content = document.getElementById('recommendationContent');
    
    content.innerHTML = `
        <div style="text-align: center;">
            <i class="fas fa-calendar-check" style="font-size: 48px; color: #667eea; margin-bottom: 20px;"></i>
            <h3>${recommendation.message}</h3>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px;">
                <p><strong>Мастер:</strong> ${recommendation.master_name}</p>
                <p><strong>Дата:</strong> ${formatDate(new Date(recommendation.date))}</p>
                <p><strong>Время:</strong> ${recommendation.time}</p>
            </div>
        </div>
    `;
    
    window.currentRecommendation = recommendation;
    modal.style.display = 'flex';
}

async function acceptRecommendation() {
    if (!window.currentRecommendation) return;
    
    const { master_id, date, time } = window.currentRecommendation;
    
    currentMasterId = master_id;
    currentDate = date;
    currentTime = time;
    
    closeRecommendationModal();
    
    try {
        showNotification('info', 'Бронирование по рекомендации...');
        
        const result = await api.bookAppointment(master_id, date, time);
        
        if (result.success) {
            showNotification('success', 'Запись по рекомендации создана!');
            loadUserBookings();
        } else {
            showNotification('error', result.error || 'Не удалось записаться по рекомендации');
        }
    } catch (error) {
        showNotification('error', 'Ошибка соединения с сервером');
    }
}

// ФУНКЦИИ МАСТЕРА
async function getMasterDashboardHTML() {
    const user = api.getCurrentUser();
    
    return `
        <div class="container">
            <div class="dashboard-header">
                <div class="user-info">
                    <div class="user-avatar">
                        <i class="fas fa-cut"></i>
                    </div>
                    <div class="user-details">
                        <h3>${user.name}</h3>
                        <span class="role-badge">Мастер</span>
                    </div>
                </div>
                <button class="btn-secondary" onclick="logout()">
                    <i class="fas fa-sign-out-alt"></i> Выйти
                </button>
            </div>
            
            <div class="dashboard-nav">
                <button class="nav-btn active" data-section="schedule">
                    <i class="fas fa-calendar-alt"></i> Активные записи
                </button>
                <button class="nav-btn" data-section="visit-history">
                    <i class="fas fa-history"></i> История посещений
                </button>
            </div>
            
            <div class="dashboard-content">
                <div id="scheduleSection" class="content-section active">
                    <h2><i class="fas fa-calendar-alt"></i> Активные записи</h2>
                    <div id="masterSchedule" class="loading">
                        <div class="spinner"></div>
                        <p>Загрузка записей...</p>
                    </div>
                </div>
                
                <div id="visitHistorySection" class="content-section">
                    <h2><i class="fas fa-history"></i> История посещений</h2>
                    <div id="masterVisitHistory" class="loading">
                        <div class="spinner"></div>
                        <p>Загрузка истории...</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function loadMasterData() {
    await loadMasterSchedule();
    await loadMasterVisitHistory();
}

async function loadMasterSchedule() {
    try {
        const user = api.getCurrentUser();
        const masterId = getMasterIdByEmail(user.email);
        
        const bookings = await api.getMasterBookings(masterId);
        const scheduleDiv = document.getElementById('masterSchedule');
        
        if (!scheduleDiv) return;
        
        if (bookings.success && bookings.master_bookings && bookings.master_bookings.length > 0) {
            scheduleDiv.innerHTML = bookings.master_bookings.map(booking => `
                <div class="session-card">
                    <div class="session-info">
                        <h4>${booking.user || `Клиент #${booking.user_id}`}</h4>
                        <p>${booking.date} в ${booking.time}</p>
                    </div>
                    <div class="session-actions">
                        <button class="btn-success" onclick="completeMasterVisit(${masterId}, ${booking.user_id}, '${booking.date}', '${booking.time}', '${booking.user}')">
                            <i class="fas fa-check"></i> Завершить
                        </button>
                        <button class="btn-danger" onclick="cancelMasterBooking(${masterId}, ${booking.user_id}, '${booking.date}', '${booking.time}')">
                            <i class="fas fa-times"></i> Отменить
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            scheduleDiv.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-calendar" style="font-size: 48px; margin-bottom: 20px; opacity: 0.3;"></i>
                    <p>Активных записей нет</p>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('masterSchedule').innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #dc3545; margin-bottom: 20px;"></i>
                <p style="color: #666;">Ошибка загрузки расписания</p>
            </div>
        `;
    }
}

async function loadMasterVisitHistory() {
    try {
        const user = api.getCurrentUser();
        const masterId = getMasterIdByEmail(user.email);
        
        const response = await fetch(`http://localhost:5001/master_visit_history/${masterId}`);
        const history = await response.json();
        
        const historyDiv = document.getElementById('masterVisitHistory');
        if (!historyDiv) return;
        
        if (history.success && history.visits && history.visits.length > 0) {
            historyDiv.innerHTML = history.visits.map(visit => `
                <div class="session-card">
                    <div class="session-info">
                        <h4>${visit.client_name || 'Клиент'}</h4>
                        <p>${visit.date} в ${visit.time}</p>
                        <p>Статус: <span class="session-status ${visit.status}">${
                            visit.status === 'completed' ? 'Завершен' : 'Отменен'
                        }</span></p>
                    </div>
                </div>
            `).join('');
        } else {
            historyDiv.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-history" style="font-size: 48px; margin-bottom: 20px; opacity: 0.3;"></i>
                    <p>История посещений пуста</p>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('masterVisitHistory').innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #dc3545; margin-bottom: 20px;"></i>
                <p style="color: #666;">Ошибка загрузки истории</p>
            </div>
        `;
    }
}

function getMasterIdByEmail(email) {
    if (email.includes('anna')) return 1;
    if (email.includes('boris')) return 2;
    return 1;
}

async function completeMasterVisit(masterId, clientId, date, time, clientName = 'Клиент') {
    if (!confirm('Подтвердить завершение визита?')) return;
    
    try {
        const response = await fetch('http://localhost:5001/add_master_visit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                master_id: masterId,
                client_id: clientId,
                client_name: clientName || `Клиент #${clientId}`,
                date: date,
                time: time,
                status: 'completed'
            })
        });
        
        if (response.ok) {
            await api.freeSlot(masterId, date, time);
            showNotification('success', 'Визит завершен');
            
            await loadMasterSchedule();
            await loadMasterVisitHistory();
        } else {
            showNotification('error', 'Ошибка завершения визита');
        }
    } catch (error) {
        showNotification('error', 'Ошибка соединения');
    }
}

async function cancelMasterBooking(masterId, clientId, date, time) {
    if (!confirm('Отменить запись?')) return;
    
    try {
        await api.freeSlot(masterId, date, time);
        
        await fetch('http://localhost:5001/add_master_visit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                master_id: masterId,
                client_id: clientId,
                client_name: 'Отменено мастером',
                date: date,
                time: time,
                status: 'cancelled'
            })
        });
        
        showNotification('success', 'Запись отменена');
        
        await loadMasterSchedule();
        await loadMasterVisitHistory();
    } catch (error) {
        showNotification('error', 'Ошибка отмены записи');
    }
}

// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
function formatDate(date) {
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    return `${day}.${month}.${date.getFullYear()}`;
}

function getDayName(dayIndex) {
    const days = ['ВС', 'ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ'];
    return days[dayIndex];
}

function initNotifications() {
    const notificationDiv = document.createElement('div');
    notificationDiv.id = 'notificationContainer';
    document.body.appendChild(notificationDiv);
}

function showNotification(type, message) {
    const container = document.getElementById('notificationContainer');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const icon = type === 'success' ? 'fa-check-circle' :
                 type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle';
    
    notification.innerHTML = `
        <i class="fas ${icon}"></i>
        <div class="notification-content">
            <h4>${type === 'success' ? 'Успешно!' : type === 'error' ? 'Ошибка!' : 'Информация'}</h4>
            <p>${message}</p>
        </div>
    `;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function logout() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        api.logout();
        showLogin();
    }
}

async function getAdminDashboardHTML() {
    return `
        <div class="container">
            <div class="dashboard-header">
                <div class="user-info">
                    <div class="user-avatar">
                        <i class="fas fa-crown"></i>
                    </div>
                    <div class="user-details">
                        <h3>${api.getCurrentUser().name}</h3>
                        <span class="role-badge">Администратор</span>
                    </div>
                </div>
                <button class="btn-secondary" onclick="logout()">
                    <i class="fas fa-sign-out-alt"></i> Выйти
                </button>
            </div>
            
            <div class="dashboard-nav">
                <button class="nav-btn active" data-section="users">
                    <i class="fas fa-users"></i> Пользователи
                </button>
                <button class="nav-btn" data-section="stats">
                    <i class="fas fa-chart-bar"></i> Статистика
                </button>
            </div>
            
            <div class="dashboard-content">
                <div id="usersSection" class="content-section active">
                    <h2><i class="fas fa-users"></i> Управление пользователями</h2>
                    <div id="usersList" class="loading">
                        <div class="spinner"></div>
                        <p>Загрузка пользователей...</p>
                    </div>
                </div>
                
                <div id="statsSection" class="content-section">
                    <h2><i class="fas fa-chart-bar"></i> Статистика системы</h2>
                    <div id="adminStats" class="loading">
                        <div class="spinner"></div>
                        <p>Загрузка статистики...</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}