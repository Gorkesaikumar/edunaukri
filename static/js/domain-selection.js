(function () {
  "use strict";

  function initDomainCards() {
    var cards = document.querySelectorAll(".ed-domain-card");
    if (!cards.length) return;

    cards.forEach(function (card) {
      var cta = card.querySelector(".ed-domain-card__cta");
      if (!cta) return;

      card.addEventListener("mouseenter", function () {
        cards.forEach(function (c) {
          c.classList.remove("is-hovered");
        });
        card.classList.add("is-hovered");
      });

      card.addEventListener("mouseleave", function () {
        card.classList.remove("is-hovered");
      });

      card.addEventListener("focusin", function () {
        cards.forEach(function (c) {
          c.classList.remove("is-hovered");
        });
        card.classList.add("is-hovered");
      });

      card.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          cta.click();
        }
      });

      cta.addEventListener("click", function () {
        cta.classList.add("is-loading");
        cta.setAttribute("aria-busy", "true");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initDomainCards();
  });
})();
