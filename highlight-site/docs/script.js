(function () {
  var $ = function (id) { return document.getElementById(id); };

  // Server ka link (config.js se). Khaali ho to usi jagah se baat karta hai jahan se site khuli hai.
  var API = String(window.API_URL || '').replace(/\/+$/, '');
  var onPages = /\.github\.io$/i.test(location.hostname);

  var form = $('form');
  var go = $('go');
  var errBox = $('err');
  var progress = $('progress');
  var msg = $('msg');
  var result = $('result');
  var timer = null;
  var failures = 0;

  // GitHub Pages par repository ka Actions link dikhao
  if (onPages) {
    var user = location.hostname.split('.')[0];
    var repo = location.pathname.split('/')[1];
    if (user && repo) {
      $('actions-link').href = 'https://github.com/' + user + '/' + repo + '/actions/workflows/clip.yml';
      $('actions-tip').hidden = false;
    }
  }

  function showError(text) {
    errBox.textContent = text;
  }

  function setBusy(busy) {
    go.disabled = busy;
    go.textContent = busy ? 'Clip ban rahi hai...' : 'Clip banao';
    progress.hidden = !busy;
  }

  function stopPolling() {
    if (timer) { clearInterval(timer); timer = null; }
  }

  function fileUrl(path) {
    return /^https?:/i.test(path) ? path : API + path;
  }

  function showResult(d) {
    $('note').textContent = d.note || '';
    $('player').src = fileUrl(d.video);

    var dv = $('dl-video');
    dv.href = fileUrl(d.video);
    if (API) { dv.target = '_blank'; dv.rel = 'noopener'; }

    var srt = $('dl-srt');
    if (d.srt) {
      srt.href = fileUrl(d.srt);
      if (API) { srt.target = '_blank'; srt.rel = 'noopener'; }
      srt.hidden = false;
    } else {
      srt.hidden = true;
    }
    result.hidden = false;
    result.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function poll(jobId) {
    failures = 0;
    timer = setInterval(function () {
      fetch(API + '/api/job/' + encodeURIComponent(jobId))
        .then(function (r) {
          return r.json().then(function (d) { return { ok: r.ok, status: r.status, d: d }; });
        })
        .then(function (res) {
          failures = 0;
          if (!res.ok) {
            var e = new Error(res.d.error || 'Kaam nahi mila.');
            e.fatal = res.status === 404;
            throw e;
          }
          var d = res.d;
          msg.textContent = d.message || '';
          if (d.status === 'done') {
            stopPolling();
            setBusy(false);
            showResult(d);
          } else if (d.status === 'error') {
            stopPolling();
            setBusy(false);
            showError(d.message || 'Kuch gadbad ho gayi.');
          }
        })
        .catch(function (e) {
          failures += 1;
          if (failures >= 5 || e.fatal) {
            stopPolling();
            setBusy(false);
            showError(e.message || 'Server se connection toot gaya.');
          }
        });
    }, 2000);
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    showError('');
    result.hidden = true;
    stopPolling();

    var body = {
      url: $('url').value.trim(),
      len: Number($('len').value) || 45,
      vertical: $('vertical').checked,
      captions: $('captions').checked
    };

    if (!body.url) {
      showError('Pehle video ka link daalo.');
      return;
    }

    if (onPages && !API) {
      showError('Ye page GitHub Pages par hai, jahan video process nahi ho sakta. ' +
                'docs/config.js me apne server ka link daalo, ya neeche wale GitHub Actions se clip banao.');
      return;
    }

    setBusy(true);
    msg.textContent = 'Kaam shuru ho raha hai...';

    fetch(API + '/api/clip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
      .then(function (r) {
        return r.json().then(function (d) { return { ok: r.ok, d: d }; });
      })
      .then(function (res) {
        if (!res.ok) {
          throw new Error(res.d.error || 'Kuch gadbad ho gayi.');
        }
        poll(res.d.job_id);
      })
      .catch(function (err) {
        setBusy(false);
        showError(err.message || 'Server se connect nahi ho paya.');
      });
  });
})();
