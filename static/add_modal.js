// ====== 图片详情与预览 ======
function showImageDetail(imageId) {
  fetch(`${API_BASE}/api/v1/images/${imageId}`)
    .then(r => r.json())
    .then(d => {
      if (d.code === 0) {
        openImageModal(d.data);
      } else {
        toast('获取图片详情失败', 'error');
      }
    })
    .catch(e => {
      toast('请求失败: ' + e.message, 'error');
    });
}

function openImageModal(imageData) {
  const modal = document.getElementById('imageModal');
  const modalImg = document.getElementById('modalImage');
  const modalTitle = document.getElementById('modalTitle');
  const modalDesc = document.getElementById('modalDesc');
  const modalAuthor = document.getElementById('modalAuthor');
  const modalSize = document.getElementById('modalSize');
  const modalTags = document.getElementById('modalTags');
  
  modalImg.src = imageData.url || '';
  modalImg.onerror = function() {
    this.src = '';
    this.parentElement.innerHTML = '<div class="empty-state"><div class="icon">🖼️</div><p>图片加载失败</p></div>';
  };
  modalTitle.textContent = imageData.title || '无标题';
  modalDesc.textContent = imageData.description || '暂无描述';
  modalAuthor.innerHTML = '👤 ' + (imageData.author || '未知');
  modalSize.innerHTML = '📏 ' + (imageData.width || '?') + ' × ' + (imageData.height || '?');
  modalTags.innerHTML = (imageData.tags || []).map(t => '<span class="tag-chip tag-chip-green">' + t + '</span>').join('');
  
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  
  const handleEsc = (e) => {
    if (e.key === 'Escape') closeImageModal();
  };
  document.addEventListener('keydown', handleEsc);
  modal.dataset.escHandler = 'true';
}

function closeImageModal() {
  const modal = document.getElementById('imageModal');
  modal.style.display = 'none';
  document.body.style.overflow = '';
  
  if (modal.dataset.escHandler === 'true') {
    document.removeEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeImageModal();
    });
    modal.dataset.escHandler = 'false';
  }
}

document.getElementById('imageModal').addEventListener('click', (e) => {
  if (e.target.id === 'imageModal') closeImageModal();
});
