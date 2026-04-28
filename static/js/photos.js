document.addEventListener('DOMContentLoaded', () => {
    fetch('/data/photos.json?t=' + Date.now())
        .then(res => res.json())
        .then(photos => {
            document.getElementById('loader').style.display = 'none';
            const grid = document.getElementById('photo-grid');
            grid.style.display = 'grid';
            if (!photos.length) {
                grid.innerHTML = '<p style="text-align:center; grid-column:1/-1;">暂无照片，请稍后...</p>';
                return;
            }
            photos.forEach((photo, idx) => {
                const item = document.createElement('div');
                item.className = 'photo-item';
                item.setAttribute('data-index', idx);
                const img = document.createElement('img');
                img.src = photo.image || photo.src;
                img.alt = photo.title || '摄影作品';
                img.loading = 'lazy';
                const titleSpan = document.createElement('div');
                titleSpan.className = 'photo-title';
                titleSpan.textContent = photo.title || '';
                item.appendChild(img);
                item.appendChild(titleSpan);
                item.addEventListener('click', () => openLightbox(photos, idx));
                grid.appendChild(item);
            });
        })
        .catch(err => {
            console.error(err);
            document.getElementById('loader').innerHTML = '<div class="error-message">❌ 照片加载失败，请刷新重试</div>';
        });
});

let currentPhotos = [];
let currentIndex = 0;

function openLightbox(photos, index) {
    currentPhotos = photos;
    currentIndex = index;
    const lightbox = document.getElementById('lightbox');
    const img = document.getElementById('lightbox-img');
    const captionTitle = document.querySelector('.caption-title');
    const captionAuthor = document.querySelector('.caption-author');
    const captionDate = document.querySelector('.caption-date');
    const captionDesc = document.querySelector('.caption-desc');
    const photo = photos[index];
    img.src = photo.image || photo.src;
    captionTitle.textContent = photo.title || '';
    captionAuthor.textContent = photo.author ? `摄影：${photo.author}` : '';
    captionDate.textContent = photo.date || '';
    captionDesc.textContent = photo.description || '';
    lightbox.style.display = 'flex';
}

function closeLightbox() {
    document.getElementById('lightbox').style.display = 'none';
}

function prevPhoto() {
    if (currentPhotos.length === 0) return;
    currentIndex = (currentIndex - 1 + currentPhotos.length) % currentPhotos.length;
    const photo = currentPhotos[currentIndex];
    const img = document.getElementById('lightbox-img');
    const captionTitle = document.querySelector('.caption-title');
    const captionAuthor = document.querySelector('.caption-author');
    const captionDate = document.querySelector('.caption-date');
    const captionDesc = document.querySelector('.caption-desc');
    img.src = photo.image || photo.src;
    captionTitle.textContent = photo.title || '';
    captionAuthor.textContent = photo.author ? `摄影：${photo.author}` : '';
    captionDate.textContent = photo.date || '';
    captionDesc.textContent = photo.description || '';
}

function nextPhoto() {
    if (currentPhotos.length === 0) return;
    currentIndex = (currentIndex + 1) % currentPhotos.length;
    const photo = currentPhotos[currentIndex];
    const img = document.getElementById('lightbox-img');
    const captionTitle = document.querySelector('.caption-title');
    const captionAuthor = document.querySelector('.caption-author');
    const captionDate = document.querySelector('.caption-date');
    const captionDesc = document.querySelector('.caption-desc');
    img.src = photo.image || photo.src;
    captionTitle.textContent = photo.title || '';
    captionAuthor.textContent = photo.author ? `摄影：${photo.author}` : '';
    captionDate.textContent = photo.date || '';
    captionDesc.textContent = photo.description || '';
}

document.addEventListener('click', (e) => {
    if (e.target.classList.contains('close-lightbox')) closeLightbox();
    if (e.target.classList.contains('prev')) prevPhoto();
    if (e.target.classList.contains('next')) nextPhoto();
});
document.addEventListener('keydown', (e) => {
    if (document.getElementById('lightbox').style.display === 'flex') {
        if (e.key === 'Escape') closeLightbox();
        if (e.key === 'ArrowLeft') prevPhoto();
        if (e.key === 'ArrowRight') nextPhoto();
    }
});
