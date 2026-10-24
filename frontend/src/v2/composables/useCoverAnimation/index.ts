// useCoverAnimation — the "juicy" motion layer for alt-art game covers.
//
// v2 port of v1's `useGameAnimation` (which drove a Vuetify VImg; v2 drives a
// raw <img>). Two behaviours, both gated by the card's hover/focus `active`
// signal and the flags `useCoverArt` resolves:
//   * CD spin     — physical art on a CD platform spins up on hover
//                   (accelerate) and coasts down on leave.
//   * Hover video — miximage art crossfades to its `path_video` clip a beat
//                   after hover, and resets on leave.
//
// All motion is gated by the user's `disableAnimations` setting (via
// `motionEnabled`) AND reduced-motion mode (OS `prefers-reduced-motion` plus
// the user's low-power override, via `useReducedMotion`).
import {
  computed,
  onBeforeUnmount,
  ref,
  watch,
  type ComputedRef,
  type Ref,
} from "vue";
import { useReducedMotion } from "@/v2/composables/useReducedMotion";

export interface SpinConfig {
  /** Top rotational speed, deg/sec. */
  maxSpeed: number;
  /** Acceleration while hovered, deg/sec². */
  accel: number;
  /** Deceleration while not hovered, deg/sec². */
  decel: number;
}

// Mirrors v1's ANIMATION_CONFIG, kept as deg/sec(²) for the frame-rate-
// independent step.
export const SPIN_CONFIG: SpinConfig = {
  maxSpeed: 5000,
  accel: 2500,
  decel: 1500,
};

// Delay before the hover video kicks in, so fast scans across the gallery
// don't fire a burst of <video> loads.
const VIDEO_HOVER_DELAY_MS = 1000;

/** Pure one-frame integration of the spin physics — exported for tests.
 *  `accelerating` is true while the cover is hovered/focused; otherwise the
 *  disc coasts to a stop. Velocity is clamped to `[0, maxSpeed]` and the
 *  angle wraps at 360°. */
export function stepSpin(
  state: { angle: number; velocity: number },
  dtSeconds: number,
  accelerating: boolean,
  cfg: SpinConfig = SPIN_CONFIG,
): { angle: number; velocity: number } {
  const rate = accelerating ? cfg.accel : -cfg.decel;
  const velocity = Math.min(
    cfg.maxSpeed,
    Math.max(0, state.velocity + rate * dtSeconds),
  );
  const angle = (state.angle + velocity * dtSeconds) % 360;
  return { angle, velocity };
}

export interface UseCoverAnimationOptions {
  /** The cover <img> element (the thing that spins / slides). */
  el: Ref<HTMLElement | null>;
  /** The cover box that clips the slide — used for its `offsetHeight`. */
  containerEl: Ref<HTMLElement | null>;
  /** The hover-video <video> element (miximage style), if rendered. */
  videoEl: Ref<HTMLVideoElement | null>;
  /** Disc-spin applies (physical art, CD-based platform). */
  animateCD: ComputedRef<boolean>;
  /** Hover-video src (miximage style), or null. */
  videoUrl: ComputedRef<string | null>;
  /** User's animation preference (`!disableAnimations`). */
  motionEnabled: ComputedRef<boolean>;
  /** Hover / focus state of the card — drives the spin / video. */
  active: Ref<boolean> | ComputedRef<boolean>;
}

export interface UseCoverAnimation {
  /** True while the hover video is actually playing (drives the
   *  image→video crossfade in the card). */
  isVideoPlaying: Ref<boolean>;
}

export function useCoverAnimation(
  opts: UseCoverAnimationOptions,
): UseCoverAnimation {
  // Reactive, so the spin/video stops the instant either input flips.
  const { enabled: reducedMotion } = useReducedMotion();
  const motionOk = computed(
    () => opts.motionEnabled.value && !reducedMotion.value,
  );

  // ── CD spin ───────────────────────────────────────
  let angle = 0;
  let velocity = 0;
  let lastTs: number | null = null;
  let raf: number | null = null;

  function frame(ts: number) {
    const img = opts.el.value;
    if (!img) {
      raf = null;
      return;
    }
    if (lastTs === null) lastTs = ts;
    // Clamp dt so a backgrounded tab doesn't resume with a giant jump.
    const dt = Math.min((ts - lastTs) / 1000, 0.05);
    lastTs = ts;

    const next = stepSpin({ angle, velocity }, dt, opts.active.value);
    angle = next.angle;
    velocity = next.velocity;

    img.style.transform = `rotate(${angle.toFixed(2)}deg)`;

    if (velocity > 0 || opts.active.value) {
      raf = requestAnimationFrame(frame);
    } else {
      stopSpin();
    }
  }

  function kickSpin() {
    if (raf === null) {
      lastTs = null;
      raf = requestAnimationFrame(frame);
    }
  }

  function stopSpin() {
    if (raf !== null) cancelAnimationFrame(raf);
    raf = null;
    lastTs = null;
    angle = 0;
    velocity = 0;
    const img = opts.el.value;
    if (img) img.style.transform = "";
  }

  const wantsSpin = computed(
    () => opts.active.value && opts.animateCD.value && motionOk.value,
  );
  watch(wantsSpin, (on) => {
    if (on) kickSpin();
    // Leaving: the frame loop coasts down on its own (active is false).
  });
  watch(
    () => opts.animateCD.value,
    (cd) => {
      if (!cd) stopSpin();
    },
  );

  // ── Hover video ───────────────────────────────────────────────────
  const isVideoPlaying = ref(false);
  let videoTimer: number | null = null;

  const wantsVideo = computed(
    () => opts.active.value && !!opts.videoUrl.value && motionOk.value,
  );

  function scheduleVideo() {
    cancelVideoTimer();
    videoTimer = window.setTimeout(() => {
      const v = opts.videoEl.value;
      if (!v) return;
      v.play()
        .then(() => {
          isVideoPlaying.value = true;
        })
        .catch(() => {
          isVideoPlaying.value = false;
        });
    }, VIDEO_HOVER_DELAY_MS);
  }

  function cancelVideoTimer() {
    if (videoTimer !== null) {
      clearTimeout(videoTimer);
      videoTimer = null;
    }
  }

  function stopVideo() {
    cancelVideoTimer();
    isVideoPlaying.value = false;
    const v = opts.videoEl.value;
    if (v) {
      v.pause();
      v.currentTime = 0;
    }
  }

  watch(wantsVideo, (on) => {
    if (on) scheduleVideo();
    else stopVideo();
  });

  // ── Motion preference flips off mid-flight ────────────────────────
  watch(motionOk, (ok) => {
    if (!ok) {
      stopSpin();
      stopVideo();
    }
  });

  onBeforeUnmount(() => {
    stopSpin();
    cancelVideoTimer();
    const v = opts.videoEl.value;
    if (v) v.pause();
  });

  return { isVideoPlaying };
}
