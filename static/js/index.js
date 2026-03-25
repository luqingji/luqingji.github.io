document.addEventListener('DOMContentLoaded', () => {
    // 加载主数据
    fetch('/data/daily.json?t=' + Date.now())
        .then(res => res.json())
        .then(data => {
            hideLoader();
            document.getElementById('date').textContent = data.date || '今日';
            if (data.updated_at) {
                const beijingTime = new Date(data.updated_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
                document.getElementById('update-time').textContent = `更新于 ${beijingTime}`;
            }
            if (data.summary) {
                document.getElementById('daily-summary').textContent = data.summary;
            }
            const displayDate = data.date;
            document.getElementById('easter-egg').textContent = getEasterEgg(displayDate);

            // 每日一歌
            if (data.songs && data.songs.length > 0) {
                document.getElementById('song-card').style.display = 'block';
                document.getElementById('songs-link').href = `/songs.html?date=${data.date}`;
                const dailySong = data.songs[0];
                const container = document.getElementById('daily-song');
                container.innerHTML = '';
                let playLink = null;
                if (dailySong.id) {
                    playLink = `https://music.163.com/#/song?id=${dailySong.id}`;
                } else if (dailySong.name && dailySong.artist) {
                    const query = encodeURIComponent(`${dailySong.name} ${dailySong.artist}`);
                    playLink = `https://music.163.com/#/search/m/?s=${query}`;
                }
                container.innerHTML = `
                    <div class="daily-song-item">
                        <div class="song-name">
                            ${escapeHtml(dailySong.name)}
                            ${playLink ? `<a href="${playLink}" target="_blank" class="play-icon" title="在网易云音乐播放">🎧</a>` : ''}
                        </div>
                        <div class="song-artist">${escapeHtml(dailySong.artist)}</div>
                        <div class="song-album">${escapeHtml(dailySong.album || '')}</div>
                        <div class="song-recommendation">${escapeHtml(dailySong.recommendation || '')}</div>
                    </div>
                `;
            }

            // 散落诗行
            if (data.sentence) {
                document.getElementById('sentence-card').style.display = 'block';
                const sentenceText = data.sentence.content || '';
                document.getElementById('sentence-content').textContent = sentenceText;
                document.getElementById('sentence-from').textContent = data.sentence.from ? `—— ${data.sentence.from}` : '';
                if (data.sentence.meaning) {
                    const meaningEl = document.getElementById('sentence-meaning');
                    meaningEl.textContent = data.sentence.meaning;
                    meaningEl.style.display = 'block';
                }
                document.getElementById('copy-sentence-btn').onclick = () => copyToClipboard(sentenceText);
                document.getElementById('share-sentence-btn').onclick = () => captureCard(document.getElementById('sentence-card'), `拾光驿站_${data.date}.png`);
            }

            // 墨香盲盒
            if (data.article) {
                document.getElementById('article-card').style.display = 'block';
                document.getElementById('article-title').textContent = data.article.title || '';
                let articleText = data.article.description || data.article.content || '';
                document.getElementById('article-desc').textContent = articleText;
                document.getElementById('article-author').textContent = data.article.author ? `—— ${data.article.author}` : '';
                if (data.article.url) {
                    document.getElementById('article-link').href = data.article.url;
                } else {
                    document.getElementById('article-link').style.display = 'none';
                }
                if (data.article.meaning) {
                    const meaningEl = document.getElementById('article-meaning');
                    meaningEl.textContent = data.article.meaning;
                    meaningEl.style.display = 'block';
                }
                const articleWords = countWords(articleText);
                document.getElementById('article-stats').textContent = formatStats(articleWords);
            }

            // 早报（去重+截断）
            if (data.zaobao && data.zaobao.news && data.zaobao.news.length > 0) {
                document.getElementById('zaobao-card').style.display = 'block';
                const weiyuEl = document.getElementById('zaobao-weiyu');
                if (data.zaobao.weiyu) {
                    weiyuEl.textContent = data.zaobao.weiyu;
                    weiyuEl.style.display = 'block';
                } else if (data.zaobao.summary) {
                    weiyuEl.textContent = data.zaobao.summary;
                    weiyuEl.style.display = 'block';
                } else {
                    weiyuEl.style.display = 'none';
                }

                // 音频
                const audioUrl = data.zaobao.audio;
                const playBtn = document.getElementById('zaobao-play-btn');
                const audioPlayer = document.getElementById('zaobao-audio-player');
                if (audioUrl && playBtn && audioPlayer) {
                    audioPlayer.src = audioUrl;
                    playBtn.style.display = 'inline-block';
                    playBtn.onclick = () => {
                        if (audioPlayer.paused) {
                            audioPlayer.play();
                            playBtn.textContent = '⏸️ 暂停';
                        } else {
                            audioPlayer.pause();
                            playBtn.textContent = '🔊 语音播报';
                        }
                    };
                    audioPlayer.onended = () => {
                        playBtn.textContent = '🔊 语音播报';
                    };
                    audioPlayer.onerror = () => {
                        playBtn.style.display = 'none';
                        console.error('早报音频加载失败');
                    };
                } else if (playBtn) {
                    playBtn.style.display = 'none';
                }

                // 新闻列表：去重 + 截断
                const rawNews = data.zaobao.news;
                const uniqueNews = [];
                const seenTitles = new Set();
                for (const item of rawNews) {
                    if (!seenTitles.has(item.title)) {
                        seenTitles.add(item.title);
                        uniqueNews.push(item);
                    }
                }
                const displayNews = uniqueNews.slice(0, 15); // 最多显示15条

                const listContainer = document.getElementById('zaobao-list');
                listContainer.innerHTML = '';
                displayNews.forEach(item => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'zaobao-item';
                    itemDiv.innerHTML = `
                        <div>
                            <span class="zaobao-title">${escapeHtml(item.title)}</span>
                            <span class="zaobao-source">${escapeHtml(item.source || '')}</span>
                        </div>
                        <div class="zaobao-summary-text">${escapeHtml(item.summary || '')}</div>
                    `;
                    if (item.url) {
                        const titleSpan = itemDiv.querySelector('.zaobao-title');
                        titleSpan.style.cursor = 'pointer';
                        titleSpan.style.color = '#4f9da6';
                        titleSpan.addEventListener('click', () => window.open(item.url, '_blank'));
                    }
                    listContainer.appendChild(itemDiv);
                });
                if (data.zaobao.date) {
                    document.getElementById('zaobao-date').textContent = data.zaobao.date;
                }
            }

            // 小说
            if (data.novels && Array.isArray(data.novels)) {
                document.getElementById('novel-card').style.display = 'block';
                renderNovels(data.novels);
            }

            // ONE · 一个
            if (data.one) {
                renderOneModule(data.one);
            }
        })
        .catch(err => {
            console.error(err);
            hideLoader();
            showError('数据加载失败，请稍后刷新');
        });

    // 加载统计数据并渲染侧边栏
    fetch('/data/stats.json?t=' + Date.now())
        .then(res => res.json())
        .then(stats => {
            renderStats(stats);
        })
        .catch(err => console.warn('统计加载失败', err));
});

// 渲染侧边栏统计
function renderStats(stats) {
    const leftSidebar = document.getElementById('stats-left');
    const rightSidebar = document.getElementById('stats-right');
    if (!leftSidebar || !rightSidebar) return;

    leftSidebar.innerHTML = `
        <h3>📊 拾光足迹</h3>
        <div class="stat-item"><span class="stat-label">运行天数</span><span class="stat-number">${stats.total_days || 0}</span></div>
        <div class="stat-item"><span class="stat-label">推荐歌曲</span><span class="stat-number">${stats.total_songs || 0}</span></div>
        <div class="stat-item"><span class="stat-label">精选文章</span><span class="stat-number">${stats.total_articles || 0}</span></div>
        <div class="stat-item"><span class="stat-label">原创小说</span><span class="stat-number">${stats.total_novels || 0}</span></div>
    `;

    rightSidebar.innerHTML = `
        <h3>📚 内容印记</h3>
        <div class="stat-item"><span class="stat-label">总字数</span><span class="stat-number">${(stats.total_words / 10000).toFixed(1)}万</span></div>
        <div class="stat-item"><span class="stat-label">推荐语字数</span><span class="stat-number">${(stats.total_recommend_words / 1000).toFixed(1)}k</span></div>
        <div class="stat-item"><span class="stat-label">早报资讯</span><span class="stat-number">${stats.total_news_items || 0}</span></div>
        <div class="stat-item"><span class="stat-label">ONE精选</span><span class="stat-number">${stats.total_one_items || 0}</span></div>
        <div class="stat-item"><span class="stat-label">阅读时长</span><span class="stat-number">${stats.read_minutes || 0}分钟</span></div>
    `;
}

// ==================== ONE模块渲染 ====================
function renderOneModule(oneData) {
    const oneCard = document.getElementById('one-card');
    const oneContainer = document.getElementById('one-content');
    oneContainer.innerHTML = '';
    let hasContent = false;

    if (oneData.article && oneData.article.content) {
        hasContent = true;
        const articleDiv = document.createElement('div');
        articleDiv.className = 'one-article';
        const contentHtml = escapeHtml(oneData.article.content).replace(/\n/g, '<br>');
        articleDiv.innerHTML = `
            <h3>📝 文章</h3>
            <div class="one-title">${escapeHtml(oneData.article.title)}</div>
            <div class="one-author">${escapeHtml(oneData.article.author || '')}</div>
            <div class="one-content-text">${contentHtml}</div>
        `;
        oneContainer.appendChild(articleDiv);
    }

    if (oneData.photo && oneData.photo.image) {
        hasContent = true;
        const photoDiv = document.createElement('div');
        photoDiv.className = 'one-photo';
        photoDiv.innerHTML = `
            <h3>📷 摄影</h3>
            <img src="${oneData.photo.image}" alt="${escapeHtml(oneData.photo.title || 'ONE摄影')}" class="one-photo-img" loading="lazy">
            <div class="one-title">${escapeHtml(oneData.photo.title || '')}</div>
            <div class="one-author">${escapeHtml(oneData.photo.author || '')}</div>
            <div class="one-desc">${escapeHtml(oneData.photo.description || '').replace(/\n/g, '<br>')}</div>
        `;
        oneContainer.appendChild(photoDiv);
    }

    if (oneData.question && oneData.question.question) {
        hasContent = true;
        const qaDiv = document.createElement('div');
        qaDiv.className = 'one-qa';
        qaDiv.innerHTML = `
            <h3>💬 问答</h3>
            <div class="one-question">${escapeHtml(oneData.question.question)}</div>
            <div class="one-answer">${escapeHtml(oneData.question.answer || '').replace(/\n/g, '<br>')}</div>
            ${oneData.question.author ? `<div class="one-author">—— ${escapeHtml(oneData.question.author)}</div>` : ''}
        `;
        oneContainer.appendChild(qaDiv);
    }

    if (hasContent) {
        oneCard.style.display = 'block';
    }
}

// ==================== 小说渲染 ====================
function renderNovels(novels) {
    const container = document.getElementById('novels-container');
    container.innerHTML = '';
    if (!novels || novels.length === 0) {
        container.innerHTML = '<p>暂无小说，请稍后再来。</p>';
        return;
    }
    novels.forEach(novel => {
        const novelDiv = document.createElement('div');
        novelDiv.className = 'novel-item';
        const title = novel.title || '无题';
        let content = novel.content || '';
        content = content.replace(/\\n/g, '\n');
        const paragraphs = content.split(/\n\s*\n/).filter(p => p.trim());
        const finalContent = paragraphs.join('\n\n');
        const wordCount = countWords(finalContent);
        const stats = formatStats(wordCount);

        const headerDiv = document.createElement('div');
        headerDiv.className = 'novel-header';
        headerDiv.innerHTML = `<div class="novel-title">${escapeHtml(title)}</div>`;
        const btnGroup = document.createElement('div');
        const speakBtn = document.createElement('button');
        speakBtn.className = 'speak-btn';
        speakBtn.textContent = '🔊 朗读';
        speakBtn.addEventListener('click', () => speakText(finalContent));
        const immerseBtn = document.createElement('button');
        immerseBtn.className = 'immerse-btn';
        immerseBtn.textContent = '🔍 沉浸';
        immerseBtn.addEventListener('click', () => {
            const html = `
                <div class="novel-title" style="font-size:2rem; margin-bottom:1rem;">${escapeHtml(title)}</div>
                <div class="novel-content">${paragraphs.map(p => `<p>${escapeHtml(p).replace(/\n/g, '<br>')}</p>`).join('')}</div>
                <div class="novel-stats">${stats}</div>
            `;
            openImmerse(html);
        });
        btnGroup.appendChild(speakBtn);
        btnGroup.appendChild(immerseBtn);
        headerDiv.appendChild(btnGroup);
        novelDiv.appendChild(headerDiv);

        const contentDiv = document.createElement('div');
        contentDiv.className = 'novel-content';
        contentDiv.innerHTML = paragraphs.map(p => `<p>${escapeHtml(p).replace(/\n/g, '<br>')}</p>`).join('');
        novelDiv.appendChild(contentDiv);

        const statsDiv = document.createElement('div');
        statsDiv.className = 'novel-stats';
        statsDiv.textContent = stats;
        novelDiv.appendChild(statsDiv);

        const aiReviews = [
            "📖 这篇小说像一杯温茶，慢慢品出人生滋味。",
            "🎭 虚构的世界里，藏着真实的情感。",
            "🌟 每一段文字都是时光的琥珀。",
            "💫 读完后，心里某个角落被轻轻触动。",
            "📜 故事虽短，余韵悠长。",
            "🌙 适合在夜深人静时再读一遍。",
            "🍃 像风一样轻，却留下痕迹。"
        ];
        const reviewDiv = document.createElement('div');
        reviewDiv.className = 'ai-review';
        reviewDiv.textContent = aiReviews[Math.floor(Math.random() * aiReviews.length)];
        novelDiv.appendChild(reviewDiv);

        container.appendChild(novelDiv);
    });
}
