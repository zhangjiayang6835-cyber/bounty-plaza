import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

/**
 * All scroll/load-driven motion on the page: a choreographed hero entrance, a connecting
 * line that draws itself as the burn/attest/mint flow scrolls into view, and staggered
 * reveals for the section heads, problem list, code sample, and closing statement.
 *
 * Respects prefers-reduced-motion by setting every target to its final state immediately
 * and skipping timeline/ScrollTrigger setup entirely.
 */
export function initAnimations(): void {
  const mql = window.matchMedia("(prefers-reduced-motion: reduce)");

  const applyStaticEndState = (): void => {
    ScrollTrigger.getAll().forEach((st) => st.kill());
    gsap.globalTimeline.clear();
    document
      .querySelectorAll<HTMLElement>(
        ".hero-anim-line, .hero-anim, .pos-word, #problem .section-head, #how-it-works .section-head, #problem .problem-item, .flow-node .stage-label, .flow-node .fn, .flow-node p",
      )
      .forEach((el) => {
        el.style.opacity = "1";
        el.style.transform = "none";
      });
    document.querySelectorAll<HTMLElement>(".flow-progress-fill, .flow-dot").forEach((el) => {
      el.style.transform = "none";
    });
    document.querySelectorAll<HTMLElement>("pre.code-block .code-line").forEach((el) => {
      el.style.clipPath = "none";
    });
    document.querySelectorAll<HTMLElement>(".type-cursor").forEach((el) => {
      el.style.opacity = "0";
    });
  };

  mql.addEventListener("change", (ev) => {
    if (ev.matches) {
      applyStaticEndState();
    }
  });

  if (mql.matches) {
    applyStaticEndState();
    return;
  }

  heroEntrance();
  sectionHeadReveals();
  problemReveal();
  flowStripDraw();
  codeBlockReveal();
  positionWords();
}

/**
 * Runs `enter` immediately if `el` is already within the viewport at call time, otherwise
 * defers it to a one-shot ScrollTrigger. An element already on screen when the page loads
 * must never be left waiting on a scroll event that may never come. This is the same class
 * of bug that left the old CSS-only `.reveal` sections permanently invisible (see git history);
 * ScrollTrigger's own initial refresh isn't a reliable enough guarantee to skip this check.
 */
function runOrDefer(el: Element, enter: () => void): void {
  const rect = el.getBoundingClientRect();
  if (rect.top < window.innerHeight && rect.bottom > 0) {
    enter();
    return;
  }
  ScrollTrigger.create({
    trigger: el,
    start: "top 88%",
    once: true,
    onEnter: enter,
  });
}

// --------------------------------------------------------------------- hero entrance

function heroEntrance(): void {
  const lines = gsap.utils.toArray<HTMLElement>(".hero-anim-line");
  const rest = gsap.utils.toArray<HTMLElement>(".hero-copy > .hero-anim");

  gsap.set(lines, { yPercent: 110 });
  gsap.set(rest, { opacity: 0, y: 14 });

  const tl = gsap.timeline({ defaults: { ease: "power4.out" } });
  tl.to(lines, { yPercent: 0, duration: 0.95, stagger: 0.09 })
    .to(rest, { opacity: 1, y: 0, duration: 0.7, stagger: 0.09, ease: "power2.out" }, "-=0.55");
}

// --------------------------------------------------------------------- section headings
// Each section's head enters on a different axis so the page doesn't read as one repeated
// fade-up applied everywhere.

function sectionHeadReveals(): void {
  const variants: { selector: string; from: gsap.TweenVars }[] = [
    { selector: "#problem .section-head", from: { opacity: 0, y: 22 } },
    { selector: "#how-it-works .section-head", from: { opacity: 0, x: -34, skewX: -2 } },
  ];

  for (const variant of variants) {
    const el = document.querySelector<HTMLElement>(variant.selector);
    if (!el) continue;
    gsap.set(el, variant.from);
    runOrDefer(el, () => {
      gsap.to(el, { opacity: 1, x: 0, y: 0, scale: 1, skewX: 0, duration: 0.8, ease: "power3.out" });
    });
  }
}

// --------------------------------------------------------------------- problem: tilted pop-in + hover

function problemReveal(): void {
  const container = document.querySelector("#problem .problem-row");
  if (!container) return;
  const items = gsap.utils.toArray<HTMLElement>(".problem-item", container);

  gsap.set(items, { opacity: 0, y: 30, scale: 0.94, rotateZ: -1.5, transformOrigin: "left center" });
  runOrDefer(container, () => {
    gsap.to(items, {
      opacity: 1,
      y: 0,
      scale: 1,
      rotateZ: 0,
      duration: 0.65,
      stagger: 0.14,
      ease: "back.out(1.8)",
    });
  });
}

// --------------------------------------------------------------------- code block: typing stream

function codeBlockReveal(): void {
  const block = document.querySelector<HTMLElement>("pre.code-block");
  if (!block) return;
  const lines = gsap.utils.toArray<HTMLElement>(".code-line", block);
  if (lines.length === 0) return;

  // width: fit-content matters here. Without it each line's box fills the full pre
  // width, so a percentage clip-path reveals against that instead of the actual text
  // width and the "typing" jumps unevenly instead of tracking character-by-character.
  gsap.set(lines, { clipPath: "inset(0 100% 0 0)" });

  const cursor = document.createElement("span");
  cursor.className = "type-cursor";
  block.appendChild(cursor);
  gsap.set(cursor, { opacity: 0, top: 0, left: 0 });

  runOrDefer(block, () => {
    const tl = gsap.timeline();
    lines.forEach((line, i) => {
      const chars = Math.max(6, (line.textContent ?? "").length);
      const duration = Math.max(0.7, chars / 9);
      const lineWidth = line.scrollWidth;
      const lineTop = line.offsetTop;
      const progress = { t: 0 };
      tl.set(cursor, { top: lineTop, left: 0, opacity: 1 }, i === 0 ? 0 : "+=0.22").to(
        progress,
        {
          t: 1,
          duration,
          ease: `steps(${chars})`,
          // Driving the clip and the cursor off the same interpolated value, in the same
          // onUpdate, guarantees they land on the same pixel every frame. Two separate
          // tweens (even with identical duration/ease) were visibly drifting apart.
          onUpdate: () => {
            line.style.clipPath = `inset(0 ${(1 - progress.t) * 100}% 0 0)`;
            cursor.style.left = `${progress.t * lineWidth}px`;
          },
        },
        "<"
      );
    });
    tl.to(cursor, { opacity: 0, duration: 0.5, repeat: -1, yoyo: true, ease: "steps(1)" });
  });
}

// --------------------------------------------------------------------- burn/attest/mint flow

function flowStripDraw(): void {
  const strip = document.querySelector(".flow-strip");
  if (!strip) return;

  const fill = strip.querySelector(".flow-progress-fill");
  const dots = gsap.utils.toArray<HTMLElement>(".flow-dot", strip);
  const nodes = gsap.utils.toArray<HTMLElement>(".flow-node", strip);

  gsap.set(dots, { scale: 0 });
  gsap.set(nodes.map((n) => n.querySelectorAll(".stage-label, .fn, p")).flat(), { opacity: 0, y: 10 });

  runOrDefer(strip, () => {
    const tl = gsap.timeline({ defaults: { ease: "power2.out" } });
    if (fill) {
      tl.fromTo(fill, { scaleX: 0 }, { scaleX: 1, duration: 1.1, ease: "power1.inOut" }, 0);
    }
    dots.forEach((dot, i) => {
      tl.to(dot, { scale: 1, duration: 0.45, ease: "back.out(3)" }, i * 0.35);
    });
    nodes.forEach((node, i) => {
      const parts = node.querySelectorAll(".stage-label, .fn, p");
      tl.to(parts, { opacity: 1, y: 0, duration: 0.5, stagger: 0.06 }, i * 0.35 + 0.15);
    });
  });
}

// --------------------------------------------------------------------- closing statement

function positionWords(): void {
  const words = gsap.utils.toArray<HTMLElement>(".pos-word");
  const line = document.querySelector(".position-line");
  if (words.length === 0 || !line) return;

  gsap.set(words, { opacity: 0, y: 18 });
  runOrDefer(line, () => {
    gsap.to(words, { opacity: 1, y: 0, duration: 0.6, stagger: 0.12, ease: "power3.out" });
  });
}
