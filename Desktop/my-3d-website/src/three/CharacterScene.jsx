import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js'
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js'
import { gsap } from 'gsap'

const BASE = import.meta.env.BASE_URL

const TYPING_BONES = [
  'thighL','thighR','shinL','shinR','forearmL','forearmR','handL','handR',
  'f_pinky03R','f_pinky02L','f_pinky02R','f_pinky01L','f_pinky01R',
  'palm04L','palm04R','f_ring01L','thumb01L','thumb01R','thumb03L','thumb03R',
  'palm02L','palm02R','palm01L','palm01R','f_index01L','f_index01R',
  'palm03L','palm03R','f_ring02L','f_ring02R','f_ring01R','f_ring03L','f_ring03R',
  'f_middle01L','f_middle02L','f_middle03L','f_middle01R','f_middle02R','f_middle03R',
  'f_index02L','f_index03L','f_index02R','f_index03R','thumb02L','f_pinky03L',
  'upper_armL','upper_armR','thumb02R','toeL','heel02L','toeR','heel02R',
]
const EYEBROW_BONES = ['eyebrow_L', 'eyebrow_R']

async function generateAESKey(password) {
  const buf = new TextEncoder().encode(password)
  const hash = await crypto.subtle.digest('SHA-256', buf)
  return crypto.subtle.importKey('raw', hash.slice(0, 32), { name: 'AES-CBC' }, false, ['decrypt'])
}

async function decryptFile(url, password) {
  const res = await fetch(url)
  const enc = await res.arrayBuffer()
  const iv = new Uint8Array(enc.slice(0, 16))
  const data = enc.slice(16)
  const key = await generateAESKey(password)
  return crypto.subtle.decrypt({ name: 'AES-CBC', iv }, key, data)
}

function filterTracks(clip, boneNames) {
  const tracks = clip.tracks.filter(t => boneNames.some(b => t.name.includes(b)))
  return new THREE.AnimationClip(clip.name + '_f', clip.duration, tracks)
}

// mode="face"  → close-up portrait for hero
// mode="desk"  → full-body side angle for about section
export default function CharacterScene({ style, mode = 'face' }) {
  const containerRef = useRef(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const rect = container.getBoundingClientRect()
    const w = rect.width || window.innerWidth * 0.6
    const h = rect.height || window.innerHeight

    const scene = new THREE.Scene()

    // face: exact original camera — telephoto, monitor hidden → face fills frame
    // desk: zoomed out side angle → full body at desk visible
    const fov = mode === 'face' ? 14.5 : 18
    const camera = new THREE.PerspectiveCamera(fov, w / h, 0.1, 1000)

    if (mode === 'face') {
      camera.position.set(0, 13.1, 24.7)
      camera.zoom = 1.45
    } else {
      // Full body at desk — head to feet visible
      camera.position.set(-1, 9.5, 42)
      camera.lookAt(0, 10.5, 0)
      camera.zoom = 0.85
    }
    camera.updateProjectionMatrix()

    let faceCameraLocked = false

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    renderer.setSize(w, h)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1
    container.appendChild(renderer.domElement)

    // Lighting
    const dirLight = new THREE.DirectionalLight(0x5eead4, 0)
    dirLight.position.set(-0.47, -0.32, -1)
    dirLight.castShadow = true
    scene.add(dirLight)

    const pointLight = new THREE.PointLight(0x22d3ee, 0, 100, 3)
    pointLight.position.set(3, 12, 4)
    scene.add(pointLight)

    // HDR environment
    new RGBELoader()
      .setPath(BASE + 'models/')
      .load('char_enviorment.hdr', (texture) => {
        texture.mapping = THREE.EquirectangularReflectionMapping
        scene.environment = texture
        scene.environmentIntensity = 0
        scene.environmentRotation.set(5.76, 85.85, 1)
      })

    // Mouse tracking
    let mouse = { x: 0, y: 0 }
    let interpolation = { x: 0.1, y: 0.2 }
    const onMouseMove = (e) => {
      mouse.x = (e.clientX / window.innerWidth) * 2 - 1
      mouse.y = -(e.clientY / window.innerHeight) * 2 + 1
    }
    document.addEventListener('mousemove', onMouseMove)

    // DRACO + GLTF loaders
    const dracoLoader = new DRACOLoader()
    dracoLoader.setDecoderPath(BASE + 'draco/')
    const gltfLoader = new GLTFLoader()
    gltfLoader.setDRACOLoader(dracoLoader)

    let mixer, headBone, screenLight, animFrameId
    let cleanup = false

    decryptFile(BASE + 'models/character.enc', 'MyCharacter12').then(async (decrypted) => {
      if (cleanup) return
      const blob = new Blob([decrypted])
      const blobUrl = URL.createObjectURL(blob)

      gltfLoader.load(blobUrl, async (gltf) => {
        if (cleanup) return
        const char = gltf.scene
        await renderer.compileAsync(char, camera, scene)

        char.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = true
            child.receiveShadow = true
            child.frustumCulled = true
          }
        })

        // Hide monitor + screen light at start (same as original)
        char.children.forEach((obj) => {
          if (obj.name === 'Plane004') {
            obj.children.forEach((child) => {
              if (child.material) {
                child.material.transparent = true
                child.material.opacity = mode === 'face' ? 0 : 1
              }
            })
          }
          if (obj.name === 'screenlight') {
            if (obj.material) {
              obj.material.transparent = true
              obj.material.opacity = mode === 'face' ? 0 : 1
            }
          }
        })

        scene.add(char)
        headBone = char.getObjectByName('spine006') || null
        screenLight = char.getObjectByName('screenlight') || null

        // Desk mode: rotate character to front-left angle like reference photo
        if (mode === 'desk') {
          char.rotation.y = 0.75
          char.rotation.x = 0.08
          const neckBone = char.getObjectByName('spine005')
          if (neckBone) neckBone.rotation.x = 0.4
        }


        mixer = new THREE.AnimationMixer(char)

        // Intro (plays once)
        const introClip = gltf.animations.find(c => c.name === 'introAnimation')
        if (introClip) {
          const introAction = mixer.clipAction(introClip)
          introAction.setLoop(THREE.LoopOnce, 1)
          introAction.clampWhenFinished = true
          introAction.play()
        }

        // Key press loops
        ;['key1', 'key2', 'key5', 'key6'].forEach(name => {
          const clip = THREE.AnimationClip.findByName(gltf.animations, name)
          if (clip) {
            const a = mixer.clipAction(clip)
            a.play()
            a.timeScale = 1.2
          }
        })

        // Typing bone animation
        const typingClip = THREE.AnimationClip.findByName(gltf.animations, 'typing')
        if (typingClip) {
          const filtered = filterTracks(typingClip, TYPING_BONES)
          const a = mixer.clipAction(filtered)
          a.enabled = true
          a.play()
          a.timeScale = 1.2
        }

        // Turn on lights after 2.5s
        setTimeout(() => {
          if (cleanup) return
          gsap.to(scene, { environmentIntensity: 0.64, duration: 2, ease: 'power2.inOut' })
          gsap.to(dirLight, { intensity: 1, duration: 2, ease: 'power2.inOut' })

          // Blink
          const blinkClip = gltf.animations.find(c => c.name === 'Blink')
          if (blinkClip) mixer.clipAction(blinkClip).play().fadeIn(0.5)

          // Intro reset
          if (introClip) {
            const a = mixer.clipAction(introClip)
            a.clampWhenFinished = true
            a.reset().play()
          }
        }, 2500)

        URL.revokeObjectURL(blobUrl)
      })
    }).catch(err => console.error('Character load error:', err))

    // Resize
    const onResize = () => {
      if (!container) return
      const r = container.getBoundingClientRect()
      camera.aspect = r.width / r.height
      camera.updateProjectionMatrix()
      renderer.setSize(r.width, r.height)
    }
    window.addEventListener('resize', onResize)

    // Render loop
    const clock = new THREE.Clock()
    const animate = () => {
      animFrameId = requestAnimationFrame(animate)
      const delta = clock.getDelta()
      if (mixer) mixer.update(delta)

      if (headBone && (window.scrollY < 200 || mode === 'face')) {
        const max = Math.PI / 6
        headBone.rotation.y = THREE.MathUtils.lerp(headBone.rotation.y, mouse.x * max, interpolation.y)
        const clampedY = Math.max(-0.3, Math.min(0.4, mouse.y))
        headBone.rotation.x = THREE.MathUtils.lerp(headBone.rotation.x, -clampedY - 0.5 * max, interpolation.x)
      }


      if (screenLight && pointLight) {
        pointLight.intensity = (screenLight.material?.opacity ?? 0) > 0.9
          ? (screenLight.material.emissiveIntensity ?? 1) * 20
          : 0
      }

      renderer.render(scene, camera)
    }
    animate()

    return () => {
      cleanup = true
      cancelAnimationFrame(animFrameId)
      document.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('resize', onResize)
      scene.clear()
      renderer.dispose()
      dracoLoader.dispose()
      if (container && renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [])

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100%', ...style }}
    />
  )
}
