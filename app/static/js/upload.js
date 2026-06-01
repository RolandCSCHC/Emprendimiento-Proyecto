document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form.upload-form');
  if (!form) return;

  const progressEl = document.getElementById('upload-progress');
  const statusEl = document.getElementById('upload-status');
  const submitBtn = form.querySelector('button[type="submit"]');

  const allowedVideo = form.dataset.allowedVideo.split(',');
  const allowedAudio = form.dataset.allowedAudio.split(',');
  const createPendingUrl = form.dataset.createPendingUrl;
  const completeUrlTemplate = form.dataset.completeUrlTemplate;

  const ext = filename => filename.split('.').pop().toLowerCase();

  const showError = msg => {
    statusEl.textContent = msg;
    statusEl.style.color = 'var(--color-error, #c0392b)';
  };

  const resetUI = () => {
    submitBtn.disabled = false;
    progressEl.hidden = true;
    progressEl.value = 0;
  };

  const putToS3 = (presignedUrl, file, onProgress) =>
    new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('PUT', presignedUrl);
      xhr.upload.onprogress = onProgress;
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve();
        else reject(new Error(`Error al subir archivo (HTTP ${xhr.status})`));
      };
      xhr.onerror = () => reject(new Error('Error de red al subir el archivo.'));
      xhr.send(file);
    });

  form.addEventListener('submit', async e => {
    e.preventDefault();

    const nombre = form.nombre.value.trim();
    const fecha = form.fecha.value;
    const gimId = form.gimnasio_id.value;
    const profId = form.profesor_id.value;
    const tipoId = form.tipo_clase_id.value;
    const sala = form.sala ? form.sala.value.trim() : '';
    const nivel = form.nivel ? form.nivel.value.trim() : '';
    const videoFile = form.video.files[0] || null;
    const audioFile = form.audio.files[0] || null;

    if (!nombre) return showError('El nombre de la clase es obligatorio.');
    if (!fecha) return showError('La fecha y hora son obligatorias.');
    if (!gimId) return showError('Selecciona un gimnasio.');
    if (!profId) return showError('Selecciona un profesor.');
    if (!tipoId) return showError('Selecciona el tipo de clase.');
    if (!videoFile && !audioFile) return showError('Debes subir al menos un archivo de video o audio.');
    if (videoFile && !allowedVideo.includes(ext(videoFile.name))) {
      return showError(`Formato de video no permitido. Usa: ${allowedVideo.join(', ')}.`);
    }
    if (audioFile && !allowedAudio.includes(ext(audioFile.name))) {
      return showError(`Formato de audio no permitido. Usa: ${allowedAudio.join(', ')}.`);
    }

    submitBtn.disabled = true;
    progressEl.hidden = false;
    progressEl.value = 0;
    statusEl.textContent = 'Creando clase…';

    let pendingData;
    try {
      const res = await fetch(createPendingUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nombre,
          fecha,
          gimnasio_id: gimId,
          profesor_id: profId,
          tipo_clase_id: tipoId,
          sala,
          nivel,
          video_filename: videoFile ? videoFile.name : null,
          audio_filename: audioFile ? audioFile.name : null,
        }),
      });
      pendingData = await res.json();
      if (res.status !== 201) {
        showError(pendingData.error || 'Error al crear la clase.');
        resetUI();
        return;
      }
    } catch {
      showError('Error de conexión al crear la clase.');
      resetUI();
      return;
    }

    const { clase_id, uploads, redirect_url } = pendingData;

    const uploadEntries = [];
    if (uploads.video) uploadEntries.push({ tipo: 'video', info: uploads.video, file: videoFile });
    if (uploads.audio) uploadEntries.push({ tipo: 'audio', info: uploads.audio, file: audioFile });

    const fileSizes = uploadEntries.map(u => u.file.size);
    const totalBytes = fileSizes.reduce((a, b) => a + b, 0);
    const loadedByType = uploadEntries.map(() => 0);

    for (let i = 0; i < uploadEntries.length; i++) {
      const { tipo, info, file } = uploadEntries[i];
      statusEl.textContent = `Subiendo ${tipo}…`;
      try {
        await putToS3(info.presigned_url, file, ev => {
          if (!ev.lengthComputable) return;
          loadedByType[i] = ev.loaded;
          const totalLoaded = loadedByType.reduce((a, b) => a + b, 0);
          progressEl.value = Math.round((totalLoaded / totalBytes) * 100);
        });
      } catch (err) {
        showError(err.message);
        resetUI();
        return;
      }
    }

    progressEl.value = 100;
    statusEl.textContent = 'Finalizando…';

    try {
      const completeUrl = completeUrlTemplate.replace('CLASE_ID', clase_id);
      const res = await fetch(completeUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      const data = await res.json();
      if (res.status !== 200) {
        showError(data.error || 'Error al finalizar la subida.');
        resetUI();
        return;
      }
      window.location.href = data.redirect_url || redirect_url;
    } catch {
      showError('Error de conexión al finalizar la subida.');
      resetUI();
    }
  });
});
