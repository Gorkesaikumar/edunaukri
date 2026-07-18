/**

 * EduNaukri Job Seeker Dashboard — interactions

 */

(function () {

  "use strict";



  var CELEBRATION_DURATION_MS = 2600;

  var FADE_OUT_DURATION_MS = 550;



  document.addEventListener("DOMContentLoaded", function () {

    initCardHover();

    if (typeof window.initPortalDashboardHeader === "function") {
      window.initPortalDashboardHeader();
    }

    initProfileCompletionWorkflow();

    initLogoutConfirm();

    initRecommendationsRefresh();

    initDashboardLiveRefresh();

    initLiveJobRecommendations();

    initInsightsTicker();

  });



  function initCardHover() {

    document.querySelectorAll(".jsd-card--hover").forEach(function (card) {

      card.addEventListener("mouseenter", function () {

        card.style.transform = "translateY(-4px)";

      });

      card.addEventListener("mouseleave", function () {

        card.style.transform = "translateY(0)";

      });

    });

  }



  function getSearchInput() {

    return (

      document.getElementById("jsdSearchInput") ||

      document.querySelector(".jsd-mobile-search__form .jsd-header__search-input")

    );

  }



  function initSearchShortcut() {

    window.addEventListener("keydown", function (e) {

      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {

        e.preventDefault();

        var desktop = document.getElementById("jsdSearchInput");

        if (desktop && window.matchMedia("(min-width: 992px)").matches) {

          desktop.focus();

          return;

        }

        openMobileSearch();

      }

      if (e.key === "Escape") {

        closeMobileSearch();

      }

    });

  }



  function initMobileSearch() {

    var toggle = document.getElementById("jsdMobileSearchToggle");

    var panel = document.getElementById("jsdMobileSearch");

    var closeBtn = document.getElementById("jsdMobileSearchClose");

    if (!toggle || !panel) return;



    toggle.addEventListener("click", function () {

      if (panel.hidden) {

        openMobileSearch();

      } else {

        closeMobileSearch();

      }

    });



    if (closeBtn) {

      closeBtn.addEventListener("click", closeMobileSearch);

    }

  }



  function openMobileSearch() {

    var panel = document.getElementById("jsdMobileSearch");

    var toggle = document.getElementById("jsdMobileSearchToggle");

    if (!panel) return;

    panel.hidden = false;

    if (toggle) toggle.setAttribute("aria-expanded", "true");

    var input = panel.querySelector(".jsd-header__search-input");

    if (input) {

      window.setTimeout(function () {

        input.focus();

      }, 50);

    }

  }



  function closeMobileSearch() {

    var panel = document.getElementById("jsdMobileSearch");

    var toggle = document.getElementById("jsdMobileSearchToggle");

    if (!panel || panel.hidden) return;

    panel.hidden = true;

    if (toggle) {

      toggle.setAttribute("aria-expanded", "false");

      toggle.focus();

    }

  }



  function initNotificationForms() {

    document.querySelectorAll(".jsd-notif-mark-form").forEach(function (form) {

      form.addEventListener("submit", function (e) {

        if (!window.fetch) return;

        e.preventDefault();

        var fd = new FormData(form);

        fetch(form.action, {

          method: "POST",

          body: fd,

          headers: { "X-Requested-With": "XMLHttpRequest" },

          credentials: "same-origin",

        }).then(function (res) {

          if (res.ok) {

            var btn = form.querySelector(".jsd-notif-item");

            if (btn) btn.classList.remove("jsd-notif-item--unread");

          }

        });

      });

    });

  }



  function initProfileDropdownChevron() {

    var profileBtn = document.getElementById("jsdProfileDropdown");

    if (!profileBtn) return;

    profileBtn.addEventListener("hidden.bs.dropdown", function () {

      profileBtn.classList.remove("show");

    });

    profileBtn.addEventListener("shown.bs.dropdown", function () {

      profileBtn.classList.add("show");

    });

  }



  function initRecommendationsRefresh() {

    document.addEventListener("edu:recommendations-updated", function () {

      refreshDashboardData(true);
      refreshLiveJobRecommendations();

    });

  }

  function initLiveJobRecommendations() {
    var section = document.querySelector('[data-recommended-jobs-url]');
    if (!section) return;

    window.setInterval(function () {
      if (document.visibilityState === "visible") {
        refreshLiveJobRecommendations();
      }
    }, 15000);
  }

  function refreshLiveJobRecommendations() {
    var section = document.querySelector('[data-recommended-jobs-url]');
    if (!section) return;

    var url = section.getAttribute('data-recommended-jobs-url');
    if (!url) return;

    fetch(url, {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) { return res.json(); })
      .then(function (payload) {
        if (payload.success && payload.html) {
          var grid = document.getElementById("jsdRecommendedJobs");
          if (grid) {
            grid.innerHTML = payload.html;
          }
        }
      })
      .catch(function () {});
  }

  function initInsightsTicker() {

    var scroll = document.getElementById("jsdInsightsScroll");

    applyInsightsTickerAnimation(scroll);

  }



  function initDashboardLiveRefresh() {

    var statsRow = document.getElementById("jsdStatsRow");

    if (!statsRow) return;

    refreshDashboardData(true);

    window.setInterval(function () {

      if (document.visibilityState === "visible") {

        refreshDashboardData(true);

      }

    }, 60000);

  }



  function refreshDashboardData(forceRefresh) {

    var statsRow = document.getElementById("jsdStatsRow");

    var hero = document.getElementById("jsdHeroCard");

    var url = (statsRow && statsRow.getAttribute("data-insights-url"))

      || (hero && hero.getAttribute("data-insights-url"));

    if (!url) return;

    var fetchUrl = url + (forceRefresh ? "?live=1" : "");

    fetch(fetchUrl, {

      credentials: "same-origin",

      headers: { "X-Requested-With": "XMLHttpRequest" },

    })

      .then(function (res) {

        return res.json();

      })

      .then(function (payload) {

        if (!payload.success || !payload.data) return;

        if (payload.data.stats) {

          renderDashboardStats(payload.data.stats);

        }

        if (payload.data.kpis) {

          renderDashboardInsights(payload.data.kpis);

        }

        if (payload.data.hero && payload.data.hero.message) {

          var heroMsg = document.getElementById("jsdHeroMessage");

          if (heroMsg) heroMsg.textContent = payload.data.hero.message;

        }

      })

      .catch(function () {});

  }



  function renderDashboardStats(stats) {

    if (!stats || !stats.length) return;

    stats.forEach(function (stat) {

      var card = document.querySelector('.jsd-stat[data-stat-key="' + stat.key + '"]');

      if (!card) return;

      var valueEl = card.querySelector("[data-stat-value]");

      var subtitleEl = card.querySelector("[data-stat-subtitle]");

      var pctEl = card.querySelector("[data-stat-pct]");

      var trendEl = card.querySelector(".jsd-stat__trend");

      if (valueEl) valueEl.textContent = stat.value;

      if (subtitleEl) subtitleEl.textContent = stat.subtitle || "";

      if (pctEl) {

        if (stat.pct_badge) {

          pctEl.textContent = stat.pct_badge;

          pctEl.hidden = false;

        } else {

          pctEl.hidden = true;

        }

      } else if (stat.pct_badge) {

        var badge = document.createElement("span");

        badge.className = "jsd-stat__pct";

        badge.setAttribute("data-stat-pct", "");

        badge.textContent = stat.pct_badge;

        card.appendChild(badge);

      }

      if (trendEl) {

        trendEl.className = "jsd-stat__trend jsd-stat__trend--" + (stat.trend_tone || "muted");

        trendEl.innerHTML = (stat.trend_icon

          ? '<i class="bi ' + stat.trend_icon + '" aria-hidden="true"></i>'

          : "") + escapeHtml(stat.trend_label || "");

      }

    });

  }



  function buildInsightsTickerItems(insights) {

    return insights

      .map(function (item) {

        return '<li><span class="jsd-insights-ticker__dot" aria-hidden="true"></span>' + escapeHtml(item) + "</li>";

      })

      .join("");

  }



  function applyInsightsTickerAnimation(scrollEl) {

    if (!scrollEl) return;

    window.requestAnimationFrame(function () {

      var duration = Math.max(18, Math.min(40, scrollEl.scrollWidth / 40));

      scrollEl.style.animationDuration = duration + "s";

    });

  }



  function renderDashboardInsights(kpis) {

    var strip = document.getElementById("jsdInsightsStrip");

    if (!kpis || !kpis.activity_insights || !kpis.activity_insights.length) {

      if (strip) strip.hidden = true;

      return;

    }

    var itemsHtml = buildInsightsTickerItems(kpis.activity_insights);

    if (!strip) {

      var statsRow = document.getElementById("jsdStatsRow");

      if (!statsRow) return;

      strip = document.createElement("section");

      strip.className = "jsd-insights-ticker";

      strip.id = "jsdInsightsStrip";

      strip.setAttribute("aria-label", "Live career updates");

      strip.innerHTML =

        '<div class="jsd-insights-ticker__badge" aria-hidden="true">' +

        '<i class="bi bi-lightning-charge-fill"></i><span>Live</span></div>' +

        '<div class="jsd-insights-ticker__track">' +

        '<div class="jsd-insights-ticker__scroll" id="jsdInsightsScroll">' +

        '<ul class="jsd-insights-ticker__list" id="jsdInsightsList">' + itemsHtml + "</ul>" +

        '<ul class="jsd-insights-ticker__list jsd-insights-ticker__list--clone" aria-hidden="true">' + itemsHtml + "</ul>" +

        "</div></div>" +

        '<time class="jsd-insights-ticker__time" id="jsdInsightsUpdated" datetime=""></time>';

      statsRow.parentNode.insertBefore(strip, statsRow);

      applyInsightsTickerAnimation(document.getElementById("jsdInsightsScroll"));

    } else {

      strip.hidden = false;

      var scroll = document.getElementById("jsdInsightsScroll");

      if (scroll) {

        scroll.innerHTML =

          '<ul class="jsd-insights-ticker__list" id="jsdInsightsList">' + itemsHtml + "</ul>" +

          '<ul class="jsd-insights-ticker__list jsd-insights-ticker__list--clone" aria-hidden="true">' + itemsHtml + "</ul>";

        applyInsightsTickerAnimation(scroll);

      }

    }

    var updated = document.getElementById("jsdInsightsUpdated");

    if (updated && kpis.updated_at) {

      updated.textContent = kpis.updated_at;

      updated.hidden = false;

    }

  }






  function escapeHtml(value) {

    return String(value)

      .replace(/&/g, "&amp;")

      .replace(/</g, "&lt;")

      .replace(/>/g, "&gt;");

  }



  function escapeAttr(value) {

    return String(value).replace(/"/g, "&quot;");

  }



  function initLogoutConfirm() {

    document.querySelectorAll(".jsd-dropdown-item--danger[href]").forEach(function (link) {

      if (link.textContent.indexOf("Logout") === -1 && link.textContent.indexOf("Log out") === -1) return;

      link.addEventListener("click", function (e) {

        if (!window.EduNotify) return;

        e.preventDefault();

        var href = link.getAttribute("href");

        window.EduNotify.confirm({

          title: "Logout",

          message: "Are you sure you want to sign out of your EduNaukri account?",

          confirmText: "Logout",

          cancelText: "Stay signed in",

          variant: "warning",

          icon: "bi-box-arrow-right",

        }).then(function (ok) {

          if (ok && href) window.location.href = href;

        });

      });

    });

  }



  function initProfileCompletionWorkflow() {

    var hero = document.getElementById("jsdHeroCard");

    if (!hero) return;



    if (hero.getAttribute("data-play-celebration") === "true") {

      runProfileCompletionCelebration(hero);

      return;

    }



    initHeroProgressAnimation();

  }



  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.getAttribute("content")) {
      return meta.getAttribute("content");
    }
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input && input.value) {
      return input.value;
    }
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function initHeroProgressAnimation() {

    var bar = document.getElementById("jsdHeroProgressBar");

    var valueEl = document.getElementById("jsdHeroCompletion");

    if (!bar || !valueEl) return;



    var target = parseInt(valueEl.getAttribute("data-target") || "0", 10);

    bar.classList.add("jsd-progress__bar--animated");

    bar.style.width = "0%";



    window.requestAnimationFrame(function () {

      window.setTimeout(function () {

        bar.classList.remove("jsd-progress__bar--animated");

        bar.style.width = Math.min(100, Math.max(0, target)) + "%";

      }, 120);

    });

  }



  function runProfileCompletionCelebration(hero) {

    var message = hero.getAttribute("data-celebration-message") || "";

    var markUrl = hero.getAttribute("data-mark-animation-url") || "";

    var celebration = document.getElementById("jsdHeroCelebration");

    var messageEl = document.getElementById("jsdHeroCelebrationMessage");

    var bar = document.getElementById("jsdHeroProgressBar");

    var valueEl = document.getElementById("jsdHeroCompletion");



    if (bar) bar.style.width = "100%";

    if (valueEl) valueEl.textContent = "100%";



    if (celebration) {

      celebration.hidden = false;

      if (messageEl) messageEl.textContent = message;

    }



    hero.classList.add("jsd-hero--celebrating");

    startConfetti(document.getElementById("jsdHeroConfetti"), CELEBRATION_DURATION_MS);



    window.setTimeout(function () {

      markCelebrationShown(markUrl).finally(function () {

        fadeOutHeroCard(hero);

      });

    }, CELEBRATION_DURATION_MS);

  }



  function markCelebrationShown(url) {

    if (!url || !window.fetch) {

      return Promise.resolve();

    }

    return fetch(url, {

      method: "POST",

      headers: {

        "X-Requested-With": "XMLHttpRequest",

        "X-CSRFToken": getCsrfToken(),

      },

      credentials: "same-origin",

    }).catch(function () {

      /* Non-blocking — card still dismisses locally */

    });

  }



  function fadeOutHeroCard(hero) {

    var startHeight = hero.offsetHeight;

    hero.style.maxHeight = startHeight + "px";

    hero.classList.remove("jsd-hero--celebrating");

    hero.classList.add("jsd-hero--removing");



    window.requestAnimationFrame(function () {

      hero.classList.add("jsd-hero--removed");

    });



    window.setTimeout(function () {

      hero.remove();

    }, FADE_OUT_DURATION_MS + 50);

  }



  function startConfetti(canvas, durationMs) {

    if (!canvas || !canvas.getContext) return null;



    var ctx = canvas.getContext("2d");

    var rect = canvas.parentElement ? canvas.parentElement.getBoundingClientRect() : canvas.getBoundingClientRect();

    canvas.width = rect.width;

    canvas.height = rect.height;



    var colors = ["#6366f1", "#8b5cf6", "#22c55e", "#f59e0b", "#ec4899", "#0ea5e9"];

    var particles = [];

    var count = Math.min(120, Math.floor((canvas.width * canvas.height) / 4500));



    for (var i = 0; i < count; i++) {

      particles.push({

        x: canvas.width * 0.5 + (Math.random() - 0.5) * canvas.width * 0.35,

        y: canvas.height * 0.35,

        vx: (Math.random() - 0.5) * 8,

        vy: Math.random() * -8 - 3,

        size: Math.random() * 6 + 3,

        color: colors[Math.floor(Math.random() * colors.length)],

        rotation: Math.random() * 360,

        spin: (Math.random() - 0.5) * 12,

        life: 1,

      });

    }



    var start = performance.now();

    var rafId = 0;



    function frame(now) {

      var elapsed = now - start;

      var progress = Math.min(1, elapsed / durationMs);

      ctx.clearRect(0, 0, canvas.width, canvas.height);



      particles.forEach(function (p) {

        p.x += p.vx;

        p.y += p.vy;

        p.vy += 0.18;

        p.vx *= 0.99;

        p.rotation += p.spin;

        p.life = 1 - progress;



        if (p.life <= 0) return;



        ctx.save();

        ctx.globalAlpha = Math.max(0, p.life);

        ctx.translate(p.x, p.y);

        ctx.rotate((p.rotation * Math.PI) / 180);

        ctx.fillStyle = p.color;

        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.65);

        ctx.restore();

      });



      if (progress < 1) {

        rafId = requestAnimationFrame(frame);

      } else {

        ctx.clearRect(0, 0, canvas.width, canvas.height);

      }

    }



    rafId = requestAnimationFrame(frame);

    return rafId;

  }

})();


