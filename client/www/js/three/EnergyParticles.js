/**
 * Nova Cyber Infinity Soul — Energy Particles
 * Section 14 & 36 of Nova Design System
 */
class EnergyParticles {
  constructor(governor) {
    this.governor = governor || new PerformanceGovernor();
    this.count = this.governor.particleBudget || 90;
    this.points = null;
    this.geometry = null;
    this.positions = null;
    this.velocities = null;
    this._buildParticles();
  }

  _buildParticles() {
    this.geometry = new THREE.BufferGeometry();
    this.positions = new Float32Array(this.count * 3);
    this.velocities = new Float32Array(this.count * 3);

    for (let i = 0; i < this.count; i++) {
      const idx = i * 3;
      // Distribute particles in a spherical torus shell around the Soul Core
      const theta = Math.random() * Math.PI * 2;
      const phi = (Math.random() - 0.5) * Math.PI;
      const dist = 0.8 + Math.random() * 2.2;

      this.positions[idx] = dist * Math.cos(theta) * Math.cos(phi);
      this.positions[idx + 1] = dist * Math.sin(phi);
      this.positions[idx + 2] = dist * Math.sin(theta) * Math.cos(phi);

      this.velocities[idx] = (Math.random() - 0.5) * 0.006;
      this.velocities[idx + 1] = (Math.random() - 0.5) * 0.006;
      this.velocities[idx + 2] = (Math.random() - 0.5) * 0.006;
    }

    this.geometry.setAttribute(
      "position",
      new THREE.BufferAttribute(this.positions, 3)
    );

    const material = new THREE.PointsMaterial({
      color: 0x8cc8ff,
      size: 0.05,
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending,
    });

    this.points = new THREE.Points(this.geometry, material);
  }

  update(time, state) {
    if (!this.geometry || !this.positions) return;

    let speedMult = 1.0;
    switch (state) {
      case "listening":
        speedMult = 1.6;
        break;
      case "thinking":
        speedMult = 2.8;
        break;
      case "speaking":
        speedMult = 2.0;
        break;
      case "idle":
      default:
        speedMult = 1.0;
        break;
    }

    const pos = this.positions;
    const v = this.velocities;
    const count = this.count;

    for (let i = 0; i < count; i++) {
      const idx = i * 3;
      pos[idx] += v[idx] * speedMult;
      pos[idx + 1] += v[idx + 1] * speedMult;
      pos[idx + 2] += v[idx + 2] * speedMult;

      // Orbit pull towards center
      const d = Math.sqrt(pos[idx] ** 2 + pos[idx + 1] ** 2 + pos[idx + 2] ** 2);
      if (d > 3.2 || d < 0.4) {
        pos[idx] *= 0.5;
        pos[idx + 1] *= 0.5;
        pos[idx + 2] *= 0.5;
      }
    }

    this.geometry.attributes.position.needsUpdate = true;
  }

  dispose() {
    if (this.geometry) this.geometry.dispose();
    if (this.points && this.points.material) this.points.material.dispose();
  }
}

if (typeof window !== "undefined") {
  window.EnergyParticles = EnergyParticles;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = EnergyParticles;
}
