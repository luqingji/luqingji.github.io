document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const date = urlParams.get('date');
    let dataUrl = '/data/daily.json';
    let displayDate = null;

    if (date) {
        const [y, m, d] = date.split('-');
        dataUrl = `/data/history/${y}/${m}/${d}.json`;
        displayDate = date;
    }

    fetch(dataUrl + '?t=' + Date.now())
        .then(res => res.json())
        .then(data => {
            hideLoader();
            const container = document.getElementById('songs-container');
            container.style.display = 'block';

            let dateToShow = displayDate;
            if (!dateToShow && data.date) dateToShow = data.date;
            if (dateToShow) {
                const [year, month, day] = dateToShow.split('-');
                document.getElementById('song-date').textContent = `${year}年${parseInt(month)}月${parseInt(day)}日`;
            } else {
                document.getElementById('song-date').style.display = 'none';
            }

            let songs = data.songs;
            if (!songs && data.song) songs = [data.song];
            if (!songs || songs.length === 0) {
                container.innerHTML = '<p>暂无歌单数据</p>';
                return;
            }
            songs.forEach(song => {
                const card = document.createElement('div');
                card.className = 'song-card';
                card.innerHTML = `
                    <h3>${song.name}</h3>
                    <div class="artist">${song.artist}</div>
                    <div class="album">${song.album || '未知专辑'}</div>
                    <div class="recommendation">${song.recommendation || '暂无推荐语'}</div>
                `;
                container.appendChild(card);
            });
        })
        .catch(err => {
            console.error(err);
            hideLoader();
            showError('加载失败');
        });
});