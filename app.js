const API = 'http://127.0.0.1:5000';

const messagesContainer = document.getElementById('messages');
const chatInput = document.getElementById('chatInput');
const sendButton = document.getElementById('sendButton');
const voiceButton = document.getElementById('voiceButton');
const charCounter = document.getElementById('charCounter');
const clearChatButton = document.querySelector('.clear-chat-button');
const newChatBtn = document.getElementById('newChatBtn');
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
const userBadge = document.getElementById('userBadge');
const loginBtn = document.getElementById('loginBtn');
const logoutBtn = document.getElementById('logoutBtn');

let selectedLanguage = 'en';
let currentTheme = 'day';
let typingIndicator = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let mediaStream = null;
let recordingTimer = null;
let recordingSeconds = 0;
let currentUser = null;

// Separate session id per language — this is the core fix
let enSessionId = null;
let twSessionId = null;

const WELCOME = {
  en: 'Hello! I am AgriBotGH. Ask me any farming question in English or Twi and I will help you.',
  tw: "Akwaaba! Yɛfrɛ me AgriBotGH. Wo bɛtumi abisa me nsɛmfua biara ɛfa kuaeɛ ho wɔ yɛ man yi mu."
};

function personalisedWelcome(lang){
  if(!currentUser) return WELCOME[lang];
  const name = currentUser.username;
  if(lang === 'en') return `Hello ${name}! 🌱 I am AgriBotGH. Ask me any farming question in English or Twi and I will help you.`;
  return `Akwaaba ${name}! 🌱 Yɛfrɛ me AgriBotGH. Wo bɛtumi abisa me nsɛmfua biara ɛfa kuaeɛ ho wɔ yɛ man yi mu.`;
}

function getTimestamp(){
  const now=new Date(); let h=now.getHours(); const m=now.getMinutes().toString().padStart(2,'0');
  const ap=h>=12?'PM':'AM'; h=h%12||12; return `${h}:${m} ${ap}`;
}

function createWelcomeMessage(){
  const box=document.createElement('div');
  box.className='welcome-box';
  box.textContent=personalisedWelcome(selectedLanguage);
  messagesContainer.appendChild(box);
  scrollToBottom();
}

function appendMessage({text,type,skipSave}){
  const card=document.createElement('div');
  card.className=`message-card ${type}-message`;
  const bubble=document.createElement('div');
  bubble.className='bubble';
  if(type==='bot'){
    const icon=document.createElement('span');
    icon.className='message-icon'; icon.textContent='🤖';
    bubble.appendChild(icon);
  }
  const span=document.createElement('span'); span.textContent=text;
  bubble.appendChild(span); card.appendChild(bubble);
  const ts=document.createElement('div');
  ts.className='message-timestamp'+(type==='user'?' right':'');
  ts.textContent=getTimestamp();
  card.appendChild(ts);
  messagesContainer.appendChild(card);
  scrollToBottom();
}

function showTypingIndicator(){
  typingIndicator=document.createElement('div');
  typingIndicator.className='message-card typing-indicator';
  const bubble=document.createElement('div'); bubble.className='bubble';
  const dots=document.createElement('div'); dots.className='typing-dots';
  dots.innerHTML='<span>●</span><span>●</span><span>●</span>';
  bubble.appendChild(dots); typingIndicator.appendChild(bubble);
  messagesContainer.appendChild(typingIndicator); scrollToBottom();
}
function hideTypingIndicator(){ if(typingIndicator){typingIndicator.remove(); typingIndicator=null;} }

function generateSessionId(){ return 'sess_'+Date.now()+'_'+Math.random().toString(36).substr(2,9); }

function getCurrentSessionId(){
  return selectedLanguage==='en' ? enSessionId : twSessionId;
}
function setCurrentSessionId(id){
  if(selectedLanguage==='en') enSessionId=id; else twSessionId=id;
}

// ── CLEAR / NEW CHAT ──────────────────────────────────────────────
function startFreshChat(lang){
  messagesContainer.innerHTML='';
  if(lang==='en') enSessionId = generateSessionId();
  else twSessionId = generateSessionId();
  createWelcomeMessage();
}

function clearChat(){
  startFreshChat(selectedLanguage);
  chatInput.value=''; updateCharCounter(); chatInput.focus();
}

// ── SEND MESSAGE ──────────────────────────────────────────────────
function handleSend(){
  const text=chatInput.value.trim();
  if(!text) return;
  appendMessage({text,type:'user'});
  chatInput.value=''; updateCharCounter(); chatInput.focus();
  showTypingIndicator();
  sendToBackend(text,selectedLanguage).then(response=>{
    hideTypingIndicator();
    appendMessage({text:response,type:'bot'});
    if(currentUser) loadSidebarHistory();
  });
}

async function sendToBackend(message,language){
  try{
    if(!getCurrentSessionId()) setCurrentSessionId(generateSessionId());
    const res=await fetch(`${API}/api/chat`,{
      method:'POST', credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message,language,session_id:getCurrentSessionId()})
    });
    const data=await res.json();
    return data.response;
  }catch(e){
    return 'Sorry, the backend is unavailable right now. Please make sure the server is running.';
  }
}

// ── CHAR COUNTER ──────────────────────────────────────────────────
function updateCharCounter(){
  const len=chatInput.value.length;
  charCounter.textContent=`${len}/2000`;
  charCounter.classList.toggle('warning',len>1800);
}

// ── LANGUAGE SWITCH (CORE FIX) ─────────────────────────────────────
// When switching language: save current chat to its history (already
// saved via backend as it happens) then load that language's most
// recent session OR start a fresh chat if none exists yet.
function setLanguage(lang){
  if(lang === selectedLanguage) return; // no-op if same

  selectedLanguage = lang;

  document.querySelectorAll('.lang-button').forEach(btn=>{
    btn.classList.toggle('active', btn.dataset.lang===lang);
  });

  currentLangIndicator.innerHTML = `Chatting in: <strong>${lang==='en'?'English':'Twi'}</strong>`;

  if(enChips) enChips.style.display = lang==='en' ? 'flex' : 'none';
  if(twChips) twChips.style.display = lang==='tw' ? 'flex' : 'none';

  chatInput.placeholder = lang==='en' ? 'Type your question here...' : 'Kyerɛ wo asemmisa ha...';

  // Clear the view and start a brand new chat for this language
  // (previous language's chat remains saved in its own session)
  startFreshChat(lang);
}

function setupLanguageToggle(){
  document.querySelectorAll('.lang-button').forEach(btn=>{
    btn.addEventListener('click',()=>setLanguage(btn.dataset.lang));
  });
  if(mobileLanguageWrapper){
    ['en','tw'].forEach((lang,i)=>{
      const btn=document.createElement('button');
      btn.type='button';
      btn.className='lang-button'+(i===0?' active':'');
      btn.dataset.lang=lang;
      btn.textContent=lang==='en'?'English':'Twi';
      btn.addEventListener('click',()=>setLanguage(lang));
      mobileLanguageWrapper.appendChild(btn);
    });
  }
}

// ── SUGGESTIONS SIDEBAR ─────────────────────────────────────────
function setupSuggestionsSidebar(){
  if(suggestionsClose) suggestionsClose.addEventListener('click',()=>suggestionsSidebar.classList.remove('open'));
  if(suggestionsToggle) suggestionsToggle.addEventListener('click',()=>suggestionsSidebar.classList.toggle('open'));
}
function setupQuickChips(){
  document.querySelectorAll('.chip').forEach(chip=>{
    chip.addEventListener('click',()=>{
      chatInput.value=chip.textContent; updateCharCounter(); chatInput.focus();
      if(chip.dataset.lang && chip.dataset.lang!==selectedLanguage) setLanguage(chip.dataset.lang);
    });
  });
}
function setupMobileSidebar(){
  if(mobileMenuButton) mobileMenuButton.addEventListener('click',()=>{
    sidebar.classList.toggle('mobile-open');
    mobileOverlay.style.display=sidebar.classList.contains('mobile-open')?'block':'none';
  });
  if(mobileOverlay) mobileOverlay.addEventListener('click',()=>{
    sidebar.classList.remove('mobile-open');
    mobileOverlay.style.display='none';
  });
}

// ── VOICE RECORDING (self-contained, no external API) ─────────────
function formatTime(s){return `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`;}
function micIconHTML(){
  return `<svg class="voice-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M12 1c-1.657 0-3 1.343-3 3v7c0 1.657 1.343 3 3 3s3-1.343 3-3V4c0-1.657-1.343-3-3-3z"/>
    <path d="M19 10c0 3.314-2.686 6-6 6s-6-2.686-6-6"/>
    <line x1="12" y1="19" x2="12" y2="23"/>
    <line x1="8" y1="23" x2="16" y2="23"/>
  </svg>`;
}
let recognition=null, liveTranscript='', audioContext=null, analyser=null, animationId=null;

function startRecordingTimer(){
  recordingSeconds=0; voiceButton.setAttribute('data-timer','00:00');
  recordingTimer=setInterval(()=>{
    recordingSeconds++;
    voiceButton.setAttribute('data-timer',formatTime(recordingSeconds));
    if(recordingSeconds>=120) stopVoiceRecording();
  },1000);
}
function stopRecordingTimer(){ if(recordingTimer){clearInterval(recordingTimer); recordingTimer=null;} voiceButton.removeAttribute('data-timer'); }

function startWaveform(stream){
  const canvas=document.getElementById('voiceCanvas');
  if(!canvas) return;
  canvas.style.display='block';
  audioContext=new (window.AudioContext||window.webkitAudioContext)();
  analyser=audioContext.createAnalyser(); analyser.fftSize=64;
  const source=audioContext.createMediaStreamSource(stream); source.connect(analyser);
  const bufferLength=analyser.frequencyBinCount; const dataArray=new Uint8Array(bufferLength);
  const ctx=canvas.getContext('2d');
  function draw(){
    animationId=requestAnimationFrame(draw);
    analyser.getByteFrequencyData(dataArray);
    ctx.clearRect(0,0,canvas.width,canvas.height);
    const barW=canvas.width/bufferLength;
    dataArray.forEach((val,i)=>{
      const barH=(val/255)*canvas.height;
      ctx.fillStyle=`rgba(46,125,50,${0.4+(val/255)*0.6})`;
      ctx.fillRect(i*barW,canvas.height-barH,barW-1,barH);
    });
  }
  draw();
}
function stopWaveform(){
  if(animationId){cancelAnimationFrame(animationId); animationId=null;}
  if(audioContext){audioContext.close(); audioContext=null;}
  const canvas=document.getElementById('voiceCanvas');
  if(canvas) canvas.style.display='none';
}

function startLiveRecognition(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR) return;
  recognition=new SR();
  recognition.lang=selectedLanguage==='tw'?'ak-GH':'en-GH';
  recognition.continuous=true; recognition.interimResults=true;
  liveTranscript='';
  recognition.onresult=(event)=>{
    let interim='',final='';
    for(let i=event.resultIndex;i<event.results.length;i++){
      const t=event.results[i][0].transcript;
      if(event.results[i].isFinal) final+=t; else interim+=t;
    }
    liveTranscript+=final;
    chatInput.value=liveTranscript+interim;
    updateCharCounter();
  };
  recognition.onerror=()=>{};
  recognition.onend=()=>{ if(isRecording) recognition.start(); };
  recognition.start();
}

async function startVoiceRecording(){
  try{
    mediaStream=await navigator.mediaDevices.getUserMedia({audio:true});
  }catch(err){
    showTip('⚠️ Microphone access denied. Please allow microphone access in browser settings.','error');
    return;
  }
  audioChunks=[];
  mediaRecorder=new MediaRecorder(mediaStream,{mimeType:'audio/webm'});
  mediaRecorder.ondataavailable=(e)=>{if(e.data.size>0)audioChunks.push(e.data);};
  mediaRecorder.onstop=()=>{ mediaStream.getTracks().forEach(t=>t.stop()); stopWaveform(); };

  isRecording=true; liveTranscript=''; chatInput.value='';
  chatInput.placeholder=selectedLanguage==='en'?'Listening...':'Retie...';
  voiceButton.classList.add('recording'); voiceButton.innerHTML='⏹';
  voiceButton.setAttribute('aria-label','Stop recording');

  startRecordingTimer(); startWaveform(mediaStream); startLiveRecognition();
  mediaRecorder.start(200);
}

function stopVoiceRecording(){
  if(!isRecording) return;
  isRecording=false; stopRecordingTimer();
  if(recognition){ recognition.onend=null; recognition.stop(); recognition=null; }
  if(mediaRecorder && mediaRecorder.state!=='inactive') mediaRecorder.stop();
  voiceButton.classList.remove('recording'); voiceButton.innerHTML=micIconHTML();
  voiceButton.setAttribute('aria-label','Record voice message');
  chatInput.placeholder=selectedLanguage==='en'?'Type your question here...':'Kyerɛ wo asemmisa ha...';

  const finalText=chatInput.value.trim();
  if(finalText){
    showTip('✅ Voice captured — review then press Send','success');
    chatInput.focus(); chatInput.select();
  }
}

function showTip(text,type='success'){
  const el=document.createElement('div');
  el.className='voice-tip'+(type==='error'?' error':'');
  el.textContent=text;
  messagesContainer.appendChild(el); scrollToBottom();
  setTimeout(()=>{if(el.parentNode)el.remove();},3000);
}

// ── THEME ─────────────────────────────────────────────────────────
function applyTheme(theme){
  currentTheme=theme;
  document.body.dataset.theme=theme;
  if(themeToggleButton){
    themeToggleButton.textContent=theme==='day'?'🌙':'☀️';
    themeToggleButton.setAttribute('aria-label',theme==='day'?'Switch to night theme':'Switch to day theme');
  }
}
function toggleTheme(){ applyTheme(currentTheme==='day'?'night':'day'); }

// ── AUTH ──────────────────────────────────────────────────────────
async function checkAuth(){
  try{
    const res=await fetch(`${API}/api/auth/me`,{credentials:'include'});
    if(res.ok){
      const data=await res.json();
      currentUser=data.user;
    } else {
      currentUser=null;
    }
  }catch(e){ currentUser=null; }
  updateUserUI();
}

function updateUserUI(){
  if(currentUser){
    if(userBadge) userBadge.textContent='👤 '+currentUser.username;
    if(logoutBtn) logoutBtn.style.display='inline-flex';
    if(loginBtn) loginBtn.style.display='none';
    loadSidebarHistory();
  } else {
    if(userBadge) userBadge.textContent='';
    if(logoutBtn) logoutBtn.style.display='none';
    if(loginBtn) loginBtn.style.display='inline-flex';
  }
}

async function doLogout(){
  await fetch(`${API}/api/auth/logout`,{method:'POST',credentials:'include'});
  currentUser=null; updateUserUI();
  window.location.href='/auth.html';
}

// ── SAVED CHAT HISTORY (per-language) ──────────────────────────────
async function loadSidebarHistory(){
  if(!currentUser) return;
  try{
    const res=await fetch(`${API}/api/sessions`,{credentials:'include'});
    if(!res.ok) return;
    const data=await res.json();
    renderSidebarHistory(data.sessions);
  }catch(e){}
}

function renderSidebarHistory(sessions){
  if(!enHistoryList || !twHistoryList) return;
  const enS=sessions.filter(s=>s.language==='en');
  const twS=sessions.filter(s=>s.language==='tw');

  function build(list,container,activeId){
    container.innerHTML='';
    if(list.length===0){ container.innerHTML='<p class="empty-state-small">None yet</p>'; return; }
    list.forEach(sess=>{
      const item=document.createElement('div');
      item.className='history-mini-item'+(sess.id===activeId?' active':'');
      item.textContent=sess.title; item.title=sess.title;
      item.addEventListener('click',()=>loadSession(sess.id, sess.language));
      container.appendChild(item);
    });
  }
  build(enS, enHistoryList, enSessionId);
  build(twS, twHistoryList, twSessionId);
}

async function loadSession(sessId, lang){
  try{
    const res=await fetch(`${API}/api/sessions/${sessId}`,{credentials:'include'});
    if(!res.ok) return;
    const data=await res.json();

    if(lang !== selectedLanguage){
      selectedLanguage = lang;
      document.querySelectorAll('.lang-button').forEach(btn=>btn.classList.toggle('active', btn.dataset.lang===lang));
      currentLangIndicator.innerHTML = `Chatting in: <strong>${lang==='en'?'English':'Twi'}</strong>`;
      if(enChips) enChips.style.display = lang==='en' ? 'flex' : 'none';
      if(twChips) twChips.style.display = lang==='tw' ? 'flex' : 'none';
      chatInput.placeholder = lang==='en' ? 'Type your question here...' : 'Kyerɛ wo asemmisa ha...';
    }

    setCurrentSessionId(sessId);
    messagesContainer.innerHTML='';
    data.messages.forEach(msg=>appendMessage({text:msg.message,type:msg.role,skipSave:true}));
    scrollToBottom();
    loadSidebarHistory();
  }catch(e){}
}

function scrollToBottom(){ messagesContainer.scrollTop=messagesContainer.scrollHeight; }

// ── EVENT LISTENERS ───────────────────────────────────────────────
sendButton.addEventListener('click',handleSend);
chatInput.addEventListener('keydown',(e)=>{if(e.key==='Enter'){e.preventDefault();handleSend();}});
chatInput.addEventListener('input',updateCharCounter);
clearChatButton.addEventListener('click',clearChat);
if(newChatBtn) newChatBtn.addEventListener('click',clearChat);
voiceButton.addEventListener('click',()=>{ if(!isRecording) startVoiceRecording(); else stopVoiceRecording(); });
if(themeToggleButton) themeToggleButton.addEventListener('click',toggleTheme);
if(logoutBtn) logoutBtn.addEventListener('click', doLogout);

// ── INIT ──────────────────────────────────────────────────────────
setupLanguageToggle();
setupSuggestionsSidebar();
setupQuickChips();
setupMobileSidebar();
applyTheme('day');
checkAuth().then(()=>{
  selectedLanguage='en';
  document.querySelectorAll('.lang-button').forEach(btn=>btn.classList.toggle('active', btn.dataset.lang==='en'));
  startFreshChat('en');
});
