document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('recomendaciones-container');
  if (!container) return;

  const profesorId = container.dataset.profesorId;
  const awsEnabled = container.dataset.awsEnabled === 'true';

  if (!awsEnabled || !profesorId) return;

  loadRecommendations(profesorId, container);
});

/**
 * Carga recomendaciones de la API y renderiza en el contenedor.
 * @param {string} profesorId - UUID del profesor
 * @param {HTMLElement} container - Elemento DOM donde renderizar
 */
async function loadRecommendations(profesorId, container) {
  container.innerHTML =
    '<div class="reco-loading"><span class="reco-spinner"></span>' +
    '<p class="text-muted">Generando recomendaciones con IA…</p></div>';

  try {
    const resp = await fetch(`/api/profesores/${profesorId}/recomendaciones`);
    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
      renderMessage(
        container,
        data.error || 'No se pudieron cargar las recomendaciones.'
      );
      return;
    }

    if (data.status === 'insufficient_data') {
      renderMessage(
        container,
        data.message ||
          'Se necesitan al menos 2 sesiones analizadas para generar recomendaciones.'
      );
      return;
    }

    if (!data.recommendations || data.recommendations.length === 0) {
      renderMessage(container, 'No hay recomendaciones disponibles por ahora.');
      return;
    }

    renderCards(container, data.recommendations);
  } catch (err) {
    renderMessage(container, 'No se pudieron cargar las recomendaciones.');
  }
}

function renderMessage(container, text) {
  const p = document.createElement('p');
  p.className = 'text-muted reco-message';
  p.textContent = text;
  container.replaceChildren(p);
}

function renderCards(container, recommendations) {
  const list = document.createElement('div');
  list.className = 'reco-grid';

  recommendations.forEach((rec, i) => {
    const card = document.createElement('article');
    card.className = 'reco-card';

    const num = document.createElement('span');
    num.className = 'reco-num';
    num.textContent = i + 1;

    const text = document.createElement('p');
    // Si la recomendación empieza con un título corto seguido de ":",
    // lo mostramos en negrita. Usamos nodos de texto (no innerHTML) por seguridad.
    const colonIdx = rec.indexOf(':');
    if (colonIdx > 0 && colonIdx <= 60) {
      const strong = document.createElement('strong');
      strong.textContent = rec.slice(0, colonIdx + 1);
      text.appendChild(strong);
      text.appendChild(document.createTextNode(rec.slice(colonIdx + 1)));
    } else {
      text.textContent = rec;
    }

    card.appendChild(num);
    card.appendChild(text);
    list.appendChild(card);
  });

  container.replaceChildren(list);
}
