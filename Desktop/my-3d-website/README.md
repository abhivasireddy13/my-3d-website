# Abhi Vasireddy — 3D Portfolio

> Personal portfolio website with an interactive 3D character, physics-based skills section, and smooth scroll animations.

**Live →** [abhivasireddy13.github.io/my-3d-website](https://abhivasireddy13.github.io/my-3d-website/)

![Preview](public/preview.svg)

---

## Tech Stack

| Layer | Tools |
|---|---|
| Framework | React 19 + Vite 8 |
| 3D / WebGL | Three.js · @react-three/fiber · @react-three/drei |
| Animations | Framer Motion · GSAP · Lenis (smooth scroll) |
| Physics | Matter.js (Skills section) |
| Styling | Tailwind CSS v4 |
| Deployment | GitHub Pages via GitHub Actions |

---

## Features

- **Interactive 3D Character** — encrypted GLTF model with idle/typing animations, head tracks mouse cursor
- **Face Portrait Hero** — telephoto camera framing (fov 14.5) isolates face with monitor hidden
- **Desk View (About)** — full-body side-angle with monitor visible, matching original reference aesthetic
- **Physics Skills Board** — Matter.js 2D rigid-body simulation, skill badges bounce and collide
- **Smooth Scroll** — Lenis scroll driver synced with Framer Motion viewport triggers
- **Dark Theme** — `#0a0a0f` base, electric cyan `#00e5ff` accent, purple `#7928ca` fill
- **Responsive** — 3D canvas hidden on mobile (<900px), full layout preserved
- **GitHub Pages CI** — auto-deploys on every push to `main`

---

## Project Structure

```
Desktop/my-3d-website/
├── public/
│   ├── models/
│   │   ├── character.enc        # AES-CBC encrypted GLTF character
│   │   └── char_enviorment.hdr  # HDRI environment lighting
│   ├── draco/                   # DRACO mesh decoder
│   ├── robot.glb                # Three.js RobotExpressive fallback
│   └── Abhi_Vasireddy.pdf       # Resume
├── src/
│   ├── components/
│   │   ├── Hero.jsx             # Landing section + 3D canvas
│   │   ├── About.jsx            # About section + desk view
│   │   ├── Skills.jsx           # Physics skills board
│   │   ├── Projects.jsx         # Project cards
│   │   ├── Experience.jsx       # Timeline
│   │   ├── Contact.jsx          # Contact form
│   │   └── Navbar.jsx
│   └── three/
│       ├── CharacterScene.jsx   # Vanilla Three.js character loader
│       └── RobotModel.jsx       # @react-three/fiber robot fallback
└── .github/workflows/deploy.yml
```

---

## Local Development

```bash
# Clone
git clone https://github.com/abhivasireddy13/my-3d-website.git
cd my-3d-website/Desktop/my-3d-website

# Install
npm install

# Dev server (port 5180)
npm run dev

# Production build
npm run build
```

---

## Deployment

Pushes to `main` automatically trigger the **Deploy to GitHub Pages** workflow:

```
push → actions/checkout → npm ci → npm run build → upload dist → deploy
```

---

## About Me

Final-year B.Tech CSE (AI & ML) student at **Manipal Institute of Technology**.  
Specialising in LLM fine-tuning, RAG pipelines, multi-agent systems, and production MLOps infrastructure.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-abhishek--sai--vasireddy-0077B5?style=flat&logo=linkedin)](https://linkedin.com/in/abhishek-sai-vasireddy)
[![GitHub](https://img.shields.io/badge/GitHub-abhivasireddy13-181717?style=flat&logo=github)](https://github.com/abhivasireddy13)

---

<sub>Built with React + Three.js · Deployed on GitHub Pages</sub>
