/**
 * Nova Cyber Infinity Soul — HUD Rings & Energy Axis
 * Section 1.1 & 13 of Nova Design System
 */
class HudRings {
  constructor() {
    this.group = new THREE.Group();
    this.outerRing = null;
    this.innerRing = null;
    this.scanArc = null;
    this.axisGroup = null;
    this._buildHud();
  }

  _buildHud() {
    // 1. Outer Ring (Segmented line)
    const outerGeo = new THREE.RingGeometry(2.35, 2.37, 64);
    const outerMat = new THREE.MeshBasicMaterial({
      color: 0x5aa9ff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.25,
    });
    this.outerRing = new THREE.Mesh(outerGeo, outerMat);
    this.group.add(this.outerRing);

    // 2. Inner Reverse Ring (Dashed/finer)
    const innerGeo = new THREE.RingGeometry(1.65, 1.67, 48);
    const innerMat = new THREE.MeshBasicMaterial({
      color: 0x8cc8ff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.22,
    });
    this.innerRing = new THREE.Mesh(innerGeo, innerMat);
    this.group.add(this.innerRing);

    // 3. Scan Ring / Partial Arc
    const scanGeo = new THREE.RingGeometry(1.95, 2.0, 32, 1, 0, Math.PI * 0.45);
    const scanMat = new THREE.MeshBasicMaterial({
      color: 0xb6deff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.55,
    });
    this.scanArc = new THREE.Mesh(scanGeo, scanMat);
    this.group.add(this.scanArc);

    // 4. Vertical Energy Axis with Spherical Metallic Nodes/Beads (Reference Image 1)
    this.axisGroup = new THREE.Group();

    // Central Vertical Line
    const axisLineGeo = new THREE.CylinderGeometry(0.012, 0.012, 5.2, 8);
    const axisLineMat = new THREE.MeshBasicMaterial({
      color: 0x8cc8ff,
      transparent: true,
      opacity: 0.35,
    });
    const axisLine = new THREE.Mesh(axisLineGeo, axisLineMat);
    this.axisGroup.add(axisLine);

    // Metallic Beads / Nodes along the axis
    const nodePositions = [2.2, 1.5, -1.5, -2.2];
    const nodeGeo = new THREE.SphereGeometry(0.07, 16, 16);
    const nodeMat = new THREE.MeshPhysicalMaterial({
      color: 0xe8edf4,
      metalness: 1.0,
      roughness: 0.2,
      clearcoat: 1.0,
    });

    nodePositions.forEach((y) => {
      const node = new THREE.Mesh(nodeGeo, nodeMat);
      node.position.y = y;
      this.axisGroup.add(node);
    });

    this.group.add(this.axisGroup);
  }

  update(time, state) {
    if (!this.group) return;

    let outerSpeed = 0.0015;
    let innerSpeed = -0.0025;
    let scanSpeed = 0.015;

    switch (state) {
      case "listening":
        outerSpeed = 0.004;
        innerSpeed = -0.006;
        scanSpeed = 0.03;
        break;
      case "thinking":
        outerSpeed = 0.008;
        innerSpeed = -0.014;
        scanSpeed = 0.06;
        break;
      case "speaking":
        outerSpeed = 0.005;
        innerSpeed = -0.008;
        scanSpeed = 0.025;
        break;
      case "idle":
      default:
        outerSpeed = 0.0015;
        innerSpeed = -0.0025;
        scanSpeed = 0.015;
        break;
    }

    if (this.outerRing) this.outerRing.rotation.z += outerSpeed;
    if (this.innerRing) this.innerRing.rotation.z += innerSpeed;
    if (this.scanArc) this.scanArc.rotation.z += scanSpeed;

    // Subtle axis breathing
    if (this.axisGroup) {
      const axisPulse = 1.0 + Math.sin(time * 2) * 0.04;
      this.axisGroup.scale.set(1, axisPulse, 1);
    }
  }

  dispose() {
    if (this.outerRing) {
      this.outerRing.geometry.dispose();
      this.outerRing.material.dispose();
    }
    if (this.innerRing) {
      this.innerRing.geometry.dispose();
      this.innerRing.material.dispose();
    }
    if (this.scanArc) {
      this.scanArc.geometry.dispose();
      this.scanArc.material.dispose();
    }
  }
}

if (typeof window !== "undefined") {
  window.HudRings = HudRings;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = HudRings;
}
