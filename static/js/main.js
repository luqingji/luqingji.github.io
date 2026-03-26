// ==================== 暗色模式 ====================
function initDarkMode() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) themeToggle.innerHTML = '☀️ 亮色模式';
    }
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            themeToggle.innerHTML = isDark ? '☀️ 亮色模式' : '🌙 暗色模式';
        });
    }
}

// ==================== 语音朗读 ====================
let currentUtterance = null;

function stopSpeaking() {
    if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }
    if (currentUtterance) {
        currentUtterance = null;
    }
}

function speakText(text) {
    if (!window.speechSynthesis) {
        alert("您的浏览器不支持语音朗读");
        return;
    }
    stopSpeaking();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'zh-CN';
    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    currentUtterance = utterance;
    utterance.onend = () => { currentUtterance = null; };
    utterance.onerror = () => { currentUtterance = null; };
    window.speechSynthesis.speak(utterance);
}

// ==================== 沉浸模式 ====================
const modal = document.getElementById('immerse-modal');
const immerseContent = document.getElementById('immerse-content');
const closeImmerse = document.getElementById('close-immerse');

function openImmerse(htmlContent) {
    if (!modal || !immerseContent) return;
    immerseContent.innerHTML = htmlContent;
    modal.classList.add('active');
}

function closeImmerseModal() {
    if (modal) modal.classList.remove('active');
}

if (closeImmerse) {
    closeImmerse.addEventListener('click', closeImmerseModal);
}
if (modal) {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeImmerseModal();
    });
}

// ==================== 复制与截图 ====================
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('已复制');
    }).catch(() => alert('复制失败'));
}

function captureCard(element, filename = '拾光驿站.png') {
    if (!element) {
        alert('无法截取内容');
        return;
    }
    if (typeof html2canvas === 'undefined') {
        alert('截图库未加载，请稍后重试');
        return;
    }
    html2canvas(element, {
        scale: 2,
        backgroundColor: null,
        useCORS: true,
        logging: false
    }).then(canvas => {
        const link = document.createElement('a');
        link.download = filename;
        link.href = canvas.toDataURL('image/png');
        link.click();
    }).catch(err => {
        console.error(err);
        alert('生成图片失败，请重试');
    });
}

// ==================== Toast 提示 ====================
function showToast(message) {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2000);
}

// ==================== 字数统计 ====================
function countWords(text) {
    const chinese = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
    const english = (text.match(/[a-zA-Z]+/g) || []).length;
    return chinese + english;
}

function formatStats(words) {
    return `${words} 字 · 约 ${Math.ceil(words / 250)} 分钟阅读`;
}

// ==================== 彩蛋 ====================
function getEasterEgg(dateStr) {
    let baseDate = dateStr ? new Date(dateStr) : new Date();
    const seed = baseDate.toDateString();
    const eggs = [
        "✨ 今日彩蛋：再读一遍，或许会发现隐藏的温柔。",
        "🍂 今日彩蛋：时光不语，静待花开。",
        "📖 今日彩蛋：每一篇小说都是平行宇宙的你。",
        "🎵 今日彩蛋：未知旋律里藏着昨天的故事。",
        "💭 今日彩蛋：散落的诗行，是某人的心事。",
        "🌟 今日彩蛋：你正在阅读的，是宇宙送给你的礼物。",
        "🌙 今日彩蛋：此刻的宁静，胜过万语千言。",
        "☕ 今日彩蛋：读一段文字，饮一杯暖茶。"
    ];
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
        hash = ((hash << 5) - hash) + seed.charCodeAt(i);
        hash |= 0;
    }
    const index = Math.abs(hash) % eggs.length;
    return eggs[index];
}

// ==================== HTML 转义 ====================
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// ==================== 加载与错误处理 ====================
function showLoader() {
    const loader = document.getElementById('loader');
    if (loader) loader.style.display = 'flex';
}

function hideLoader() {
    const loader = document.getElementById('loader');
    if (loader) loader.style.display = 'none';
}

function showError(message, retryCallback = null) {
    const container = document.getElementById('content') || document.body;
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `<p style="color:#bf6f5a; text-align:center;">${message}</p>`;
    if (retryCallback) {
        const retryBtn = document.createElement('button');
        retryBtn.textContent = '重试';
        retryBtn.onclick = retryCallback;
        errorDiv.appendChild(retryBtn);
    }
    container.appendChild(errorDiv);
}

// ==================== 页面通用初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    initDarkMode();

    // 随机渐变背景
    const gradients = [
        "linear-gradient(145deg, #f9f3e8 0%, #d9e2f0 100%)",
        "linear-gradient(135deg, #e8f0f5 0%, #d0e0e8 100%)",
        "linear-gradient(145deg, #f5efe9 0%, #e0d8cf 100%)",
        "linear-gradient(135deg, #fdf8ed 0%, #eae3d5 100%)",
        "linear-gradient(145deg, #f2e9e1 0%, #dcd3c6 100%)",
        "linear-gradient(135deg, #ebf0f5 0%, #cbdbe0 100%)"
    ];
    const randomGradient = gradients[Math.floor(Math.random() * gradients.length)];
    document.body.style.background = randomGradient;

    // 回到顶部按钮
    const goTopBtn = document.getElementById('go-top');
    if (goTopBtn) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 300) goTopBtn.classList.add('visible');
            else goTopBtn.classList.remove('visible');
        });
        goTopBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    }
});
