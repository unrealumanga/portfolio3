/* app.js — progressive enhancement only.
 *
 * Every page renders and is navigable with this file absent: the work grid is
 * server-rendered, project pages are real documents, and gallery items are
 * plain <button>/<video>. This adds sector filtering, a lightbox, scroll
 * reveal and the sticky-header hairline.
 */

(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- Sticky header hairline ---------- */

  var header = document.getElementById("site-header");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("is-stuck", window.scrollY > 8);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------- Scroll reveal ---------- */

  var revealables = document.querySelectorAll("[data-reveal]");
  if (revealables.length) {
    if (reduceMotion || !("IntersectionObserver" in window)) {
      revealables.forEach(function (el) {
        el.classList.add("is-revealed");
      });
    } else {
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              entry.target.classList.add("is-revealed");
              observer.unobserve(entry.target);
            }
          });
        },
        { rootMargin: "0px 0px -8% 0px", threshold: 0.05 }
      );
      revealables.forEach(function (el) {
        observer.observe(el);
      });
    }
  }

  /* ---------- Sector filter (index only) ---------- */

  var filters = document.getElementById("filters");
  var grid = document.getElementById("work-grid");

  if (filters && grid) {
    var cards = Array.prototype.slice.call(grid.querySelectorAll(".card"));
    var empty = document.getElementById("work-empty");
    var countEl = document.getElementById("work-count");

    filters.addEventListener("click", function (event) {
      var button = event.target.closest(".pill");
      if (!button) return;

      var sector = button.dataset.sector;

      filters.querySelectorAll(".pill").forEach(function (pill) {
        pill.setAttribute("aria-pressed", String(pill === button));
      });

      var shown = 0;
      cards.forEach(function (card) {
        var list = (card.dataset.sectors || "").split("|");
        var match = sector === "__all__" || list.indexOf(sector) !== -1;
        card.hidden = !match;
        if (match) shown++;
      });

      if (empty) empty.hidden = shown !== 0;
      if (countEl) {
        countEl.textContent = shown + (shown === 1 ? " Project" : " Projects");
      }
    });
  }

  /* ---------- Lightbox (project pages) ---------- */

  var lightbox = document.getElementById("lightbox");
  var gallery = document.getElementById("gallery");

  if (lightbox && gallery) {
    var stageImg = document.getElementById("lightbox-img");
    var counter = document.getElementById("lightbox-count");
    var btnPrev = document.getElementById("lightbox-prev");
    var btnNext = document.getElementById("lightbox-next");
    var btnClose = document.getElementById("lightbox-close");

    var items = Array.prototype.slice.call(
      gallery.querySelectorAll("button.gallery-item")
    );
    var current = 0;
    var lastFocused = null;

    var show = function (index) {
      current = (index + items.length) % items.length;
      var item = items[current];
      var img = item.querySelector("img");
      stageImg.src = item.dataset.full;
      stageImg.alt = img ? img.alt : "";
      if (counter) {
        counter.textContent = current + 1 + " / " + items.length;
      }
    };

    var open = function (index) {
      lastFocused = document.activeElement;
      show(index);
      lightbox.hidden = false;
      lightbox.classList.add("is-open");
      document.body.style.overflow = "hidden";
      btnClose.focus();
    };

    var close = function () {
      lightbox.classList.remove("is-open");
      lightbox.hidden = true;
      document.body.style.overflow = "";
      stageImg.src = "";
      if (lastFocused) lastFocused.focus();
    };

    items.forEach(function (item, index) {
      item.addEventListener("click", function () {
        open(index);
      });
    });

    btnPrev.addEventListener("click", function () {
      show(current - 1);
    });
    btnNext.addEventListener("click", function () {
      show(current + 1);
    });
    btnClose.addEventListener("click", close);

    lightbox.addEventListener("click", function (event) {
      if (event.target === lightbox || event.target.closest(".lightbox-stage")) {
        close();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (lightbox.hidden) return;
      if (event.key === "Escape") {
        close();
      } else if (event.key === "ArrowLeft") {
        show(current - 1);
      } else if (event.key === "ArrowRight") {
        show(current + 1);
      } else if (event.key === "Tab") {
        // Trap focus inside the dialog while it is open.
        var focusable = [btnPrev, btnNext, btnClose];
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    });
  }
})();
