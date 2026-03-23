document.addEventListener('DOMContentLoaded', () => {
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
            // 彩蛋与历史上的今天使用数据中的日期
            const displayDate = data.date;
            document.getElementById('easter-egg').textContent = getEasterEgg(displayDate);
            document.getElementById('today-in-history').innerHTML = `📜 历史上的今天：${getTodayInHistory(displayDate)}`;

            // 歌单入口
            if (data.songs && data.songs.length > 0) {
                document.getElementById('song-card').style.display = 'block';
                document.getElementById('songs-count').textContent = `今日歌单 · 共 ${data.songs.length} 首`;
                document.getElementById('songs-link').href = `/songs.html?date=${data.date}`;
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

            // 早报
            if (data.zaobao && data.zaobao.news && data.zaobao.news.length > 0) {
                document.getElementById('zaobao-card').style.display = 'block';
                if (data.zaobao.summary) {
                    document.getElementById('zaobao-summary').textContent = data.zaobao.summary;
                }
                const listContainer = document.getElementById('zaobao-list');
                listContainer.innerHTML = '';
                data.zaobao.news.forEach(item => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'zaobao-item';
                    itemDiv.innerHTML = `
                        <div>
                            <span class="zaobao-title">${item.title}</span>
                            <span class="zaobao-source">${item.source || ''}</span>
                        </div>
                        <div class="zaobao-summary-text">${item.summary || ''}</div>
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
        })
        .catch(err => {
            console.error(err);
            hideLoader();
            showError('数据加载失败，请稍后刷新');
        });
});

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
        // 清理可能残留的转义
        content = content.replace(/\\n/g, '\n');
        const paragraphs = content.split(/\n\s*\n/).filter(p => p.trim());
        const finalContent = paragraphs.join('\n\n');
        const wordCount = countWords(finalContent);
        const stats = formatStats(wordCount);

        const headerDiv = document.createElement('div');
        headerDiv.className = 'novel-header';
        headerDiv.innerHTML = `<div class="novel-title">${title}</div>`;
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
                <div class="novel-title" style="font-size:2rem; margin-bottom:1rem;">${title}</div>
                <div class="novel-content">${paragraphs.map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('')}</div>
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
        contentDiv.innerHTML = paragraphs.map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
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