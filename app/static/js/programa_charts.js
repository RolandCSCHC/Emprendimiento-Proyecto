document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('programa-charts');
  if (!container || typeof Chart === 'undefined') return;

  const series = JSON.parse(container.dataset.chartSeries || '{}');
  const labels = JSON.parse(container.dataset.metricLabels || '{}');

  const CHART_CONFIG = {
    asistencia: {
      type: 'bar',
      yMin: 0,
      yMax: null,
      yTickFormat: v => Math.round(v),
      formatValue: v => `${Math.round(v)} personas`,
    },
    permanencia: {
      type: 'line',
      yMin: 0,
      yMax: 100,
      yTickFormat: v => `${v}%`,
      formatValue: v => `${v.toFixed(1)}%`,
    },
    claridad_instrucciones: {
      type: 'line',
      yMin: 0,
      yMax: 100,
      yTickFormat: v => v,
      formatValue: v => `${v.toFixed(1)} score`,
    },
    tiempo_hablando_vs_demostrando: {
      type: 'line',
      yMin: 0,
      yMax: 100,
      yTickFormat: v => `${v}%`,
      formatValue: v => `${v.toFixed(1)}%`,
    },
    satisfaccion_alumno: {
      type: 'line',
      yMin: 0,
      yMax: 100,
      yTickFormat: v => v,
      formatValue: v => `${v.toFixed(0)} score`,
    },
  };

  const accent = getComputedStyle(document.documentElement)
    .getPropertyValue('--accent')
    .trim() || '#2563eb';
  const border = getComputedStyle(document.documentElement)
    .getPropertyValue('--border')
    .trim() || '#e2e8f0';
  const textMuted = getComputedStyle(document.documentElement)
    .getPropertyValue('--text-muted')
    .trim() || '#64748b';

  container.querySelectorAll('canvas[data-metric-key]').forEach(canvas => {
    const key = canvas.dataset.metricKey;
    const points = series[key] || [];
    const config = CHART_CONFIG[key] || {
      type: 'line',
      yMin: 0,
      yMax: 100,
      yTickFormat: v => v,
      formatValue: v => String(v),
    };
    const title = labels[key] || key;

    if (points.length === 0) {
      const wrapper = canvas.closest('.chart-container');
      if (wrapper) {
        wrapper.innerHTML = '<p class="text-muted chart-no-data">Sin datos</p>';
      }
      return;
    }

    const xLabels = points.map(p => p.fecha);
    const values = points.map(p => p.valor);

    new Chart(canvas, {
      type: config.type,
      data: {
        labels: xLabels,
        datasets: [{
          label: title,
          data: values,
          backgroundColor: config.type === 'bar' ? accent : `${accent}33`,
          borderColor: accent,
          borderWidth: 2,
          fill: config.type === 'line',
          tension: 0.25,
          pointRadius: 4,
          pointHoverRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => config.formatValue(ctx.parsed.y),
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: textMuted, maxRotation: 45, minRotation: 0 },
          },
          y: {
            min: config.yMin,
            max: config.yMax ?? undefined,
            grid: { color: border },
            ticks: {
              color: textMuted,
              callback: value => config.yTickFormat(value),
            },
          },
        },
      },
    });
  });
});
