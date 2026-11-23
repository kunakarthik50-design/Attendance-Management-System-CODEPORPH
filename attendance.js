// Interactive Attendance Marking Matrix Functionality
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('attendance-marking-form');
  if (!form) return;

  const countPresentEl = document.getElementById('count-present');
  const countAbsentEl = document.getElementById('count-absent');
  const countBypassEl = document.getElementById('count-bypass');
  const livePctEl = document.getElementById('live-percentage-val');
  const liveProgressBar = document.getElementById('live-progress-fill');

  // Status button selection
  document.querySelectorAll('.status-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const studentId = btn.dataset.studentId;
      const status = btn.dataset.status;
      
      const hiddenInput = document.getElementById(`status_input_${studentId}`);
      if (hiddenInput) {
        hiddenInput.value = status;
      }

      // Update active state in group
      const parentGroup = btn.closest('.status-toggle-group');
      parentGroup.querySelectorAll('.status-btn').forEach(b => {
        b.className = 'status-btn';
      });
      btn.classList.add(`selected-${status.toLowerCase()}`);

      recalculateLiveStats();
    });
  });

  // Bulk Marking Buttons
  const markAllPresentBtn = document.getElementById('btn-mark-all-present');
  const markAllAbsentBtn = document.getElementById('btn-mark-all-absent');

  if (markAllPresentBtn) {
    markAllPresentBtn.addEventListener('click', (e) => {
      e.preventDefault();
      applyBulkStatus('PRESENT');
    });
  }

  if (markAllAbsentBtn) {
    markAllAbsentBtn.addEventListener('click', (e) => {
      e.preventDefault();
      applyBulkStatus('ABSENT');
    });
  }

  function applyBulkStatus(status) {
    document.querySelectorAll('.student-row').forEach(row => {
      const studentId = row.dataset.studentId;
      const hiddenInput = document.getElementById(`status_input_${studentId}`);
      if (hiddenInput) hiddenInput.value = status;

      const targetBtn = row.querySelector(`.status-btn[data-status="${status}"]`);
      if (targetBtn) {
        row.querySelectorAll('.status-btn').forEach(b => b.className = 'status-btn');
        targetBtn.classList.add(`selected-${status.toLowerCase()}`);
      }
    });
    recalculateLiveStats();
  }

  function recalculateLiveStats() {
    const hiddenInputs = document.querySelectorAll('input[name^="status_"]');
    let present = 0, absent = 0, bypass = 0;

    hiddenInputs.forEach(input => {
      const val = input.value.toUpperCase();
      if (val === 'PRESENT') present++;
      else if (val === 'ABSENT') absent++;
      else if (val === 'BYPASS' || val === 'EXCUSED') bypass++;
    });

    const total = present + absent + bypass;
    if (countPresentEl) countPresentEl.textContent = present;
    if (countAbsentEl) countAbsentEl.textContent = absent;
    if (countBypassEl) countBypassEl.textContent = bypass;

    if (total > 0 && livePctEl && liveProgressBar) {
      const effectivePresent = present + bypass;
      const pct = Math.round((effectivePresent / total) * 100);
      livePctEl.textContent = `${pct}%`;
      liveProgressBar.style.width = `${pct}%`;

      if (pct >= 85) {
        liveProgressBar.className = 'progress-bar-fill progress-success';
      } else if (pct >= 75) {
        liveProgressBar.className = 'progress-bar-fill progress-warning';
      } else {
        liveProgressBar.className = 'progress-bar-fill progress-danger';
      }
    }
  }

  // Initial calculation
  recalculateLiveStats();
});
