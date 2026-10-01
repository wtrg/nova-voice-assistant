/**
 * Nova Cyber Infinity Soul — NovaScene Engine
 * Section 7, 34, 35, 36, 37, 55 of Nova Design System
 */
class NovaScene {
  constructor(containerElement, options = {}) {
    this.container = containerElement;
    this.options = options;
    this.governor = new PerformanceGovernor();
    this.state = "idle"; // idle | listening | thinking | speaking | error | success
    this.isPaused = false;
    this.isDestroyed = false;
    this.animId = null;

    this.renderer = null;
    this.scene = null;
    this.camera = null;

    this.infinitySoul = null;
    this.soulCore = null;
    this.hudRings = null;
    this.energyParticles = null;

    this.ambientLight = null;
    this.dirLight1 = null;
    this.dirLight2 = null;

    this._boundAnimate = this._animate.bind(this);
    this._boundResize = this.resize.bind(this);
    this._boundVisibilityChange = this._onVisibilityChange.bind(this);

    this.init();
  }

  init() {
    if (!this.container || typeof THREE === "undefined") {
      console.warn("[NovaScene] Container or THREE.js not available.");
      return false;
    }

    try {
      const width = this.container.clientWidth || 360;
      const height = this.container.clientHeight || 300;

      // 1. Scene & Camera
      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
      this.camera.position.set(0, 0, 7.2);

      // 2. WebGL Renderer (Clamped DPR, alpha for seamless dark glass background)
      this.renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      });
      this.renderer.setSize(width, height);
      this.renderer.setPixelRatio(this.governor.getEffectiveDpr());
      this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
      this.renderer.toneMappingExposure = 1.15;

      const canvas = this.renderer.domElement;
      canvas.id = "threeCanvas";
      canvas.style.display = "block";
      canvas.style.width = "100%";
      canvas.style.height = "100%";
      canvas.style.pointerEvents = "none";

      this.container.innerHTML = "";
      this.container.appendChild(canvas);

      // 3. Cyber Studio Lighting (Highlights for Chrome metal)
      this.ambientLight = new THREE.AmbientLight(0x101a2c, 1.2);
      this.scene.add(this.ambientLight);

      this.dirLight1 = new THREE.DirectionalLight(0xffffff, 2.2);
      this.dirLight1.position.set(4, 5, 5);
      this.scene.add(this.dirLight1);

      this.dirLight2 = new THREE.DirectionalLight(0x5aa9ff, 1.8);
      this.dirLight2.position.set(-4, -3, 3);
      this.scene.add(this.dirLight2);

      // 4. Construct Core 3D Components
      this.infinitySoul = new InfinitySoul(this.governor);
      this.scene.add(this.infinitySoul.group);

      this.soulCore = new SoulCore();
      this.scene.add(this.soulCore.group);

      this.hudRings = new HudRings();
      this.scene.add(this.hudRings.group);

      this.energyParticles = new EnergyParticles(this.governor);
      if (this.energyParticles.points) {
        this.scene.add(this.energyParticles.points);
      }

      // 5. Event Listeners
      window.addEventListener("resize", this._boundResize);
      document.addEventListener("visibilitychange", this._boundVisibilityChange);

      // 6. Start Render Loop
      this.resume();
      console.log("[NovaScene] Initialized successfully with tier:", this.governor.tier);
      return true;
    } catch (err) {
      console.error("[NovaScene] WebGL initialization failed:", err);
      return false;
    }
  }

  setState(newState) {
    if (this.state === newState) return;
    this.state = newState;
    console.log(`[NovaScene] State transition: ${newState}`);

    // Temporary red pulse for error state, then return to neutral
    if (newState === "error") {
      setTimeout(() => {
        if (this.state === "error") {
          this.setState("idle");
        }
      }, 700);
    }
  }

  setQuality(level) {
    if (this.governor) {
      this.governor.setTier(level);
      if (this.renderer) {
        this.renderer.setPixelRatio(this.governor.getEffectiveDpr());
      }
    }
  }

  resize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    if (width === 0 || height === 0) return;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  pause() {
    this.isPaused = true;
    if (this.animId) {
      cancelAnimationFrame(this.animId);
      this.animId = null;
    }
  }

  resume() {
    if (!this.isPaused && this.animId) return;
    this.isPaused = false;
    this.animId = requestAnimationFrame(this._boundAnimate);
  }

  _onVisibilityChange() {
    if (document.hidden) {
      this.pause();
    } else {
      this.resume();
    }
  }

  _animate(now) {
    if (this.isPaused || this.isDestroyed) return;

    this.governor.trackFrame(now);
    const time = now * 0.001;

    if (this.infinitySoul) this.infinitySoul.update(time, this.state);
    if (this.soulCore) this.soulCore.update(time, this.state);
    if (this.hudRings) this.hudRings.update(time, this.state);
    if (this.energyParticles) this.energyParticles.update(time, this.state);

    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }

    this.animId = requestAnimationFrame(this._boundAnimate);
  }

  destroy() {
    this.isDestroyed = true;
    this.pause();
    window.removeEventListener("resize", this._boundResize);
    document.removeEventListener("visibilitychange", this._boundVisibilityChange);

    if (this.infinitySoul) this.infinitySoul.dispose();
    if (this.soulCore) this.soulCore.dispose();
    if (this.hudRings) this.hudRings.dispose();
    if (this.energyParticles) this.energyParticles.dispose();

    if (this.renderer) {
      this.renderer.dispose();
      if (this.renderer.domElement && this.renderer.domElement.parentNode) {
        this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
      }
    }
  }
}

if (typeof window !== "undefined") {
  window.NovaScene = NovaScene;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = NovaScene;
}
