/**
 * EduNaukri Auth — session isolation, back-button guard, JWT refresh.
 *
 * Login/signup pages rely on server-side WebAuthGuardMiddleware for redirecting
 * already-authenticated users. Client session probes caused redirect loops when
 * refresh cookies were scoped to /auth/ but dashboard routes could not read them.
 */
(function () {
  "use strict";

  var AUTH_STATUS_URL = "/auth/session/status/";
  var REFRESH_URL = "/auth/token/refresh/";
  var LOGOUT_URL = "/auth/logout/";
  var AUTH_LOOP_KEY = "edunaukri_auth_redirect_count";
  var AUTH_LOOP_TS_KEY = "edunaukri_auth_redirect_ts";
  var LOOP_WINDOW_MS = 8000;
  var LOOP_MAX = 2;
  var path = window.location.pathname;
  var isAuthPage =
    path.indexOf("/it/login") === 0 ||
    path.indexOf("/it/signup") === 0 ||
    path.indexOf("/faculty/login") === 0 ||
    path.indexOf("/faculty/signup") === 0;
  var isDashboardPage =
    path.indexOf("/it/dashboard/") === 0 ||
    path.indexOf("/jobseeker/") === 0 ||
    path.indexOf("/recruiter/") === 0 ||
    path.indexOf("/professor/") === 0 ||
    path.indexOf("/college/") === 0;
  var loginInProgress = false;

  function getCsrf() {
    var el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function clearRedirectLoopState() {
    sessionStorage.removeItem(AUTH_LOOP_KEY);
    sessionStorage.removeItem(AUTH_LOOP_TS_KEY);
  }

  function noteRedirectAttempt() {
    var now = Date.now();
    var lastTs = parseInt(sessionStorage.getItem(AUTH_LOOP_TS_KEY) || "0", 10);
    var count = parseInt(sessionStorage.getItem(AUTH_LOOP_KEY) || "0", 10);
    if (!lastTs || now - lastTs > LOOP_WINDOW_MS) {
      count = 0;
    }
    count += 1;
    sessionStorage.setItem(AUTH_LOOP_KEY, String(count));
    sessionStorage.setItem(AUTH_LOOP_TS_KEY, String(now));
    return count;
  }

  function clearStaleAuth() {
    clearRedirectLoopState();
    return fetch(LOGOUT_URL, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrf(),
      },
    }).catch(function () {
      return null;
    });
  }

  function redirectAuthenticated(url) {
    if (!url) return;

    var attempts = noteRedirectAttempt();
    if (attempts > LOOP_MAX) {
      clearStaleAuth().finally(function () {
        var loginPath = window.location.pathname.split("?")[0];
        window.location.replace(loginPath);
      });
      return;
    }

    window.location.replace(url);
  }

  function shouldSkipAuthRedirect() {
    if (loginInProgress) return true;
    if (isAuthPage && /[?&]next=/.test(window.location.search)) return true;
    return false;
  }

  function checkSession() {
    if (shouldSkipAuthRedirect()) {
      return Promise.resolve(false);
    }

    return fetch(AUTH_STATUS_URL, {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        if (shouldSkipAuthRedirect()) {
          return false;
        }
        if (data.authenticated && data.redirect_url) {
          redirectAuthenticated(data.redirect_url);
          return true;
        }
        clearRedirectLoopState();
        return false;
      })
      .catch(function () {
        clearRedirectLoopState();
        return false;
      });
  }

  function silentRefresh() {
    return fetch(REFRESH_URL, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrf(),
      },
    });
  }

  function setLoginInProgress(active) {
    loginInProgress = Boolean(active);
  }

  if (isDashboardPage) {
    document.addEventListener("DOMContentLoaded", checkSession);
    window.addEventListener("pageshow", function (event) {
      if (event.persisted) checkSession();
    });
  }

  window.EduNaukriAuthSession = {
    checkSession: checkSession,
    silentRefresh: silentRefresh,
    redirectReplace: redirectAuthenticated,
    clearStaleAuth: clearStaleAuth,
    clearRedirectLoopState: clearRedirectLoopState,
    setLoginInProgress: setLoginInProgress,
  };
})();
