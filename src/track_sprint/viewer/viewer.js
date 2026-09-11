export default function({parentElement, data, setStateValue, setTriggerValue}) {
  const root = parentElement.querySelector('.viewer');
  const range = root.querySelector('input');
  const canvas = root.querySelector('canvas');
  const loading = root.querySelector('.loading');
  const previous = root.querySelector('.previous');
  const next = root.querySelector('.next');
  const markControls = root.querySelector('.mark-controls');
  const touchdown = root.querySelector('.mark-touchdown');
  const toeoff = root.querySelector('.mark-toeoff');
  markControls.hidden = !data.allow_marking;
  root.classList.toggle('contact-review', Boolean(data.allow_marking));
  // Keep the decoded frame cache and local position through settled-selection reruns.
  let state = root.scrubberState;
  if (!state || state.identity !== data.analysis_id) {
    state = {identity:data.analysis_id, index:data.index, command:data.command,
      cache:new Map(), pending:new Map(), displayed:-1, lastSent:data.index};
    root.scrubberState = state;
  }
  if (state.command !== data.command) {
    state.index = data.index;
    state.lastSent = data.index;
    state.command = data.command;
  }
  const last = data.frames.length - 1;
  const events = new AbortController();
  let timer, animation, active = true;
  const cards = root.querySelector('.metric-list');
  cards.replaceChildren();
  const values = data.metrics.map(metric => {
    const card = document.createElement('div'); card.className = 'metric';
    const label = document.createElement('div'); label.className = 'metric-label'; label.textContent = metric.label;
    const value = document.createElement('div'); value.className = 'metric-value';
    card.append(label,value); cards.append(card); return value;
  });
  range.max = last;

  async function decode(index) {
    if (state.cache.has(index)) {
      const bitmap = state.cache.get(index);
      state.cache.delete(index); state.cache.set(index,bitmap); return bitmap;
    }
    if (state.pending.has(index)) return state.pending.get(index);
    const promise = (async () => {
      const bytes = Uint8Array.from(atob(data.images[index]), c => c.charCodeAt(0));
      const bitmap = await createImageBitmap(new Blob([bytes], {type:'image/jpeg'}));
      state.cache.set(index,bitmap);
      // Bounded decoded memory; all other frames remain compressed in the browser.
      while (state.cache.size > 24) {
        const oldest = state.cache.keys().next().value;
        if (oldest === state.index) {
          const current = state.cache.get(oldest); state.cache.delete(oldest); state.cache.set(oldest,current);
          continue;
        }
        state.cache.get(oldest).close(); state.cache.delete(oldest);
      }
      return bitmap;
    })();
    state.pending.set(index,promise);
    try {return await promise;} finally {state.pending.delete(index);}
  }

  async function paint() {
    const index = state.index;
    try {
      const bitmap = await decode(index);
      if (!active || index !== state.index) return;
      canvas.width = bitmap.width; canvas.height = bitmap.height;
      canvas.getContext('2d').drawImage(bitmap,0,0);
      state.displayed = index;
      canvas.setAttribute('aria-label', `Sprint ${data.view === 'original' ? 'original image' : 'pose overlay'}, source frame ${data.frames[index]}`);
      touchdown.disabled = index === 0 || index === last;
      toeoff.disabled = index === 0;
      root.querySelector('.frame-title').textContent = `Source frame ${data.frames[index]}`;
      root.querySelector('.timestamp').textContent = `Decoded media time ${data.times[index].toFixed(4)} s · model ${data.side} side`;
      data.metrics.forEach((metric,i) => {
        const value = metric.values[index];
        values[i].textContent = value == null ? 'Unavailable' : `${value.toFixed(1)}°`;
      });
      loading.hidden = true;
      for (const offset of [-2,-1,1,2]) {
        const neighbour = index + offset;
        if (neighbour >= 0 && neighbour <= last) decode(neighbour).catch(() => {});
      }
    } catch {
      if (active && index === state.index) {
        loading.textContent = 'This frame could not load. Try another frame.'; loading.hidden = false;
      }
    }
  }

  function show(index) {
    state.index = Math.max(0,Math.min(last,index));
    range.value = state.index;
    range.setAttribute('aria-valuetext', `Source frame ${data.frames[state.index]}, ${state.index + 1} of ${last + 1}`);
    root.querySelector('.counter').textContent = `${state.index + 1} / ${last + 1}`;
    previous.disabled = state.index === 0; next.disabled = state.index === last;
    touchdown.disabled = toeoff.disabled = true;
    clearTimeout(timer); cancelAnimationFrame(animation);
    animation = requestAnimationFrame(paint);
  }
  function settle() {
    clearTimeout(timer);
    timer = setTimeout(() => {
      if (state.index !== state.lastSent) {
        state.lastSent = state.index;
        setStateValue('index',state.index);
      }
    },300);
  }
  range.addEventListener('input', () => show(Number(range.value)), {signal:events.signal});
  range.addEventListener('change', settle, {signal:events.signal});
  range.addEventListener('keydown', event => {
    if (['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key)) {
      event.preventDefault();
      const delta = (['ArrowRight','ArrowUp'].includes(event.key) ? 1 : -1) * (event.shiftKey ? 10 : 1);
      show(event.key === 'Home' ? 0 : event.key === 'End' ? last : state.index + delta);
    }
  }, {signal:events.signal});
  range.addEventListener('keyup', settle, {signal:events.signal});
  previous.addEventListener('click', () => {show(state.index-1); settle();}, {signal:events.signal});
  next.addEventListener('click', () => {show(state.index+1); settle();}, {signal:events.signal});
  for (const [button,kind] of [[touchdown,'touchdown'],[toeoff,'toeoff']]) {
    button.addEventListener('click', () => {
      if (state.displayed !== state.index) return;
      clearTimeout(timer);
      setTriggerValue('boundary',{kind,index:state.index});
    }, {signal:events.signal});
  }
  show(state.index);
  return () => {active=false; clearTimeout(timer); cancelAnimationFrame(animation); events.abort();};
}
