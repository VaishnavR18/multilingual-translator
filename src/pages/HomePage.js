import React, { useRef, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Html, OrbitControls, Stars } from "@react-three/drei";
import { motion, useAnimation, useInView } from "framer-motion";
import "./HomePage.css";

// Languages to show on globe and float bubbles
const globeLanguages = [
  { code: "en", label: "English", pos: [1, 0, 0] },
  { code: "hi", label: "Hindi", pos: [-1, 0, 0] },
  { code: "es", label: "Spanish", pos: [0, 1, 0] },
  { code: "fr", label: "French", pos: [0, -1, 0] },
  { code: "zh", label: "Chinese", pos: [0, 0, 1] },
  { code: "ar", label: "Arabic", pos: [0, 0, -1] },
  { code: "ru", label: "Russian", pos: [0.7, 0.7, 0] },
];

// 3D Globe Component
function Globe() {
  const group = useRef();
  useFrame(({ clock }) => {
    group.current.rotation.y = clock.getElapsedTime() / 6; // slow rotation
  });

  return (
    <group ref={group}>
      {/* Sphere for globe */}
      <mesh>
        <sphereGeometry args={[2, 64, 64]} />
        <meshStandardMaterial
          color="#4facfe"
          transparent
          opacity={0.3}
          roughness={0.7}
          metalness={0.2}
        />
      </mesh>

      {/* Language markers */}
      {globeLanguages.map(({ label, pos }, i) => (
        <mesh key={i} position={pos} >
          <sphereGeometry args={[0.1, 16, 16]} />
          <meshStandardMaterial color="#00f2fe" />
          <Html center distanceFactor={6}>
            <div className="globe-label">{label}</div>
          </Html>
        </mesh>
      ))}
    </group>
  );
}

// Typing Effect Hook
function useTypingEffect(text, speed = 50) {
  const [displayText, setDisplayText] = useState("");
  useEffect(() => {
    setDisplayText("");
    let currentIndex = 0;
    const timer = setInterval(() => {
      setDisplayText((prev) => prev + text[currentIndex]);
      currentIndex++;
      if (currentIndex >= text.length) clearInterval(timer);
    }, speed);
    return () => clearInterval(timer);
  }, [text, speed]);
  return displayText;
}

const HomePage = () => {
  // Scroll triggered animation controls
  const howItWorksRef = useRef(null);
  const useCasesRef = useRef(null);
  const howItWorksInView = useInView(howItWorksRef, { once: true, margin: "-100px" });
  const useCasesInView = useInView(useCasesRef, { once: true, margin: "-100px" });
  const controlsHow = useAnimation();
  const controlsUse = useAnimation();

  useEffect(() => {
    if (howItWorksInView) controlsHow.start("visible");
  }, [howItWorksInView, controlsHow]);

  useEffect(() => {
    if (useCasesInView) controlsUse.start("visible");
  }, [useCasesInView, controlsUse]);

  

  return (
    <div className="homepage-container">

      {/* Floating languages on background */}
      {globeLanguages.map(({ label }, i) => (
        <span key={i} className="floating-word" style={{ "--i": i }}>
          {label}
        </span>
      ))}

      {/* 3D Globe Canvas */}
      <div className="globe-canvas-wrapper" aria-label="3D rotating globe with languages">
        <Canvas camera={{ position: [0, 0, 7], fov: 45 }}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[5, 5, 5]} intensity={1} />
          <Stars radius={50} depth={20} count={5000} factor={4} saturation={0} fade />
          <Globe />
          <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={0.5} />
        </Canvas>
      </div>

      {/* Hero Section */}
      <motion.section
        className="hero-section"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1 }}
      >
        <motion.h1>
          Break the <span className="highlight">Language Barrier</span>
        </motion.h1>
        <motion.p>
          Translate text, speech, and documents instantly with AI-powered accuracy.
        </motion.p>
        <motion.a href="/translate" className="hero-cta" whileHover={{ scale: 1.05 }}>
          🌐 Start Translating
        </motion.a>
      </motion.section>

      {/* How It Works with Scroll Animations */}
      <motion.section
        className="how-it-works"
        ref={howItWorksRef}
        initial="hidden"
        animate={controlsHow}
        variants={{
          hidden: { opacity: 0, y: 50 },
          visible: { opacity: 1, y: 0, transition: { staggerChildren: 0.2 } }
        }}
      >
        <h2>How It Works</h2>
        <motion.div className="steps">
          {[
            { icon: "🎤", title: "Speak / Type", desc: "Input your message or upload audio." },
            { icon: "🤖", title: "AI Translation", desc: "Our smart AI translates it in real-time." },
            { icon: "🌍", title: "Understand", desc: "Get results you can read or hear aloud." },
          ].map(({ icon, title, desc }, i) => (
            <motion.div
              className="step"
              key={i}
              variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
            >
              <div className="step-icon">{icon}</div>
              <h3>{title}</h3>
              <p>{desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </motion.section>

      {/* Use Cases Section */}
      <motion.section
        className="use-cases"
        ref={useCasesRef}
        initial="hidden"
        animate={controlsUse}
        variants={{
          hidden: { opacity: 0, y: 50 },
          visible: { opacity: 1, y: 0, transition: { staggerChildren: 0.2 } }
        }}
      >
        <h2>Real-World Use Cases</h2>
        <motion.div className="use-cards">
          {[
            { icon: "✈️", title: "Travel", desc: "Communicate abroad with ease." },
            { icon: "📚", title: "Education", desc: "Learn or teach in multiple languages." },
            { icon: "🏛️", title: "Govt & Public", desc: "Bridge communication in official forms." },
          ].map(({ icon, title, desc }, i) => (
            <motion.div
              className="use-card"
              key={i}
              variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
            >
              <div className="use-icon">{icon}</div>
              <h4>{title}</h4>
              <p>{desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </motion.section>

      {/* Newsletter Signup Section */}
      <section className="newsletter-signup">
        <h2>Stay Updated</h2>
        <p>Subscribe to our newsletter for the latest updates, tips, and language tricks.</p>
        <form
          className="newsletter-form"
          onSubmit={(e) => {
          e.preventDefault();
          const email = e.target.elements.email.value.trim();
          if (email) {
            alert(`Thank you for subscribing with ${email}!`);
            e.target.reset();
          } else {
              alert("Please enter a valid email.");
          }
        }}>
        <input
          type="email"
          name="email"
          placeholder="Enter your email"
          required
          aria-label="Email address"/>
          <button type="submit">Subscribe</button>
        </form>
      </section>

    </div>
  );
};

export default HomePage;
