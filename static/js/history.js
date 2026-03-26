document.addEventListener('DOMContentLoaded', () => {
    fetch('/data/history/index.json?t=' + Date.now())
        .then(res => res.json())
        .then(dates => {
            hideLoader();
            const timelineEl = document.getElementById('timeline');
            timelineEl.style.display = 'block';

            const grouped = {};
            dates.forEach(date => {
                const [year, month, day] = date.split('-');
                if (!grouped[year]) grouped[year] = {};
                if (!grouped[year][month]) grouped[year][month] = [];
                grouped[year][month].push({ day, fullDate: date });
            });

            for (const year of Object.keys(grouped).sort().reverse()) {
                const yearDiv = document.createElement('div');
                yearDiv.className = 'year-group';
                yearDiv.innerHTML = `<div class="year-title">${year} 年</div>`;
                for (const month of Object.keys(grouped[year]).sort().reverse()) {
                    const monthDiv = document.createElement('div');
                    monthDiv.className = 'month-group';
                    const daysCount = grouped[year][month].length;
                    monthDiv.innerHTML = `<div class="month-title">${month} 月 <span class="month-count">（共${daysCount}天）</span></div>`;
                    const dayList = document.createElement('div');
                    dayList.className = 'day-list';
                    grouped[year][month].sort((a,b) => parseInt(b.day) - parseInt(a.day)).forEach(item => {
                        const dayLink = document.createElement('a');
                        dayLink.className = 'day-card';
                        dayLink.href = `/detail.html?date=${item.fullDate}`;
                        dayLink.textContent = `${item.day} 日`;
                        dayList.appendChild(dayLink);
                    });
                    monthDiv.appendChild(dayList);
                    yearDiv.appendChild(monthDiv);
                }
                timelineEl.appendChild(yearDiv);
            }
        })
        .catch(err => {
            console.error(err);
            hideLoader();
            showError('历史数据加载失败，请稍后刷新');
        });
});