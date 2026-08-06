"""Shared interactive-chart engine, vanilla JS, no dependencies. Reads
per-page data via calls left in each page's own inline <script> block."""

ENGINE_JS = r"""
(function(){
  var css = getComputedStyle(document.documentElement);
  function tok(name){ return css.getPropertyValue(name).trim(); }

  // ---------- scroll reveal ----------
  // Fades in only as each figure/section actually scrolls into view. Where
  // IntersectionObserver isn't available at all, reveal immediately rather
  // than leaving content permanently invisible -- but never on a timer,
  // which would fire the animation regardless of scroll position.
  //
  // Chart draw calls (BenchBar/BenchLine/etc, registered via registerChart)
  // are deferred the same way: a chart's grow/draw animation must play once
  // its figure is actually visible, not at page load while it's still
  // sitting at opacity:0 -- otherwise the animation finishes long before
  // anyone can see it and the figure just "pops in" fully drawn.
  var chartReady = {};
  window.registerChart = function(id, fn){
    var target = document.getElementById(id);
    if (target && target.classList.contains('in-view')){ fn(); return; }
    chartReady[id] = fn;
  };
  var revealEls = document.querySelectorAll('.reveal, .figure');
  if (window.IntersectionObserver){
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if (e.isIntersecting){
          e.target.classList.add('in-view');
          var fn = chartReady[e.target.id];
          if (fn){ fn(); delete chartReady[e.target.id]; }
        }
      });
    }, { threshold: 0.16 });
    revealEls.forEach(function(el){ io.observe(el); });
  } else {
    revealEls.forEach(function(el){ el.classList.add('in-view'); });
  }

  // ---------- count-up ----------
  function easeOutExpo(t){ return t === 1 ? 1 : 1 - Math.pow(2, -10 * t); }
  function countUp(el){
    var target = parseFloat(el.dataset.to);
    var start = parseFloat(el.dataset.from || '0');
    var decimals = parseInt(el.dataset.decimals || '0', 10);
    var prefix = el.dataset.prefix || '';
    var suffix = el.dataset.suffix || '';
    var dur = 1400;
    var t0 = null;
    function step(ts){
      if (!t0) t0 = ts;
      var p = Math.min(1, (ts - t0) / dur);
      var v = start + (target - start) * easeOutExpo(p);
      el.textContent = prefix + v.toLocaleString(undefined, {minimumFractionDigits: decimals, maximumFractionDigits: decimals}) + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  var countupEls = document.querySelectorAll('[data-countup]');
  if (window.IntersectionObserver){
    var cio = new IntersectionObserver(function(entries, obs){
      entries.forEach(function(e){
        if (e.isIntersecting && !e.target.dataset.counted){
          e.target.dataset.counted = '1'; countUp(e.target); obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.6 });
    countupEls.forEach(function(el){ cio.observe(el); });
  } else {
    countupEls.forEach(function(el){ countUp(el); });
  }

  // ---------- shared tooltip ----------
  var tip = document.createElement('div');
  tip.className = 'tooltip';
  document.body.appendChild(tip);
  function showTip(evt, html, wrap){
    tip.innerHTML = html;
    tip.classList.add('show');
    var r = wrap.getBoundingClientRect();
    var x = evt.clientX, y = r.top + window.scrollY - 10;
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
  }
  function hideTip(){ tip.classList.remove('show'); }

  var NS = 'http://www.w3.org/2000/svg';
  function el(tag, attrs){
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }

  // ---------- horizontal bar chart (one row per series x category) ----------
  // opts: { categories:[...], series:[{label,color,values:[num,...]}],
  //         yMax, barFmt(v), height }
  function benchBarHorizontal(host, opts){
    var W = 640, H = opts.height || 320;
    var padL = 108, padR = 16, padT = 10, padB = 30;
    var innerW = W - padL - padR, innerH = H - padT - padB;
    var n = opts.categories.length, s = opts.series.length;
    var groupH = innerH / n;
    var barH = Math.min(40, (groupH * 0.62) / s);
    var yMax = opts.yMax;

    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, preserveAspectRatio: 'xMidYMid meet' });
    host.appendChild(svg);

    var ticks = opts.yTicks || 4;
    for (var i = 0; i <= ticks; i++){
      var xv = yMax * i / ticks;
      var x = padL + (xv / yMax) * innerW;
      svg.appendChild(el('line', { x1: x, x2: x, y1: padT, y2: padT + innerH, class: 'grid-line' }));
      var lab = el('text', { x: x, y: padT + innerH + 18, class: 'axis-label', 'text-anchor': 'middle' });
      lab.textContent = opts.yFmt ? opts.yFmt(xv) : xv;
      svg.appendChild(lab);
    }

    opts.categories.forEach(function(cat, ci){
      var gy = padT + ci * groupH + groupH / 2;
      opts.series.forEach(function(s0, si){
        var v = s0.values[ci];
        var by = gy - (s * barH) / 2 + si * barH + barH * 0.08;
        var bh = barH * 0.84;
        var rowLab = el('text', { x: padL - 10, y: by + bh/2 + 3.5, class: 'axis-label', 'text-anchor': 'end' });
        rowLab.textContent = s0.label;
        svg.appendChild(rowLab);
        if (v === null || v === undefined) return;
        var bw = (v / yMax) * innerW;
        var rect = el('rect', { x: padL, y: by, width: 0, height: bh, fill: s0.color, rx: 3 });
        svg.appendChild(rect);
        requestAnimationFrame(function(){
          rect.style.transition = 'width .8s cubic-bezier(.16,1,.3,1)';
          rect.setAttribute('width', bw);
        });
        var lbl = el('text', { x: padL + bw + 8, y: by + bh/2 + 3.5, class: 'bar-label', 'text-anchor': 'start', opacity: 0 });
        lbl.textContent = opts.barFmt ? opts.barFmt(v) : v;
        svg.appendChild(lbl);
        setTimeout(function(l){ l.style.transition = 'opacity .4s'; l.setAttribute('opacity', 1); }, 500, lbl);

        rect.addEventListener('mousemove', function(e){
          showTip(e, '<span class="k">' + s0.label + '</span>&nbsp; <b>' + (opts.barFmt ? opts.barFmt(v) : v) + '</b>', host);
        });
        rect.addEventListener('mouseleave', hideTip);
        rect.style.cursor = 'pointer';
      });
    });
  }

  // ---------- grouped / annotated bar chart ----------
  // opts: { categories:[...], series:[{label,color,values:[num|null,...]}],
  //         yMax, yFmt(v), barFmt(v), unit, oomText, height, horizontal }
  window.BenchBar = function(containerId, opts){
    var host = document.getElementById(containerId);
    if (opts.horizontal){ benchBarHorizontal(host, opts); return; }
    var W = 640, H = opts.height || 320;
    var padL = 46, padR = 12, padT = 18, padB = 34;
    var innerW = W - padL - padR, innerH = H - padT - padB;
    var n = opts.categories.length, s = opts.series.length;
    var groupW = innerW / n;
    var barW = Math.min(34, (groupW * 0.66) / s);
    var yMax = opts.yMax;

    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, preserveAspectRatio: 'xMidYMid meet' });
    host.appendChild(svg);

    var ticks = opts.yTicks || 4;
    for (var i = 0; i <= ticks; i++){
      var yv = yMax * i / ticks;
      var y = padT + innerH - (yv / yMax) * innerH;
      svg.appendChild(el('line', { x1: padL, x2: W - padR, y1: y, y2: y, class: 'grid-line' }));
      var lab = el('text', { x: padL - 8, y: y + 3, class: 'axis-label', 'text-anchor': 'end' });
      lab.textContent = opts.yFmt ? opts.yFmt(yv) : yv;
      svg.appendChild(lab);
    }

    opts.categories.forEach(function(cat, ci){
      var gx = padL + ci * groupW + groupW / 2;
      var lab = el('text', { x: gx, y: H - 10, class: 'axis-label', 'text-anchor': 'middle' });
      lab.textContent = cat;
      svg.appendChild(lab);

      opts.series.forEach(function(s0, si){
        var v = s0.values[ci];
        var bx = gx - (s * barW) / 2 + si * barW + barW * 0.08;
        var bw = barW * 0.84;
        if (v === null || v === undefined){
          var by = padT + innerH - 4;
          var lx = bx + bw/2;
          // Vertical (reads bottom-to-top from the baseline) so the label's
          // footprint is just its font size wide, not its text length --
          // clears a sibling bar in the same group even on narrow, 3+
          // category charts.
          var txt = el('text', {
            x: lx, y: by, class: 'oom-label', 'text-anchor': 'start',
            transform: 'rotate(-90 ' + lx + ' ' + by + ')'
          });
          txt.textContent = opts.oomText || 'N/A';
          svg.appendChild(txt);
          return;
        }
        var bh = (v / yMax) * innerH;
        var rect = el('rect', {
          x: bx, y: padT + innerH, width: bw, height: 0,
          fill: s0.color, rx: 3
        });
        svg.appendChild(rect);
        requestAnimationFrame(function(){
          rect.style.transition = 'y .8s cubic-bezier(.16,1,.3,1), height .8s cubic-bezier(.16,1,.3,1)';
          rect.setAttribute('y', padT + innerH - bh);
          rect.setAttribute('height', bh);
        });
        var lbl = el('text', { x: bx + bw/2, y: padT + innerH - bh - 7, class: 'bar-label', opacity: 0 });
        lbl.textContent = opts.barFmt ? opts.barFmt(v) : v;
        svg.appendChild(lbl);
        setTimeout(function(l){ l.style.transition = 'opacity .4s'; l.setAttribute('opacity', 1); }, 500, lbl);

        rect.addEventListener('mousemove', function(e){
          showTip(e, '<span class="k">' + s0.label + '</span>&nbsp; <b>' + (opts.barFmt ? opts.barFmt(v) : v) + '</b>', host);
        });
        rect.addEventListener('mouseleave', hideTip);
        rect.style.cursor = 'pointer';
      });
    });
  };

  // ---------- line chart (animated draw) ----------
  // opts: { xLabels:[...], series:[{label,color,values:[num,...]}], yMax, yFmt, ptFmt, height }
  window.BenchLine = function(containerId, opts){
    var host = document.getElementById(containerId);
    var W = 640, H = opts.height || 320;
    var padL = 50, padR = 20, padT = 18, padB = 34;
    var innerW = W - padL - padR, innerH = H - padT - padB;
    var n = opts.xLabels.length;
    var yMax = opts.yMax, yMin = opts.yMin || 0;

    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, preserveAspectRatio: 'xMidYMid meet' });
    host.appendChild(svg);

    var ticks = opts.yTicks || 4;
    for (var i = 0; i <= ticks; i++){
      var yv = yMin + (yMax - yMin) * i / ticks;
      var y = padT + innerH - ((yv - yMin) / (yMax - yMin)) * innerH;
      svg.appendChild(el('line', { x1: padL, x2: W - padR, y1: y, y2: y, class: 'grid-line' }));
      var lab = el('text', { x: padL - 8, y: y + 3, class: 'axis-label', 'text-anchor': 'end' });
      lab.textContent = opts.yFmt ? opts.yFmt(yv) : yv;
      svg.appendChild(lab);
    }
    opts.xLabels.forEach(function(xl, xi){
      var x = padL + (xi / (n - 1)) * innerW;
      var lab = el('text', { x: x, y: H - 10, class: 'axis-label', 'text-anchor': 'middle' });
      lab.textContent = xl;
      svg.appendChild(lab);
    });

    function xy(xi, v){
      var x = padL + (xi / (n - 1)) * innerW;
      var y = padT + innerH - ((v - yMin) / (yMax - yMin)) * innerH;
      return [x, y];
    }

    opts.series.forEach(function(s0){
      var validIdx = [];
      var d = '';
      s0.values.forEach(function(v, i){
        if (v === null || v === undefined) return;
        var p = xy(i, v);
        d += (validIdx.length === 0 ? 'M' : 'L') + p[0].toFixed(2) + ' ' + p[1].toFixed(2) + ' ';
        validIdx.push(i);
      });
      var path = el('path', { d: d.trim(), fill: 'none', stroke: s0.color, 'stroke-width': 2.5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
      svg.appendChild(path);
      var len = path.getTotalLength();
      path.style.strokeDasharray = len;
      path.style.strokeDashoffset = len;
      requestAnimationFrame(function(){
        path.style.transition = 'stroke-dashoffset 1.1s cubic-bezier(.16,1,.3,1)';
        path.style.strokeDashoffset = 0;
      });
      validIdx.forEach(function(i){
        var p = xy(i, s0.values[i]);
        var dot = el('circle', { cx: p[0], cy: p[1], r: 4, fill: s0.color, stroke: tok('--bg-elev') || '#111', 'stroke-width': 2 });
        svg.appendChild(dot);
        dot.style.cursor = 'pointer';
        dot.addEventListener('mousemove', function(e){
          showTip(e, '<span class="k">' + s0.label + '</span>&nbsp; <b>' + (opts.ptFmt ? opts.ptFmt(s0.values[i]) : s0.values[i]) + '</b>', host);
        });
        dot.addEventListener('mouseleave', hideTip);
      });
      var lastGood = validIdx[validIdx.length - 1];
      if (lastGood !== undefined && lastGood < s0.values.length - 1){
        var lp = xy(lastGood, s0.values[lastGood]);
        var mx = lp[0] + 10, my = lp[1] - 4;
        var mark = el('text', {
          x: mx, y: my, class: 'oom-label', 'text-anchor': 'start',
          transform: 'rotate(-90 ' + mx + ' ' + my + ')'
        });
        mark.textContent = opts.oomText || 'OOM';
        svg.appendChild(mark);
      }
    });
  };

  // ---------- GPU trace: compute util + memory strips w/ looping scan-line ----------
  window.BenchTrace = function(containerId, opts){
    // opts: { util:[0..1,...], mem:[GiB,...], color, memMax, label }
    var host = document.getElementById(containerId);
    var W = 640, H = 168;
    var padL = 4, padR = 4;
    var uTop = 4, uH = 74, mTop = uTop + uH + 20, mH = 60;
    var innerW = W - padL - padR;
    var n = opts.util.length;
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, preserveAspectRatio: 'xMidYMid meet' });
    host.appendChild(svg);

    function path(vals, top, h, max){
      var pts = vals.map(function(v, i){
        var x = padL + (i / (n - 1)) * innerW;
        var y = top + h - (v / max) * h;
        return [x, y];
      });
      var line = pts.map(function(p,i){ return (i===0?'M':'L') + p[0].toFixed(2)+' '+p[1].toFixed(2); }).join(' ');
      var area = line + ' L ' + pts[pts.length-1][0].toFixed(2) + ' ' + (top+h) + ' L ' + pts[0][0].toFixed(2) + ' ' + (top+h) + ' Z';
      return { line: line, area: area };
    }

    [['util', opts.util, uTop, uH, 1], ['mem', opts.mem, mTop, mH, opts.memMax]].forEach(function(cfg){
      var vals = cfg[1], top = cfg[2], h = cfg[3], max = cfg[4];
      var p = path(vals, top, h, max);
      svg.appendChild(el('line', { x1: padL, x2: W-padR, y1: top+h, y2: top+h, class: 'grid-line' }));
      svg.appendChild(el('line', { x1: padL, x2: W-padR, y1: top, y2: top, class: 'grid-line' }));
      var fillId = containerId + '-' + cfg[0] + '-fill';
      var grad = el('linearGradient', { id: fillId, x1:0, y1:0, x2:0, y2:1 });
      grad.appendChild(el('stop', { offset:'0%', 'stop-color': opts.color, 'stop-opacity': 0.38 }));
      grad.appendChild(el('stop', { offset:'100%', 'stop-color': opts.color, 'stop-opacity': 0.02 }));
      var defs = el('defs', {}); defs.appendChild(grad); svg.appendChild(defs);
      var areaPath = el('path', { d: p.area, fill: 'url(#'+fillId+')' });
      svg.appendChild(areaPath);
      var linePath = el('path', { d: p.line, fill: 'none', stroke: opts.color, 'stroke-width': 2, 'stroke-linejoin':'round' });
      svg.appendChild(linePath);
      var len = linePath.getTotalLength();
      linePath.style.strokeDasharray = len; linePath.style.strokeDashoffset = len;
      areaPath.style.opacity = 0;
      requestAnimationFrame(function(){
        linePath.style.transition = 'stroke-dashoffset 1.3s cubic-bezier(.16,1,.3,1)';
        linePath.style.strokeDashoffset = 0;
        areaPath.style.transition = 'opacity 1s ease .3s';
        areaPath.style.opacity = 1;
      });
    });

    svg.appendChild((function(){ var t = el('text', { x: padL, y: uTop-8, class:'axis-label' }); t.textContent = 'compute util'; return t; })());
    svg.appendChild((function(){ var t = el('text', { x: padL, y: mTop-8, class:'axis-label' }); t.textContent = 'GPU memory'; return t; })());

    // looping scanner sweep
    var scan = el('rect', { x: 0, y: 0, width: 2, height: H, fill: opts.color, opacity: 0.55 });
    svg.appendChild(scan);
    scan.style.animation = 'benchscan 5.5s linear infinite';
  };

  var styleTag = document.createElement('style');
  styleTag.textContent = '@keyframes benchscan { 0%{ transform: translateX(4px); opacity:0; } 6%{opacity:.55;} 94%{opacity:.55;} 100%{ transform: translateX(636px); opacity:0; } }';
  document.head.appendChild(styleTag);
})();
"""
