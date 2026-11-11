/* Preserve the comparison when moving between the three views of the atlas. */
'use strict';

window.CeresRegions = {
  read(manifest) {
    const params = new URLSearchParams(window.location.search);
    const requestedMode = params.get('mode');
    const mode = Object.hasOwn(manifest.modes, requestedMode) ? requestedMode : 'rolling';
    const frames = manifest.modes[mode].frames;
    const frame = Number(params.get('frame'));
    const index = Number.isInteger(frame) && frame >= 0 && frame < frames.length ? frame : 0;
    const selected = ['asr', 'net', 'temperature'].map((fallback, panel) => {
      const field = params.get('field' + panel);
      return panel < 2 && field !== 'temperature' && Object.hasOwn(manifest.fields, field)
        ? field
        : fallback;
    });

    const scales = selected.map((field, panel) => {
      const info = manifest.fields[field];
      const input = params.get('scale' + panel);
      if (input === 'auto') return { [field]: { limit: info.default, auto: true } };
      if (input === null) return {};
      const limit = Number(input);
      if (!Number.isFinite(limit) || limit < info.minimum || limit > info.maximum) return {};
      const steps = Math.round((limit - info.minimum) / info.step);
      const snapped = Number((info.minimum + steps * info.step).toFixed(6));
      return { [field]: { limit: snapped, auto: false } };
    });

    return { mode, index, selected, scales, lockScale: params.get('lockScale') === '1' };
  },

  connect(state, manifest) {
    const toggle = document.getElementById('lock-region-scales');
    if (toggle) {
      toggle.checked = state.lockScale;
      toggle.addEventListener('change', () => { state.lockScale = toggle.checked; });
    }
    for (const link of document.querySelectorAll('[data-region]')) {
      link.addEventListener('click', (event) => {
        if (link.getAttribute('aria-current') === 'page' &&
            !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
          event.preventDefault();
          return;
        }
        const destination = new URL(link.href);
        destination.searchParams.set('mode', state.mode);
        destination.searchParams.set('frame', String(state.index));
        destination.searchParams.set('lockScale', state.lockScale ? '1' : '0');
        state.selected.forEach((field, panel) => {
          if (panel < 2) destination.searchParams.set('field' + panel, field);
          const scale = state.scales[panel][field];
          if (scale) {
            const limit = scale.auto && state.lockScale
              ? manifest.modes[state.mode].fields[field].auto_limit
              : scale.limit;
            destination.searchParams.set('scale' + panel,
              scale.auto && !state.lockScale ? 'auto' : String(limit));
          }
        });
        link.href = destination.href;
      });
    }
  },
};

