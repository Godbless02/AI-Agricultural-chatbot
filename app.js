const messagesContainer = document.getElementById('messages');
const chatInput = document.getElementById('chatInput');
const sendButton = document.getElementById('sendButton');
const voiceButton = document.getElementById('voiceButton');
const charCounter = document.getElementById('charCounter');
const clearChatButton = document.querySelector('.clear-chat-button');
const newConversationButton = document.getElementById('newChatBtn');
const historyToggleButton = null;
const historyClose = null;
const conversationHistory = null;
const historyOverlay = null;
const conversationList = null;
const themeToggleButton = document.querySelector('.theme-toggle-button');
const mobileMenuButton = document.querySelector('.mobile-menu-button');
const sidebar = document.getElementById('leftSidebar');
const mobileOverlay = document.getElementById('mobileOverlay');
const mobileLanguageWrapper = document.querySelector('.mobile-language-toggle');
const currentLangIndicator = document.getElementById('currentLangIndicator');
const suggestionsSidebar = document.getElementById('suggestionsSidebar');
const suggestionsClose = document.querySelector('.suggestions-close');
const suggestionsToggle = document.querySelector('.suggestions-toggle-button');
const enChips = document.getElementById('enChips');
const twChips = document.getElementById('twChips');
const enHistoryList = document.getElementById('enHistoryList');
const twHistoryList = document.getElementById('twHistoryList');

let selectedLanguage = 'en';
let currentTheme = 'day';
let typingIndicator = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let mediaStream = null;
let recordingTimer = null;
let recordingSeconds = 0;
let conversations = [];
let currentConversationId = null;

// ── WELCOME MESSAGES (FIX 4) ──────────────────────────────────────
const WELCOME = {
  en: 'Hello! I am AgriBotGH. Ask me any farming question in English and I will help you.',
  tw: 'Akwaaba! Yɛfrɛ me AgriBotGH. Wo bɛtumi abisa me nsɛmfua biara ɛfa kuaeɛ ho wɔ yɛ man yi mu.'
};

function getTimestamp() {
  const now = new Date();
  let hours = now.getHours();
  const minutes = now.getMinutes().toString().padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12 || 12;
  return `${hours}:${minutes} ${ampm}`;
}

function createWelcomeMessage() {
  const welcomeBox = document.createElement('div');
  welcomeBox.className = 'welcome-box';
  welcomeBox.textContent = WELCOME[selectedLanguage];
  messagesContainer.appendChild(welcomeBox);
  scrollToBottom();
}

function appendMessage({ text, type, skipAddToHistory }) {
  const messageCard = document.createElement('div');
  messageCard.className = `message-card ${type}-message`;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  if (type === 'bot') {
    const icon = document.createElement('span');
    icon.className = 'message-icon';
    icon.textContent = '🤖';
    bubble.appendChild(icon);
  }
  const messageText = document.createElement('span');
  messageText.textContent = text;
  bubble.appendChild(messageText);
  messageCard.appendChild(bubble);
  const timestamp = document.createElement('div');
  timestamp.className = 'message-timestamp' + (type === 'user' ? ' right' : '');
  timestamp.textContent = getTimestamp();
  messageCard.appendChild(timestamp);
  messagesContainer.appendChild(messageCard);
  if (!skipAddToHistory) addMessageToCurrentConversation(text, type);
  scrollToBottom();
}

function showTypingIndicator() {
  typingIndicator = document.createElement('div');
  typingIndicator.className = 'message-card typing-indicator';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  const dots = document.createElement('div');
  dots.className = 'typing-dots';
  dots.innerHTML = '<span>●</span><span>●</span><span>●</span>';
  bubble.appendChild(dots);
  typingIndicator.appendChild(bubble);
  messagesContainer.appendChild(typingIndicator);
  scrollToBottom();
}

function hideTypingIndicator() {
  if (typingIndicator) { typingIndicator.remove(); typingIndicator = null; }
}

function clearChat() {
  messagesContainer.innerHTML = '';
  chatInput.value = '';
  updateCharCounter();
  createNewConversation();
  createWelcomeMessage();
  chatInput.focus();
}

function handleSend() {
  const text = chatInput.value.trim();
  if (!text) return;
  appendMessage({ text, type: 'user' });
  chatInput.value = '';
  updateCharCounter();
  chatInput.focus();
  showTypingIndicator();
  sendToBackend(text, selectedLanguage).then((response) => {
    hideTypingIndicator();
    appendMessage({ text: response, type: 'bot' });
  });
}

async function sendToBackend(message, language) {
  try {
    const response = await fetch('http://127.0.0.1:5000/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, language })
    });
    const data = await response.json();
    return data.response;
  } catch (error) {
    return 'Sorry, the backend is unavailable right now. Please make sure the server is running.';
  }
}

// ── CHARACTER COUNTER ─────────────────────────────────────────────
function updateCharCounter() {
  const len = chatInput.value.length;
  charCounter.textContent = `${len}/2000`;
  charCounter.classList.toggle('warning', len > 1800);
}

// ── FIX 1: Language toggle with clear highlight + chip swap ───────
function setLanguage(lang) {
  selectedLanguage = lang;

  // Update all lang buttons
  document.querySelectorAll('.lang-button').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });

  // Update indicator
  currentLangIndicator.innerHTML = `Chatting in: <strong>${lang === 'en' ? 'English' : 'Twi'}</strong>`;

  // Swap chips in right sidebar
  if (enChips) enChips.style.display = lang === 'en' ? 'flex' : 'none';
  if (twChips) twChips.style.display = lang === 'tw' ? 'flex' : 'none';

  // Update placeholder
  chatInput.placeholder = lang === 'en' ? 'Type your question here...' : 'Twerɛ wo asemmisa wɔ ha...';

  // Update welcome message if it exists in chat
  const welcomeBox = messagesContainer.querySelector('.welcome-box');
  if (welcomeBox) {
    welcomeBox.textContent = WELCOME[lang];
  }
}

function setupLanguageToggle() {
  document.querySelectorAll('.lang-button').forEach((btn) => {
    btn.addEventListener('click', () => setLanguage(btn.dataset.lang));
  });

  if (mobileLanguageWrapper) {
    ['en', 'tw'].forEach((lang, i) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'lang-button' + (i === 0 ? ' active' : '');
      btn.dataset.lang = lang;
      btn.textContent = lang === 'en' ? 'English' : 'Twi';
      btn.addEventListener('click', () => setLanguage(lang));
      mobileLanguageWrapper.appendChild(btn);
    });
  }
}

// ── RIGHT SIDEBAR TOGGLE (FIX 2) ─────────────────────────────────
function setupSuggestionsSidebar() {
  if (suggestionsClose) {
    suggestionsClose.addEventListener('click', () => {
      suggestionsSidebar.classList.remove('open');
    });
  }
  if (suggestionsToggle) {
    suggestionsToggle.addEventListener('click', () => {
      suggestionsSidebar.classList.toggle('open');
    });
  }
}

function setupQuickChips() {
  document.querySelectorAll('.chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      chatInput.value = chip.textContent;
      updateCharCounter();
      chatInput.focus();
      // Auto-switch language if chip is Twi and current is English
      if (chip.dataset.lang && chip.dataset.lang !== selectedLanguage) {
        setLanguage(chip.dataset.lang);
      }
    });
  });
}

function setupMobileSidebar() {
  if (mobileMenuButton) {
    mobileMenuButton.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
      mobileOverlay.style.display = sidebar.classList.contains('mobile-open') ? 'block' : 'none';
    });
  }
  if (mobileOverlay) {
    mobileOverlay.addEventListener('click', () => {
      sidebar.classList.remove('mobile-open');
      mobileOverlay.style.display = 'none';
    });
  }
}

// ── VOICE RECORDING — Fully self-contained, no Google API ────────
// Uses: MediaRecorder (audio capture) + Web Audio API (waveform visualizer)
// Transcription: browser-native SpeechRecognition runs SIMULTANEOUSLY
//                while recording so no external calls happen after stop

let recognition = null;
let liveTranscript = '';
let audioContext = null;
let analyser = null;
let animationId = null;

function formatTime(secs) {
  return `${Math.floor(secs/60).toString().padStart(2,'0')}:${(secs%60).toString().padStart(2,'0')}`;
}

function micIconHTML() {
  return `<svg class="voice-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M12 1c-1.657 0-3 1.343-3 3v7c0 1.657 1.343 3 3 3s3-1.343 3-3V4c0-1.657-1.343-3-3-3z"/>
    <path d="M19 10c0 3.314-2.686 6-6 6s-6-2.686-6-6"/>
    <line x1="12" y1="19" x2="12" y2="23"/>
    <line x1="8" y1="23" x2="16" y2="23"/>
  </svg>`;
}

function startRecordingTimer() {
  recordingSeconds = 0;
  voiceButton.setAttribute('data-timer', '00:00');
  recordingTimer = setInterval(() => {
    recordingSeconds++;
    voiceButton.setAttribute('data-timer', formatTime(recordingSeconds));
    if (recordingSeconds >= 120) stopVoiceRecording(); // 2 min max
  }, 1000);
}

function stopRecordingTimer() {
  if (recordingTimer) { clearInterval(recordingTimer); recordingTimer = null; }
  voiceButton.removeAttribute('data-timer');
}

// Draw live waveform on canvas while recording
function startWaveform(stream) {
  const canvas = document.getElementById('voiceCanvas');
  if (!canvas) return;
  canvas.style.display = 'block';
  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  analyser = audioContext.createAnalyser();
  analyser.fftSize = 64;
  const source = audioContext.createMediaStreamSource(stream);
  source.connect(analyser);
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  const ctx = canvas.getContext('2d');

  function draw() {
    animationId = requestAnimationFrame(draw);
    analyser.getByteFrequencyData(dataArray);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const barW = canvas.width / bufferLength;
    dataArray.forEach((val, i) => {
      const barH = (val / 255) * canvas.height;
      ctx.fillStyle = `rgba(46,125,50,${0.4 + (val/255)*0.6})`;
      ctx.fillRect(i * barW, canvas.height - barH, barW - 1, barH);
    });
  }
  draw();
}

function stopWaveform() {
  if (animationId) { cancelAnimationFrame(animationId); animationId = null; }
  if (audioContext) { audioContext.close(); audioContext = null; }
  const canvas = document.getElementById('voiceCanvas');
  if (canvas) canvas.style.display = 'none';
}

// Start speech recognition simultaneously with recording
function startLiveRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return;

  recognition = new SpeechRecognition();
  recognition.lang = selectedLanguage === 'tw' ? 'ak-GH' : 'en-GH';
  recognition.continuous = true;       // keeps listening without stopping
  recognition.interimResults = true;   // shows partial results live
  liveTranscript = '';

  recognition.onresult = (event) => {
    let interim = '';
    let final = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const t = event.results[i][0].transcript;
      if (event.results[i].isFinal) final += t;
      else interim += t;
    }
    liveTranscript += final;
    // Show live transcription in input box as user speaks
    chatInput.value = liveTranscript + interim;
    updateCharCounter();
  };

  recognition.onerror = () => {}; // silent — MediaRecorder is still capturing
  recognition.onend = () => {
    // Auto-restart if still recording (continuous mode can cut off)
    if (isRecording) recognition.start();
  };

  recognition.start();
}

async function startVoiceRecording() {
  try {
    // Request mic once — browser shows its own one-time permission dialog
    // After first grant, it never asks again for this site
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    showVoiceError('Microphone access denied. Please allow microphone access in your browser settings.');
    return;
  }

  // Set up MediaRecorder for audio capture
  audioChunks = [];
  mediaRecorder = new MediaRecorder(mediaStream, { mimeType: 'audio/webm' });
  mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
  mediaRecorder.onstop = () => {
    mediaStream.getTracks().forEach(t => t.stop());
    stopWaveform();
  };

  isRecording = true;
  liveTranscript = '';
  chatInput.value = '';
  chatInput.placeholder = selectedLanguage === 'en' ? 'Listening...' : 'Retie...';

  voiceButton.classList.add('recording');
  voiceButton.innerHTML = '⏹';
  voiceButton.setAttribute('aria-label', 'Stop recording');

  startRecordingTimer();
  startWaveform(mediaStream);
  startLiveRecognition();   // transcription runs simultaneously
  mediaRecorder.start(200);
}

function stopVoiceRecording() {
  if (!isRecording) return;
  isRecording = false;

  stopRecordingTimer();

  // Stop speech recognition
  if (recognition) {
    recognition.onend = null; // prevent auto-restart
    recognition.stop();
    recognition = null;
  }

  // Stop media recorder
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();

  voiceButton.classList.remove('recording');
  voiceButton.innerHTML = micIconHTML();
  voiceButton.setAttribute('aria-label', 'Record voice message');
  chatInput.placeholder = selectedLanguage === 'en' ? 'Type your question here...' : 'Kyerɛ wo asemmisa ha...';

  // Put final transcript in input for user to review
  const finalText = chatInput.value.trim();
  if (finalText) {
    // Show green tip
    const tip = document.createElement('div');
    tip.className = 'voice-tip';
    tip.textContent = '✅ Voice captured — review then press Send';
    messagesContainer.appendChild(tip);
    scrollToBottom();
    setTimeout(() => { if (tip.parentNode) tip.remove(); }, 3000);
    chatInput.focus();
    chatInput.select();
  } else {
    chatInput.value = '';
    chatInput.placeholder = selectedLanguage === 'en' ? 'Type your question here...' : 'Kyerɛ wo asemmisa ha...';
  }
}

function showVoiceError(msg) {
  const err = document.createElement('div');
  err.className = 'voice-tip error';
  err.textContent = '⚠️ ' + msg;
  messagesContainer.appendChild(err);
  scrollToBottom();
  setTimeout(() => { if (err.parentNode) err.remove(); }, 4000);
}

// ── THEME ─────────────────────────────────────────────────────────
function applyTheme(theme) {
  currentTheme = theme;
  document.body.dataset.theme = theme;
  if (themeToggleButton) {
    themeToggleButton.textContent = theme === 'day' ? '🌙' : '☀️';
    themeToggleButton.setAttribute('aria-label', theme === 'day' ? 'Switch to night theme' : 'Switch to day theme');
  }
}
function toggleTheme() { applyTheme(currentTheme === 'day' ? 'night' : 'day'); }

// ── FIX 3: CONVERSATION HISTORY SPLIT BY LANGUAGE ─────────────────
function createNewConversation() {
  const id = Date.now();
  conversations.unshift({
    id, messages: [],
    title: 'New Chat',
    language: selectedLanguage,
    timestamp: new Date()
  });
  currentConversationId = id;
  renderSidebarHistory();
  return id;
}

function addMessageToCurrentConversation(text, type) {
  if (!currentConversationId) createNewConversation();
  const conv = conversations.find(c => c.id === currentConversationId);
  if (conv) {
    conv.messages.push({ text, type, timestamp: new Date() });
    if (conv.messages.length === 1 && type === 'user') {
      conv.title = text.substring(0, 25) + (text.length > 25 ? '...' : '');
      conv.language = selectedLanguage;
    }
    renderSidebarHistory();
  }
}

function renderSidebarHistory() {
  const enConvs = conversations.filter(c => c.language === 'en');
  const twConvs = conversations.filter(c => c.language === 'tw');

  // Render English conversations
  if (enHistoryList) {
    enHistoryList.innerHTML = '';
    if (enConvs.length === 0) {
      enHistoryList.innerHTML = '<p class="empty-state-small">None yet</p>';
    } else {
      enConvs.forEach(conv => {
        const item = document.createElement('div');
        item.className = 'history-mini-item' + (conv.id === currentConversationId ? ' active' : '');
        item.textContent = conv.title;
        item.title = conv.title;
        item.addEventListener('click', () => loadConversation(conv.id));
        enHistoryList.appendChild(item);
      });
    }
  }

  // Render Twi conversations
  if (twHistoryList) {
    twHistoryList.innerHTML = '';
    if (twConvs.length === 0) {
      twHistoryList.innerHTML = '<p class="empty-state-small">None yet</p>';
    } else {
      twConvs.forEach(conv => {
        const item = document.createElement('div');
        item.className = 'history-mini-item' + (conv.id === currentConversationId ? ' active' : '');
        item.textContent = conv.title;
        item.title = conv.title;
        item.addEventListener('click', () => loadConversation(conv.id));
        twHistoryList.appendChild(item);
      });
    }
  }
}

function renderFloatingHistory() {
  conversationList.innerHTML = '';
  if (conversations.length === 0) {
    conversationList.innerHTML = '<p class="empty-state">No conversations yet</p>';
    return;
  }
  conversations.forEach(conv => {
    const item = document.createElement('div');
    item.className = 'conversation-item' + (conv.id === currentConversationId ? ' active' : '');
    item.innerHTML = `<div class="conversation-title">${conv.title}</div><div class="conversation-time">${conv.language === 'en' ? '🇬🇧' : '🇬🇭'} ${formatTimeAgo(conv.timestamp)}</div>`;
    item.addEventListener('click', () => { loadConversation(conv.id); closeHistoryPanel(); });
    conversationList.appendChild(item);
  });
}

function loadConversation(id) {
  const conv = conversations.find(c => c.id === id);
  if (!conv) return;
  currentConversationId = id;
  setLanguage(conv.language);
  messagesContainer.innerHTML = '';
  if (conv.messages.length === 0) {
    createWelcomeMessage();
  } else {
    conv.messages.forEach(msg => appendMessage({ text: msg.text, type: msg.type, skipAddToHistory: true }));
  }
  renderSidebarHistory();
  closeHistoryPanel();
  scrollToBottom();
}

function formatTimeAgo(date) {
  const diff = Date.now() - date;
  const m = Math.floor(diff / 60000);
  const h = Math.floor(diff / 3600000);
  const d = Math.floor(diff / 86400000);
  if (m < 1) return 'Just now';
  if (m < 60) return `${m}m ago`;
  if (h < 24) return `${h}h ago`;
  if (d < 7) return `${d}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function toggleHistoryPanel() {
  conversationHistory.classList.toggle('open');
  historyOverlay.classList.toggle('open');
}
function closeHistoryPanel() {
  conversationHistory.classList.remove('open');
  historyOverlay.classList.remove('open');
}

function scrollToBottom() { messagesContainer.scrollTop = messagesContainer.scrollHeight; }

// ── EVENT LISTENERS ───────────────────────────────────────────────
sendButton.addEventListener('click', handleSend);
chatInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); handleSend(); } });
chatInput.addEventListener('input', updateCharCounter);
clearChatButton.addEventListener('click', clearChat);
newConversationButton.addEventListener('click', clearChat);
voiceButton.addEventListener('click', () => { if (!isRecording) startVoiceRecording(); else stopVoiceRecording(); });
if (themeToggleButton) themeToggleButton.addEventListener('click', toggleTheme);

// ── INIT ──────────────────────────────────────────────────────────
setupLanguageToggle();
setupSuggestionsSidebar();
setupQuickChips();
setupMobileSidebar();
applyTheme('day');
setLanguage('en');
clearChat();
