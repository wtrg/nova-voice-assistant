/**
 * Nova Cyber Infinity Soul — Chrome Infinity Body
 * Section 3.1 & 8 of Nova Design System
 */
class InfinitySoul {
  constructor(governor) {
    this.governor = governor || new PerformanceGovernor();
    this.group = new THREE.Group();
    this.mesh = null;
    this.edgeMesh = null;
    this._buildMesh();
  }

  _buildMesh() {
    const segments = this.governor.curveSegments || 120;
    const radialSegments = this.governor.tubeRadialSegments || 14;
    const scale = 2.4;
    const points = [];

    // Bernoulli Lemniscate procedural 3D curve (Section 8)
    for (let i = 0; i <= segments; i++) {
      const t = (i / segments) * Math.PI * 2;
      const denom = 1 + Math.sin(t) ** 2;
      const x = (scale * Math.cos(t)) / denom;
      const y = (scale * Math.sin(t) * Math.cos(t)) / denom;
      // 3D elevation so the ribbon crosses in depth like physical metal
      const z = Math.sin(t * 2) * 0.28;
      points.push(new THREE.Vector3(x, y, z));
    }

    const curve = new THREE.CatmullRomCurve3(points, true);
    const radius = 0.15;
    const tubeGeometry = new THREE.TubeGeometry(
      curve,
      segments,
      radius,
      radialSegments,
      true
    );

    // Section 3.1 Chrome Silver Material
    const chromeMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xd9dee7,
      metalness: 1.0,
      roughness: 0.18,
      clearcoat: 1.0,
      clearcoatRoughness: 0.12,
      reflectivity: 0.9,
    });

    this.mesh = new THREE.Mesh(tubeGeometry, chromeMaterial);
    this.group.add(this.mesh);

    // Subtle luminous inner edge line for specular cyber glow
    const edgeCurve = new THREE.CatmullRomCurve3(points, true);
    const edgeGeometry = new THREE.TubeGeometry(
      edgeCurve,
      Math.floor(segments / 2),
      0.03,
      6,
      true
    );
    const edgeMaterial = new THREE.MeshBasicMaterial({
      color: 0xb6deff,
      transparent: true,
      opacity: 0.45,
    });
    this.edgeMesh = new THREE.Mesh(edgeGeometry, edgeMaterial);
    this.group.add(this.edgeMesh);
  }

  update(time, state) {
    if (!this.group) return;

    // State-based animation (Section 16-20)
    let rotSpeedY = 0.003;
    let rotSpeedX = 0.0015;
    let breatheAmp = 0.02;

    switch (state) {
      case "listening":
        rotSpeedY = 0.005;
        breatheAmp = 0.035;
        break;
      case "thinking":
        rotSpeedY = 0.012;
        rotSpeedX = 0.004;
        breatheAmp = 0.04;
        break;
      case "speaking":
        rotSpeedY = 0.008;
        breatheAmp = 0.05 + Math.sin(time * 8) * 0.025;
        break;
      case "error":
        rotSpeedY = 0.001;
        break;
      case "idle":
      default:
        rotSpeedY = 0.003;
        breatheAmp = 0.015;
        break;
    }

    this.group.rotation.y += rotSpeedY;
    this.group.rotation.x = Math.sin(time * 0.5) * 0.08;
    this.group.rotation.z = Math.cos(time * 0.4) * 0.04;

    const scale = 1.0 + Math.sin(time * 1.5) * breatheAmp;
    this.group.scale.set(scale, scale, scale);
  }

  dispose() {
    if (this.mesh) {
      this.mesh.geometry.dispose();
      this.mesh.material.dispose();
    }
    if (this.edgeMesh) {
      this.edgeMesh.geometry.dispose();
      this.edgeMesh.material.dispose();
    }
  }
}

if (typeof window !== "undefined") {
  window.InfinitySoul = InfinitySoul;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = InfinitySoul;
}
