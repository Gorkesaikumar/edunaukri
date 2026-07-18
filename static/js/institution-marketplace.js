(function () {
  "use strict";

  var config = window.IM_CONFIG || {};

  function notify(type, message) {
    if (window.EduNotify && typeof window.EduNotify.toast === "function") {
      window.EduNotify.toast(type, message);
    }
  }

  function initShare() {
    document.querySelectorAll(".im-share-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var url = btn.getAttribute("data-share-url") || window.location.href;
        if (navigator.share) {
          navigator.share({ title: document.title, url: url }).catch(function () {});
          return;
        }
        if (navigator.clipboard) {
          navigator.clipboard.writeText(window.location.href).then(function () {
            notify("success", "Profile link copied.");
          });
        }
      });
    });
  }

  function initSuggest() {
    var input = document.getElementById("imSearchInput");
    if (!input || !config.suggestApiUrl) return;
    var timer;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      var q = input.value.trim();
      if (q.length < 2) return;
      timer = setTimeout(function () {
        fetch(config.suggestApiUrl + "?q=" + encodeURIComponent(q), {
          credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest" },
        })
          .then(function (res) { return res.json(); })
          .then(function (payload) {
            if (!payload.success || !payload.data.length) return;
            var first = payload.data[0];
            if (first && first.url && q.length > 4) {
              input.setAttribute("list", "imSuggestList");
            }
          })
          .catch(function () {});
      }, 300);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initShare();
    initSuggest();
  });
})();
