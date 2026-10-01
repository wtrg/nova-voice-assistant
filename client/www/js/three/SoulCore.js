/**
 * Nova Cyber Infinity Soul — Soul Core Component
 * Section 11 & 12 of Nova Design System
 */
class SoulCore {
  constructor() {
    this.group = new THREE.Group();
    this.coreMesh = null;
    this.haloMesh = null;
    this.outerFlare = null;
    this.pointLight = null;
    this._buildCore();
  }

  _buildCore() {
    // 1. Core Sphere (Section 11)
    const coreGeo = new THREE.SphereGeometry(0.24, 32, 32);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
    });
    this.coreMesh = new THREE.Mesh(coreGeo, coreMat);
    this.group.add(this.coreMesh);

    // 2. Inner Energy Halo
    const haloGeo = new THREE.SphereGeometry(0.36, 24, 24);
    const haloMat = new THREE.MeshBasicMaterial({
      color: 0x8cc8ff,
      transparent: true,
      opacity: 0.65,
    });
    this.haloMesh = new THREE.Mesh(haloGeo, haloMat);
    this.group.add(this.haloMesh);

    // 3. Outer Radial Energy Shell
    const outerGeo = new THREE.SphereGeometry(0.55, 24, 24);
    const outerMat = new THREE.MeshBasicMaterial({
      color: 0x5aa9ff,
      transparent: true,
      opacity: 0.28,
    });
    this.outerFlare = new THREE.Mesh(outerGeo, outerMat);
    this.group.add(this.outerFlare);

    // 4. Point Light to dynamically cast reflections onto the Chrome Infinity
    this.pointLight = new THREE.PointLight(0x8cc8ff, 3.2, 8);
    this.group.add(this.pointLight);
  }

  update(time, state) {
    if (!this.group) return;

    let targetIntensity = 3.0;
    let targetPulseRate = 2.0;
    let coreColor = 0xffffff;
    let haloColor = 0x8cc8ff;

    switch (state) {
      case "listening":
        targetIntensity = 5.0;
        targetPulseRate = 3.5;
        haloColor = 0x5aa9ff;
        break;
      case "thinking":
        targetIntensity = 6.0;
        targetPulseRate = 6.0;
        haloColor = 0xb6deff;
        break;
      case "speaking":
        targetIntensity = 5.5 + Math.sin(time * 10) * 2.0;
        targetPulseRate = 5.0;
        haloColor = 0x8cc8ff;
        break;
      case "error":
        targetIntensity = 4.0;
        haloColor = 0xff4d6d;
        coreColor = 0xff99aa;
        break;
      case "idle":
      default:
        targetIntensity = 2.8;
        targetPulseRate = 1.8;
        break;
    }

    const pulse = 1.0 + Math.sin(time * targetPulseRate) * 0.18;
    if (this.haloMesh) {
      this.haloMesh.scale.set(pulse, pulse, pulse);
      this.haloMesh.material.color.setHex(haloColor);
    }
    if (this.outerFlare) {
      const outerPulse = 1.0 + Math.cos(time * targetPulseRate * 0.8) * 0.25;
      this.outerFlare.scale.set(outerPulse, outerPulse, outerPulse);
    }
    if (this.coreMesh) {
      this.coreMesh.material.color.setHex(coreColor);
    }
    if (this.pointLight) {
      this.pointLight.intensity = targetIntensity * (0.8 + Math.sin(time * targetPulseRate) * 0.2);
      this.pointLight.color.setHex(haloColor);
    }
  }

  dispose() {
    if (this.coreMesh) {
      this.coreMesh.geometry.dispose();
      this.coreMesh.material.dispose();
    }
    if (this.haloMesh) {
      this.haloMesh.geometry.dispose();
      this.haloMesh.material.dispose();
    }
    if (this.outerFlare) {
      this.outerFlare.geometry.dispose();
      this.outerFlare.material.dispose();
    }
  }
}

if (typeof window !== "undefined") {
  window.SoulCore = SoulCore;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = SoulCore;
}
