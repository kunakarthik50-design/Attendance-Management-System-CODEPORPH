// Interactive Charts with Chart.js
function isDarkTheme() {
  return document.documentElement.getAttribute('data-theme') === 'dark';
}

function getChartColors() {
  const dark = isDarkTheme();
  return {
    textColor: dark ? '#94a3b8' : '#64748b',
    gridColor: dark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.05)',
    primary: '#6366f1',
    primaryAlpha: dark ? 'rgba(99, 102, 241, 0.2)' : 'rgba(79, 70, 229, 0.12)',
    success: '#10b981',
    danger: '#f43f5e',
    warning: '#f59e0b'
  };
}

let trendsChartInstance = null;
let subjectsChartInstance = null;

async function initTrendsChart() {
  const canvas = document.getElementById('attendanceTrendsChart');
  if (!canvas) return;

  try {
    const res = await fetch('/api/charts/trends');
    const data = await res.json();
    const colors = getChartColors();

    const ctx = canvas.getContext('2d');
    if (trendsChartInstance) trendsChartInstance.destroy();

    trendsChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Daily Attendance %',
          data: data.data,
          borderColor: colors.primary,
          backgroundColor: colors.primaryAlpha,
          borderWidth: 3,
          fill: true,
          tension: 0.35,
          pointBackgroundColor: colors.primary,
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => ` Attendance: ${ctx.parsed.y !== null ? ctx.parsed.y + '%' : 'No Sessions'}`
            }
          }
        },
        scales: {
          x: {
            grid: { color: colors.gridColor },
            ticks: { color: colors.textColor, font: { family: 'Plus Jakarta Sans', size: 11 } }
          },
          y: {
            min: 40,
            max: 100,
            grid: { color: colors.gridColor },
            ticks: {
              color: colors.textColor,
              font: { family: 'Plus Jakarta Sans', size: 11 },
              callback: (val) => val + '%'
            }
          }
        }
      }
    });
  } catch (err) {
    console.error('Error loading trends chart:', err);
  }
}

async function initSubjectsChart() {
  const canvas = document.getElementById('subjectPerformanceChart');
  if (!canvas) return;

  try {
    const res = await fetch('/api/charts/subjects');
    const data = await res.json();
    const colors = getChartColors();

    const labels = data.map(d => d.code);
    const percentages = data.map(d => d.percentage);
    const bgColors = percentages.map(p => p >= 75 ? colors.success : colors.danger);

    const ctx = canvas.getContext('2d');
    if (subjectsChartInstance) subjectsChartInstance.destroy();

    subjectsChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Average Attendance %',
          data: percentages,
          backgroundColor: bgColors,
          borderRadius: 6,
          barThickness: 24
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => {
                const idx = items[0].dataIndex;
                return `${data[idx].code}: ${data[idx].name}`;
              },
              label: (ctx) => ` Overall: ${ctx.parsed.y}% (${data[ctx.dataIndex].sessions_count} sessions)`
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: colors.textColor, font: { family: 'Plus Jakarta Sans', size: 11 } }
          },
          y: {
            min: 0,
            max: 100,
            grid: { color: colors.gridColor },
            ticks: {
              color: colors.textColor,
              font: { family: 'Plus Jakarta Sans', size: 11 },
              callback: (val) => val + '%'
            }
          }
        }
      }
    });
  } catch (err) {
    console.error('Error loading subject chart:', err);
  }
}

window.renderCharts = function() {
  initTrendsChart();
  initSubjectsChart();
};

document.addEventListener('DOMContentLoaded', () => {
  window.renderCharts();
});
