/**
 * Terra - the 3D animated neural assistant avatar.
 *
 * Renders a glowing globe wrapped in a rotating "neural network" (neurons +
 * connecting synapses) using Three.js (loaded from CDN). The avatar reacts to
 * the assistant's state:
 *   - "idle"     : gentle float, slow neural rotation, soft twinkle.
 *   - "thinking" : faster rotation, brighter neurons, energised rings.
 *   - "speaking" : floating circles ripple outward from Terra.
 *
 * Accessibility & robustness:
 *   - The canvas is purely decorative (the conversation carries the meaning).
 *   - If WebGL or Three.js is unavailable, a CSS fallback orb is shown instead.
 *   - If the user prefers reduced motion, animation is minimised.
 *
 * Public API: window.TerraAvatar.setState("idle" | "thinking" | "speaking").
 */

"use strict";

window.TerraAvatar = (function () {
  var state = "idle";
  var reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var scene, camera, renderer, clock;
  var globe, halo, brain, neurons, lines, ring1, ring2;
  var pulses = [];
  var active = false;
  var NEURON_COUNT = 72;
  var NEURON_RADIUS = 1.55;

  /** Show the CSS fallback orb and hide the WebGL canvas. */
  function useFallback() {
    var fb = document.getElementById("avatar-fallback");
    if (fb) {
      fb.removeAttribute("aria-hidden");
      fb.style.display = "grid";
    }
  }

  /** Build a soft round sprite texture for the neuron points. */
  function makeDotTexture() {
    var c = document.createElement("canvas");
    c.width = c.height = 64;
    var ctx = c.getContext("2d");
    var g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0.0, "rgba(255,255,255,1)");
    g.addColorStop(0.3, "rgba(160,255,210,0.95)");
    g.addColorStop(1.0, "rgba(160,255,210,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 64, 64);
    var tex = new THREE.Texture(c);
    tex.needsUpdate = true;
    return tex;
  }

  /** Distribute points evenly on a sphere (Fibonacci spiral). */
  function fibonacciSphere(n, radius) {
    var pts = [];
    var phi = Math.PI * (3 - Math.sqrt(5));
    for (var i = 0; i < n; i++) {
      var y = 1 - (i / (n - 1)) * 2;
      var r = Math.sqrt(1 - y * y);
      var theta = phi * i;
      pts.push([
        Math.cos(theta) * r * radius,
        y * radius,
        Math.sin(theta) * r * radius,
      ]);
    }
    return pts;
  }

  /** Create the Three.js scene, or fall back gracefully. */
  function init() {
    var mount = document.getElementById("avatar-canvas");
    if (!mount) return;
    if (typeof THREE === "undefined") {
      useFallback();
      return;
    }

    var width = mount.clientWidth || 300;
    var height = mount.clientHeight || 300;

    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch (err) {
      useFallback();
      return;
    }
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    mount.appendChild(renderer.domElement);

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.z = 4.6;

    // --- Core glowing globe -------------------------------------------------
    globe = new THREE.Mesh(
      new THREE.SphereGeometry(1.12, 48, 48),
      new THREE.MeshStandardMaterial({
        color: 0x14a063,
        emissive: 0x0b6b3a,
        emissiveIntensity: 0.5,
        roughness: 0.35,
        metalness: 0.15,
      })
    );
    scene.add(globe);

    // --- Soft outer halo ----------------------------------------------------
    halo = new THREE.Mesh(
      new THREE.SphereGeometry(1.7, 32, 32),
      new THREE.MeshBasicMaterial({
        color: 0x18b06a,
        transparent: true,
        opacity: 0.08,
      })
    );
    scene.add(halo);

    // --- Neural network (neurons + synapse lines), grouped to rotate -------
    brain = new THREE.Group();
    scene.add(brain);

    var pts = fibonacciSphere(NEURON_COUNT, NEURON_RADIUS);

    var positions = new Float32Array(NEURON_COUNT * 3);
    for (var i = 0; i < NEURON_COUNT; i++) {
      positions[i * 3] = pts[i][0];
      positions[i * 3 + 1] = pts[i][1];
      positions[i * 3 + 2] = pts[i][2];
    }
    var neuronGeo = new THREE.BufferGeometry();
    neuronGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    neurons = new THREE.Points(
      neuronGeo,
      new THREE.PointsMaterial({
        size: 0.17,
        map: makeDotTexture(),
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        color: 0xbafff0,
      })
    );
    brain.add(neurons);

    // Connect each neuron to its two nearest neighbours -> synapses.
    var segs = [];
    for (var a = 0; a < NEURON_COUNT; a++) {
      var dists = [];
      for (var b = 0; b < NEURON_COUNT; b++) {
        if (a === b) continue;
        var dx = pts[a][0] - pts[b][0];
        var dy = pts[a][1] - pts[b][1];
        var dz = pts[a][2] - pts[b][2];
        dists.push([dx * dx + dy * dy + dz * dz, b]);
      }
      dists.sort(function (m, n) { return m[0] - n[0]; });
      for (var k = 0; k < 2; k++) {
        var j = dists[k][1];
        segs.push(pts[a][0], pts[a][1], pts[a][2], pts[j][0], pts[j][1], pts[j][2]);
      }
    }
    var lineGeo = new THREE.BufferGeometry();
    lineGeo.setAttribute("position",
      new THREE.BufferAttribute(new Float32Array(segs), 3));
    lines = new THREE.LineSegments(
      lineGeo,
      new THREE.LineBasicMaterial({
        color: 0x49e3c2,
        transparent: true,
        opacity: 0.22,
      })
    );
    brain.add(lines);

    // --- Floating orbital rings --------------------------------------------
    ring1 = new THREE.Mesh(
      new THREE.TorusGeometry(1.95, 0.018, 12, 90),
      new THREE.MeshBasicMaterial({ color: 0x18b06a, transparent: true, opacity: 0.4 })
    );
    ring1.rotation.x = Math.PI / 2.1;
    scene.add(ring1);

    ring2 = new THREE.Mesh(
      new THREE.TorusGeometry(2.2, 0.014, 12, 90),
      new THREE.MeshBasicMaterial({ color: 0x49e3c2, transparent: true, opacity: 0.3 })
    );
    ring2.rotation.x = Math.PI / 3;
    ring2.rotation.y = Math.PI / 5;
    scene.add(ring2);

    // --- Pool of expanding "floating circle" ripples (used when speaking) --
    for (var p = 0; p < 5; p++) {
      var ripple = new THREE.Mesh(
        new THREE.RingGeometry(0.92, 1.0, 56),
        new THREE.MeshBasicMaterial({
          color: 0x8ef3c0,
          transparent: true,
          opacity: 0,
          side: THREE.DoubleSide,
          depthWrite: false,
        })
      );
      ripple.visible = false;
      scene.add(ripple);
      pulses.push({ mesh: ripple, t: 0, active: false });
    }

    // --- Lighting -----------------------------------------------------------
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    var key = new THREE.DirectionalLight(0xffffff, 0.9);
    key.position.set(3, 4, 5);
    scene.add(key);
    var rim = new THREE.DirectionalLight(0x9ef7c6, 0.5);
    rim.position.set(-4, -2, 2);
    scene.add(rim);

    clock = new THREE.Clock();
    active = true;
    window.addEventListener("resize", onResize);

    if (reduceMotion) {
      renderOnce();
    } else {
      animate();
    }
  }

  function onResize() {
    var mount = document.getElementById("avatar-canvas");
    if (!mount || !renderer || !camera) return;
    var w = mount.clientWidth || 300;
    var h = mount.clientHeight || 300;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  function renderOnce() {
    if (renderer) renderer.render(scene, camera);
  }

  /** Activate the next free ripple (a floating circle expanding outward). */
  function emitRipple() {
    for (var i = 0; i < pulses.length; i++) {
      if (!pulses[i].active) {
        pulses[i].active = true;
        pulses[i].t = 0;
        pulses[i].mesh.visible = true;
        return;
      }
    }
  }

  var rippleTimer = 0;

  function animate() {
    if (!active) return;
    requestAnimationFrame(animate);

    var t = clock.getElapsedTime();
    var dt = Math.min(clock.getDelta(), 0.05);
    var spin = state === "thinking" ? 0.9 : 0.2;

    // Rotate the neural network and globe.
    brain.rotation.y += spin * 0.02;
    brain.rotation.x = Math.sin(t * 0.35) * 0.18;
    globe.rotation.y += spin * 0.01;

    // Gentle vertical bob.
    var bob = Math.sin(t * 1.2) * 0.06;
    brain.position.y = bob;
    globe.position.y = bob;
    halo.position.y = bob;

    // Neuron twinkle + state-based brightness.
    var baseGlow = state === "thinking" ? 1.0 : state === "speaking" ? 0.9 : 0.75;
    neurons.material.opacity = baseGlow * (0.8 + 0.2 * Math.sin(t * 3.0));
    lines.material.opacity =
      (state === "idle" ? 0.2 : 0.32) * (0.85 + 0.15 * Math.sin(t * 2.0));

    // Globe emissive responds to state.
    var targetGlow =
      state === "thinking" ? 0.85 : state === "speaking" ? 0.72 : 0.5;
    globe.material.emissiveIntensity +=
      (targetGlow - globe.material.emissiveIntensity) * 0.08;

    // Orbital rings drift; spin up while thinking.
    ring1.rotation.z += 0.006 + spin * 0.01;
    ring2.rotation.z -= 0.005 + spin * 0.008;

    // While active, periodically emit floating-circle ripples.
    if (state === "thinking" || state === "speaking") {
      rippleTimer += dt;
      var interval = state === "speaking" ? 0.5 : 0.9;
      if (rippleTimer >= interval) {
        rippleTimer = 0;
        emitRipple();
      }
    }

    // Advance active ripples (expand + fade).
    for (var i = 0; i < pulses.length; i++) {
      var pu = pulses[i];
      if (!pu.active) continue;
      pu.t += dt;
      var prog = pu.t / 1.5;
      var s = 1 + prog * 2.6;
      pu.mesh.scale.set(s, s, s);
      pu.mesh.material.opacity = Math.max(0, 0.55 * (1 - prog));
      pu.mesh.lookAt(camera.position);
      if (prog >= 1) {
        pu.active = false;
        pu.mesh.visible = false;
      }
    }

    renderer.render(scene, camera);
  }

  /** Public: change the avatar's emotional state. */
  function setState(next) {
    state = next;
    if (next === "speaking") emitRipple();
    if (reduceMotion) renderOnce();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  return { setState: setState };
})();
