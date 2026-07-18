/* ==========================================================================
   EduNaukri — Landing Page Interactions
   Vanilla JavaScript. No inline handlers.
   ========================================================================== */
(function () {
  "use strict";

  /* ------------------------------------------------------------------
     1. "Your Path to Excellence" interactive timeline
     ------------------------------------------------------------------ */
  function initTimeline() {
    var steps = Array.prototype.slice.call(document.querySelectorAll(".ed-step"));
    var progress = document.getElementById("timelineProgress");
    if (!steps.length) return;

    function setActive(percentage) {
      if (progress) {
        progress.style.width = percentage + "%";
      }
      steps.forEach(function (step) {
        var value = parseInt(step.getAttribute("data-step"), 10);
        var isActive = value <= percentage;
        step.classList.toggle("is-active", isActive);
        if (value === percentage) {
          step.setAttribute("aria-current", "step");
        } else {
          step.removeAttribute("aria-current");
        }
      });
    }

    steps.forEach(function (step) {
      var value = parseInt(step.getAttribute("data-step"), 10);
      step.addEventListener("click", function () {
        setActive(value);
      });
      step.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          setActive(value);
        }
      });
      step.setAttribute("tabindex", "0");
      step.setAttribute("role", "button");
    });
  }

  /* ------------------------------------------------------------------
     2. Success Stories — infinite auto-scroll testimonial carousel
        Transform-based marquee with pause-on-hover, drag/swipe,
        horizontal wheel, prev/next, pagination dots, and live filters.
     ------------------------------------------------------------------ */
  function initStoriesCarousel() {
    var viewport = document.querySelector("[data-stories]");
    var track = document.querySelector("[data-stories-track]");
    if (!viewport || !track) return;

    var dotsWrap = document.querySelector("[data-stories-dots]");
    var noResults = document.querySelector("[data-stories-noresults]");
    var prevBtn = document.querySelector("[data-stories-prev]");
    var nextBtn = document.querySelector("[data-stories-next]");
    var chips = Array.prototype.slice.call(
      document.querySelectorAll("[data-story-filter]")
    );
    var reduceMotion =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Master list of source items (detached templates + metadata).
    var templates = Array.prototype.slice.call(track.children).map(function (node) {
      var card = node.querySelector("[data-domain]");
      return {
        node: node.cloneNode(true),
        domain: card ? card.getAttribute("data-domain") : "",
        salary: card ? parseInt(card.getAttribute("data-salary"), 10) || 0 : 0,
      };
    });

    var SPEED = 40; // px per second — slow, premium drift
    var offset = 0;
    var seqWidth = 0;
    var stride = 0;
    var perView = 1;
    var seqCount = 0;
    var playing = !reduceMotion;
    var scrollable = false;
    var activePage = -1;
    var lastTs = 0;
    var currentFilter = "all";
    var currentSort = "recent";

    function gap() {
      var style = window.getComputedStyle(track);
      return parseFloat(style.columnGap || style.gap || "0") || 0;
    }

    function measure() {
      var first = track.querySelector(".ed-stories__item");
      if (!first || seqCount === 0) {
        stride = 0;
        seqWidth = 0;
        return;
      }
      var g = gap();
      var itemWidth = first.getBoundingClientRect().width;
      stride = itemWidth + g;
      seqWidth = stride * seqCount;
      perView = Math.max(1, Math.round((viewport.clientWidth + g) / stride));
      scrollable = seqWidth > viewport.clientWidth + 1;
    }

    function apply() {
      track.style.transform = "translateX(" + -offset + "px)";
    }

    function wrap() {
      if (seqWidth <= 0) return;
      while (offset >= seqWidth) offset -= seqWidth;
      while (offset < 0) offset += seqWidth;
    }

    function buildDots() {
      if (!dotsWrap) return;
      dotsWrap.innerHTML = "";
      if (!scrollable || seqCount === 0) return;
      var pages = Math.max(1, Math.ceil(seqCount / perView));
      for (var i = 0; i < pages; i++) {
        var dot = document.createElement("button");
        dot.type = "button";
        dot.className = "ed-stories__dot";
        dot.setAttribute("role", "tab");
        dot.setAttribute("aria-label", "Go to slide group " + (i + 1));
        (function (page) {
          dot.addEventListener("click", function () {
            tweenTo(page * perView * stride);
          });
        })(i);
        dotsWrap.appendChild(dot);
      }
      activePage = -1;
      updateDots();
    }

    function updateDots() {
      if (!dotsWrap || !scrollable || stride === 0) return;
      var index = Math.round(offset / stride) % seqCount;
      if (index < 0) index += seqCount;
      var page = Math.floor(index / perView);
      if (page === activePage) return;
      activePage = page;
      var dots = dotsWrap.children;
      for (var i = 0; i < dots.length; i++) {
        dots[i].classList.toggle("is-active", i === page);
      }
    }

    function build() {
      var filtered = templates.filter(function (t) {
        return currentFilter === "all" || t.domain === currentFilter;
      });
      if (currentSort === "salary") {
        filtered = filtered.slice().sort(function (a, b) {
          return b.salary - a.salary;
        });
      }

      track.innerHTML = "";
      seqCount = filtered.length;

      if (seqCount === 0) {
        if (noResults) noResults.classList.remove("d-none");
        viewport.style.display = "none";
        if (dotsWrap) dotsWrap.innerHTML = "";
        toggleNav(false);
        return;
      }
      if (noResults) noResults.classList.add("d-none");
      viewport.style.display = "";

      var frag = document.createDocumentFragment();
      // Two identical passes → seamless infinite loop.
      for (var pass = 0; pass < 2; pass++) {
        filtered.forEach(function (t) {
          frag.appendChild(t.node.cloneNode(true));
        });
      }
      track.appendChild(frag);

      offset = 0;
      measure();
      apply();
      buildDots();
      toggleNav(scrollable);
      playing = !reduceMotion && scrollable;
    }

    function toggleNav(enabled) {
      [prevBtn, nextBtn].forEach(function (btn) {
        if (btn) btn.disabled = !enabled;
      });
    }

    // Eased manual movement for buttons / dots.
    var tweening = false;
    function tweenTo(target) {
      if (!scrollable) return;
      var start = offset;
      var delta = target - start;
      var duration = 450;
      var startTime = null;
      tweening = true;
      function frame(ts) {
        if (!startTime) startTime = ts;
        var p = Math.min((ts - startTime) / duration, 1);
        var eased = 1 - Math.pow(1 - p, 3);
        offset = start + delta * eased;
        wrap();
        apply();
        updateDots();
        if (p < 1) {
          requestAnimationFrame(frame);
        } else {
          tweening = false;
        }
      }
      requestAnimationFrame(frame);
    }

    // Continuous auto-scroll loop.
    function loop(ts) {
      var dt = lastTs ? (ts - lastTs) / 1000 : 0;
      lastTs = ts;
      if (playing && !tweening && scrollable) {
        offset += SPEED * dt;
        wrap();
        apply();
        updateDots();
      }
      requestAnimationFrame(loop);
    }

    // Pause on hover / focus.
    viewport.addEventListener("mouseenter", function () {
      playing = false;
    });
    viewport.addEventListener("mouseleave", function () {
      if (!dragging) playing = !reduceMotion && scrollable;
    });
    viewport.addEventListener("focusin", function () {
      playing = false;
    });
    viewport.addEventListener("focusout", function () {
      if (!viewport.contains(document.activeElement)) {
        playing = !reduceMotion && scrollable;
      }
    });

    // Prev / Next.
    if (prevBtn) {
      prevBtn.addEventListener("click", function () {
        tweenTo(offset - perView * stride);
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        tweenTo(offset + perView * stride);
      });
    }

    // Horizontal wheel / trackpad (won't hijack vertical page scroll).
    viewport.addEventListener(
      "wheel",
      function (event) {
        if (!scrollable) return;
        if (Math.abs(event.deltaX) <= Math.abs(event.deltaY)) return;
        event.preventDefault();
        offset += event.deltaX;
        wrap();
        apply();
        updateDots();
      },
      { passive: false }
    );

    // Drag / swipe.
    var dragging = false;
    var dragStartX = 0;
    var dragStartOffset = 0;
    var dragMoved = false;

    track.addEventListener("pointerdown", function (event) {
      if (!scrollable) return;
      if (event.pointerType === "mouse" && event.button !== 0) return;
      dragging = true;
      dragMoved = false;
      dragStartX = event.clientX;
      dragStartOffset = offset;
      playing = false;
      track.classList.add("is-dragging");
    });
    window.addEventListener("pointermove", function (event) {
      if (!dragging) return;
      var dx = event.clientX - dragStartX;
      if (Math.abs(dx) > 4) dragMoved = true;
      offset = dragStartOffset - dx;
      wrap();
      apply();
      updateDots();
    });
    function endDrag() {
      if (!dragging) return;
      dragging = false;
      track.classList.remove("is-dragging");
      if (!viewport.matches(":hover")) playing = !reduceMotion && scrollable;
    }
    window.addEventListener("pointerup", endDrag);
    window.addEventListener("pointercancel", endDrag);

    // Suppress click right after a drag.
    track.addEventListener(
      "click",
      function (event) {
        if (dragMoved) {
          event.preventDefault();
          event.stopPropagation();
          dragMoved = false;
        }
      },
      true
    );

    // "Read More" via delegation (survives rebuilds).
    track.addEventListener("click", function (event) {
      var btn = event.target.closest("[data-story-more]");
      if (!btn) return;
      var card = btn.closest(".ed-story-card");
      if (!card) return;
      var quote = card.querySelector("[data-story-quote]");
      if (!quote) return;
      var expanded = quote.classList.toggle("is-clamped") === false;
      btn.textContent = expanded ? "Read Less" : "Read More";
      btn.setAttribute("aria-expanded", expanded ? "true" : "false");
    });

    // Filters.
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        currentFilter = chip.getAttribute("data-story-filter") || "all";
        currentSort = chip.getAttribute("data-story-sort") || "recent";
        chips.forEach(function (c) {
          var isActive = c === chip;
          c.classList.toggle("is-active", isActive);
          c.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
        build();
      });
    });

    var resizeTimer;
    window.addEventListener("resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        measure();
        wrap();
        apply();
        buildDots();
        toggleNav(scrollable);
        if (!reduceMotion) playing = scrollable && !viewport.matches(":hover");
      }, 150);
    });

    build();
    requestAnimationFrame(loop);
  }

  /* ------------------------------------------------------------------
     2a. Live Hiring Activity — auto-refreshing social-proof feed
     ------------------------------------------------------------------ */
  function initActivityFeed() {
    var feed = document.querySelector("[data-activity-feed]");
    if (!feed) return;

    var url = feed.getAttribute("data-activity-url");
    var counter = document.querySelector("[data-activity-counter]");
    var emptyState = document.querySelector("[data-activity-empty]");
    var POLL_MS = 45000;
    var TICK_MS = 30000;

    function escapeHtml(str) {
      var div = document.createElement("div");
      div.textContent = str == null ? "" : String(str);
      return div.innerHTML;
    }

    function relativeTime(ts) {
      if (!ts) return "";
      var secs = Math.max(0, Math.floor(Date.now() / 1000 - ts));
      if (secs < 60) return "Just now";
      var mins = Math.floor(secs / 60);
      if (mins < 60) return mins + " minute" + (mins !== 1 ? "s" : "") + " ago";
      var hours = Math.floor(mins / 60);
      if (hours < 24) return hours + " hour" + (hours !== 1 ? "s" : "") + " ago";
      var days = Math.floor(hours / 24);
      return days + " day" + (days !== 1 ? "s" : "") + " ago";
    }

    function cardHtml(a) {
      var logo = a.logo_url
        ? '<img src="' + escapeHtml(a.logo_url) + '" alt="' + escapeHtml(a.org_name) + ' logo" loading="lazy">'
        : '<span class="ed-logo-monogram" aria-hidden="true">' + escapeHtml(a.initial) + "</span>";
      return (
        '<article class="ed-activity ed-activity--' + escapeHtml(a.domain) + '" tabindex="0">' +
        '<div class="ed-activity__logo">' + logo +
        '<span class="ed-activity__icon" aria-hidden="true"><i class="bi ' + escapeHtml(a.icon) + '"></i></span>' +
        "</div>" +
        '<div class="ed-activity__body">' +
        '<p class="ed-activity__text mb-0"><span class="ed-activity__org">' + escapeHtml(a.org_name) + "</span> " + escapeHtml(a.headline) + "</p>" +
        '<div class="ed-activity__meta">' +
        '<span class="ed-domain-badge ed-domain-badge--' + escapeHtml(a.domain) + '"><span class="ed-activity__dot"></span>' + escapeHtml(a.domain_label) + "</span>" +
        '<span class="ed-activity__time" data-ts="' + escapeHtml(a.ts) + '"><i class="bi bi-clock" aria-hidden="true"></i> ' + escapeHtml(relativeTime(a.ts)) + "</span>" +
        "</div></div></article>"
      );
    }

    function currentTopId() {
      var first = feed.querySelector(".ed-activity");
      return first ? first.getAttribute("data-id") : null;
    }

    function render(activities) {
      if (!activities || !activities.length) {
        feed.classList.add("d-none");
        if (emptyState) emptyState.classList.remove("d-none");
        return;
      }
      if (emptyState) emptyState.classList.add("d-none");
      feed.classList.remove("d-none");

      // Skip a full rebuild when nothing changed at the head of the feed.
      var existing = Array.prototype.map.call(
        feed.querySelectorAll(".ed-activity"),
        function (el) {
          return el.getAttribute("data-id");
        }
      );
      var sameOrder =
        existing.length === activities.length &&
        existing.every(function (id, i) {
          return id === activities[i].id;
        });
      if (sameOrder) {
        tick();
        return;
      }

      var prevIds = {};
      existing.forEach(function (id) {
        prevIds[id] = true;
      });

      var html = activities
        .map(function (a) {
          return cardHtml(a).replace(
            '<article class="ed-activity',
            '<article data-id="' + escapeHtml(a.id) + '" class="ed-activity' + (prevIds[a.id] ? "" : " ed-activity--new")
          );
        })
        .join("");
      feed.innerHTML = html;
    }

    function tick() {
      var times = feed.querySelectorAll(".ed-activity__time[data-ts]");
      Array.prototype.forEach.call(times, function (el) {
        var ts = parseInt(el.getAttribute("data-ts"), 10);
        el.innerHTML = '<i class="bi bi-clock" aria-hidden="true"></i> ' + escapeHtml(relativeTime(ts));
      });
    }

    function poll() {
      if (!url) return;
      fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then(function (res) {
          return res.ok ? res.json() : null;
        })
        .then(function (data) {
          if (!data) return;
          if (counter && typeof data.count_today !== "undefined") {
            counter.textContent = data.count_today;
          }
          render(data.activities);
        })
        .catch(function () {
          /* silent — keep last good state */
        });
    }

    // Tag server-rendered cards with ids so the first poll can diff cleanly.
    // (Server markup lacks data-id; the first poll replaces it with keyed cards.)
    setInterval(tick, TICK_MS);
    setInterval(poll, POLL_MS);
    poll();
  }

  /* ------------------------------------------------------------------
     2b. Featured Opportunities carousel
         Horizontal scroll with arrows, mouse-wheel, drag, keyboard,
         scroll-snap, and edge-aware navigation visibility.
     ------------------------------------------------------------------ */
  function initCarousels() {
    var carousels = Array.prototype.slice.call(
      document.querySelectorAll("[data-carousel]")
    );
    carousels.forEach(setupCarousel);
  }

  function setupCarousel(carousel) {
    if (!carousel) return;

    var root = carousel.closest("[data-carousel-root]") || document;
    var nav = root.querySelector("[data-carousel-nav]");
    var prev = root.querySelector("[data-carousel-prev]");
    var next = root.querySelector("[data-carousel-next]");

    function step() {
      var item = carousel.querySelector(".ed-carousel__item");
      if (!item) return carousel.clientWidth;
      var style = window.getComputedStyle(carousel);
      var gap = parseFloat(style.columnGap || style.gap || "0") || 0;
      return item.getBoundingClientRect().width + gap;
    }

    function maxScroll() {
      return carousel.scrollWidth - carousel.clientWidth;
    }

    function isScrollable() {
      return maxScroll() > 2;
    }

    function updateNav() {
      if (nav) {
        nav.classList.toggle("d-none", !isScrollable());
      }
      if (prev) prev.disabled = carousel.scrollLeft <= 2;
      if (next) next.disabled = carousel.scrollLeft >= maxScroll() - 2;
    }

    if (prev) {
      prev.addEventListener("click", function () {
        carousel.scrollBy({ left: -step(), behavior: "smooth" });
      });
    }
    if (next) {
      next.addEventListener("click", function () {
        carousel.scrollBy({ left: step(), behavior: "smooth" });
      });
    }

    // Mouse wheel / trackpad -> horizontal scroll
    carousel.addEventListener(
      "wheel",
      function (event) {
        if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
        if (!isScrollable()) return;
        var atStart = carousel.scrollLeft <= 0 && event.deltaY < 0;
        var atEnd = carousel.scrollLeft >= maxScroll() && event.deltaY > 0;
        if (atStart || atEnd) return; // allow the page to scroll at the edges
        event.preventDefault();
        carousel.scrollLeft += event.deltaY;
      },
      { passive: false }
    );

    // Keyboard accessibility
    carousel.addEventListener("keydown", function (event) {
      if (event.key === "ArrowRight") {
        event.preventDefault();
        carousel.scrollBy({ left: step(), behavior: "smooth" });
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        carousel.scrollBy({ left: -step(), behavior: "smooth" });
      }
    });

    // Drag-to-scroll (mouse/pen only; touch uses native scrolling)
    var isDown = false;
    var startX = 0;
    var startScroll = 0;
    var moved = false;

    carousel.addEventListener("pointerdown", function (event) {
      if (event.pointerType === "touch") return;
      if (event.pointerType === "mouse" && event.button !== 0) return;
      isDown = true;
      moved = false;
      startX = event.clientX;
      startScroll = carousel.scrollLeft;
    });

    carousel.addEventListener("pointermove", function (event) {
      if (!isDown) return;
      var dx = event.clientX - startX;
      if (Math.abs(dx) > 5) {
        moved = true;
        carousel.classList.add("is-dragging");
      }
      carousel.scrollLeft = startScroll - dx;
    });

    function endDrag() {
      if (!isDown) return;
      isDown = false;
      carousel.classList.remove("is-dragging");
    }
    carousel.addEventListener("pointerup", endDrag);
    carousel.addEventListener("pointercancel", endDrag);
    carousel.addEventListener("pointerleave", endDrag);

    // Suppress the click that follows a drag gesture
    carousel.addEventListener(
      "click",
      function (event) {
        if (moved) {
          event.preventDefault();
          event.stopPropagation();
          moved = false;
        }
      },
      true
    );

    carousel.addEventListener("scroll", updateNav, { passive: true });
    window.addEventListener("resize", updateNav);
    updateNav();
  }

  /* ------------------------------------------------------------------
     2c. Save-job toggle (bookmark) on job cards
     ------------------------------------------------------------------ */
  function initSaveButtons() {
    var buttons = document.querySelectorAll("[data-save-job]");
    buttons.forEach(function (btn) {
      btn.setAttribute("aria-pressed", "false");
      btn.addEventListener("click", function () {
        var active = btn.classList.toggle("is-saved");
        var icon = btn.querySelector("i");
        if (icon) {
          icon.classList.toggle("bi-bookmark", !active);
          icon.classList.toggle("bi-bookmark-fill", active);
        }
        btn.setAttribute("aria-pressed", active ? "true" : "false");
      });
    });
  }

  /* ------------------------------------------------------------------
     2d. Hiring partners quick filters + search
     ------------------------------------------------------------------ */
  function initPartnerFilters() {
    var track = document.querySelector("[data-partner-track]");
    if (!track) return;

    var chips = Array.prototype.slice.call(
      document.querySelectorAll("[data-partner-filter]")
    );
    var search = document.querySelector("[data-partner-search]");
    var noResults = document.querySelector("[data-partner-noresults]");
    var items = Array.prototype.slice.call(
      track.querySelectorAll(".ed-carousel__item")
    );
    var activeFilter = "all";

    function apply() {
      var query = (search && search.value ? search.value : "").trim().toLowerCase();
      var visible = 0;

      items.forEach(function (item) {
        var card = item.querySelector("[data-type]");
        var type = card ? card.getAttribute("data-type") : "";
        var name = card ? card.getAttribute("data-name") || "" : "";
        var location = card ? card.getAttribute("data-location") || "" : "";

        var matchesFilter = activeFilter === "all" || type === activeFilter;
        var matchesQuery =
          !query || name.indexOf(query) !== -1 || location.indexOf(query) !== -1;
        var show = matchesFilter && matchesQuery;

        item.style.display = show ? "" : "none";
        if (show) visible += 1;
      });

      if (noResults) noResults.classList.toggle("d-none", visible !== 0);
      track.scrollLeft = 0;
      // Recompute carousel nav visibility after the layout changes.
      window.dispatchEvent(new Event("resize"));
    }

    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        activeFilter = chip.getAttribute("data-partner-filter") || "all";
        chips.forEach(function (c) {
          var isActive = c === chip;
          c.classList.toggle("is-active", isActive);
          c.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
        apply();
      });
    });

    if (search) {
      search.addEventListener("input", apply);
    }
  }

  /* ------------------------------------------------------------------
     3. Scroll-reveal micro-interactions
     ------------------------------------------------------------------ */
  function initReveal() {
    var items = Array.prototype.slice.call(document.querySelectorAll(".ed-reveal"));
    if (!items.length) return;

    if (!("IntersectionObserver" in window)) {
      items.forEach(function (el) {
        el.classList.add("is-visible");
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1 }
    );

    items.forEach(function (el) {
      observer.observe(el);
    });
  }

  /* ------------------------------------------------------------------
     4. Newsletter form (prevent full reload — placeholder handler)
     ------------------------------------------------------------------ */
  function initNewsletter() {
    var form = document.querySelector("[data-newsletter-form]");
    if (!form) return;
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      form.reset();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initTimeline();
    initStoriesCarousel();
    initActivityFeed();
    initCarousels();
    initSaveButtons();
    initPartnerFilters();
    initReveal();
    initNewsletter();
  });
})();
