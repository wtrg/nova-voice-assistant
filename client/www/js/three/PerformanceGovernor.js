/**
 * Nova Cyber Infinity Soul — Performance Governor
 * Section 33, 34, 35 of Nova Design System
 */
class PerformanceGovernor {
  constructor() {
    this.tier = "MEDIUM"; // LOW | MEDIUM | HIGH
    this.targetFps = 60;
    this.fps = 60;
    this.frames = 0;
    this.lastTime = performance.now();
    this.lowFpsCounter = 0;
    this.maxDpr = 1.5;
    this._detectInitialCapabilities();
  }

  _detectInitialCapabilities() {
    // Detect mobile / low-memory hints
    const memory = navigator.deviceMemory || 4;
    const hardwareConcurrency = navigator.hardwareConcurrency || 4;
    if (memory <= 2 || hardwareConcurrency <= 2) {
      this.setTier("LOW");
    } else if (memory >= 8 && hardwareConcurrency >= 8) {
      this.setTier("HIGH");
    } else {
      this.setTier("MEDIUM");
    }
  }

  setTier(tier) {
    this.tier = tier;
    switch (tier) {
      case "LOW":
        this.maxDpr = 1.0;
        this.particleBudget = 40;
        this.curveSegments = 90;
        this.tubeRadialSegments = 10;
        this.enableBloom = false;
        break;
      case "HIGH":
        this.maxDpr = Math.min(window.devicePixelRatio || 1, 2.0);
        this.particleBudget = 160;
        this.curveSegments = 160;
        this.tubeRadialSegments = 18;
        this.enableBloom = true;
        break;
      case "MEDIUM":
      default:
        this.maxDpr = Math.min(window.devicePixelRatio || 1, 1.5);
        this.particleBudget = 90;
        this.curveSegments = 120;
        this.tubeRadialSegments = 14;
        this.enableBloom = false;
        break;
    }
  }

  getEffectiveDpr() {
    return Math.min(window.devicePixelRatio || 1, this.maxDpr);
  }

  trackFrame(now) {
    this.frames++;
    const delta = now - this.lastTime;
    if (delta >= 1000) {
      this.fps = Math.round((this.frames * 1000) / delta);
      this.frames = 0;
      this.lastTime = now;

      // Auto degrade if struggling under 32 FPS for 3 consecutive seconds
      if (this.fps < 32) {
        this.lowFpsCounter++;
        if (this.lowFpsCounter >= 3 && this.tier !== "LOW") {
          console.warn(`[PerformanceGovernor] Low FPS detected (${this.fps}), downgrading tier.`);
          this.setTier(this.tier === "HIGH" ? "MEDIUM" : "LOW");
          this.lowFpsCounter = 0;
        }
      } else {
        this.lowFpsCounter = 0;
      }
    }
    return this.fps;
  }
}

if (typeof window !== "undefined") {
  window.PerformanceGovernor = PerformanceGovernor;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = PerformanceGovernor;
}
