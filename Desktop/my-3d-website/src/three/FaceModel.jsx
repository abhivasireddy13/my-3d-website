import { useRef, useMemo } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'

// --- Simplex 3D noise (Stefan Gustavson / Ashima Arts) ---
const NOISE_GLSL = /* glsl */`
vec3 n_mod289(vec3 x){return x-floor(x*(1./289.))*289.;}
vec4 n_mod289(vec4 x){return x-floor(x*(1./289.))*289.;}
vec4 n_permute(vec4 x){return n_mod289(((x*34.)+1.)*x);}
vec4 n_taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){
  const vec2 C=vec2(1./6.,1./3.);
  const vec4 D=vec4(0.,.5,1.,2.);
  vec3 i=floor(v+dot(v,C.yyy));
  vec3 x0=v-i+dot(i,C.xxx);
  vec3 g=step(x0.yzx,x0.xyz);
  vec3 l=1.-g;
  vec3 i1=min(g.xyz,l.zxy);
  vec3 i2=max(g.xyz,l.zxy);
  vec3 x1=x0-i1+C.xxx;
  vec3 x2=x0-i2+C.yyy;
  vec3 x3=x0-D.yyy;
  i=n_mod289(i);
  vec4 p=n_permute(n_permute(n_permute(
    i.z+vec4(0.,i1.z,i2.z,1.))
    +i.y+vec4(0.,i1.y,i2.y,1.))
    +i.x+vec4(0.,i1.x,i2.x,1.));
  float n_=.142857142857;
  vec3 ns=n_*D.wyz-D.xzx;
  vec4 j=p-49.*floor(p*ns.z*ns.z);
  vec4 x_=floor(j*ns.z);
  vec4 y_=floor(j-7.*x_);
  vec4 x=x_*ns.x+ns.yyyy;
  vec4 y=y_*ns.x+ns.yyyy;
  vec4 h=1.-abs(x)-abs(y);
  vec4 b0=vec4(x.xy,y.xy);
  vec4 b1=vec4(x.zw,y.zw);
  vec4 s0=floor(b0)*2.+1.;
  vec4 s1=floor(b1)*2.+1.;
  vec4 sh=-step(h,vec4(0.));
  vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;
  vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
  vec3 p0=vec3(a0.xy,h.x);
  vec3 p1=vec3(a0.zw,h.y);
  vec3 p2=vec3(a1.xy,h.z);
  vec3 p3=vec3(a1.zw,h.w);
  vec4 norm=n_taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
  p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
  vec4 m=max(.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.);
  m=m*m;
  return 42.*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
}
`

const vertexShader = /* glsl */`
${NOISE_GLSL}
uniform float uTime;
varying vec3 vNormal;
varying vec3 vPos;
void main(){
  vNormal = normal;
  vPos    = position;
  float n = snoise(position * 1.3 + uTime * 0.2) * 0.38;
  vec3  d = position + normal * n;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(d, 1.0);
}
`

const fragmentShader = /* glsl */`
uniform float uTime;
varying vec3 vNormal;
varying vec3 vPos;
void main(){
  vec3 eye = normalize(vec3(0.0, 0.0, 1.0));
  float f   = pow(1.0 - max(dot(normalize(vNormal), eye), 0.0), 2.6);
  vec3 cyan   = vec3(0.0,   0.898, 1.0);
  vec3 purple = vec3(0.475, 0.157, 0.796);
  vec3 dark   = vec3(0.035, 0.055, 0.11);
  vec3 col    = mix(dark, cyan, f * 0.92);
  float pulse = 0.5 + 0.5 * sin(uTime * 0.65 + vPos.y * 3.8);
  col += purple * 0.22 * pulse;
  gl_FragColor = vec4(col, 0.86 + f * 0.14);
}
`

// Noise-displaced, Fresnel-lit sphere — the hero centrepiece
function AnimatedSphere() {
  const matRef  = useRef()
  const uniforms = useMemo(() => ({ uTime: { value: 0 } }), [])

  useFrame(({ clock }) => {
    if (matRef.current) matRef.current.uniforms.uTime.value = clock.elapsedTime
  })

  return (
    <mesh>
      <icosahedronGeometry args={[1.85, 80]} />
      <shaderMaterial
        ref={matRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        side={THREE.DoubleSide}
      />
    </mesh>
  )
}

// Low-poly wireframe shell — spins opposite to main group
function WireframeSphere() {
  const ref = useRef()
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y -= delta * 0.14
  })
  return (
    <mesh ref={ref}>
      <icosahedronGeometry args={[2.12, 4]} />
      <meshBasicMaterial color="#00e5ff" wireframe transparent opacity={0.11} />
    </mesh>
  )
}

// 1800 particles distributed on a sphere shell, drifting slowly
function Particles() {
  const COUNT = 1800
  const positions = useMemo(() => {
    const arr = new Float32Array(COUNT * 3)
    for (let i = 0; i < COUNT; i++) {
      const r     = 2.55 + Math.random() * 0.85
      const theta = Math.random() * Math.PI * 2
      const phi   = Math.acos(2 * Math.random() - 1)
      arr[i * 3]     = r * Math.sin(phi) * Math.cos(theta)
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      arr[i * 3 + 2] = r * Math.cos(phi)
    }
    return arr
  }, [])

  const ref = useRef()
  useFrame((_, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * 0.045
      ref.current.rotation.x += delta * 0.02
    }
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={COUNT} array={positions} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.017} color="#00e5ff" transparent opacity={0.5} sizeAttenuation />
    </points>
  )
}

// Three torus rings at staggered angles, each with its own rotation speed
function Rings() {
  const r1 = useRef()
  const r2 = useRef()
  const r3 = useRef()

  useFrame((_, delta) => {
    if (r1.current) r1.current.rotation.z += delta * 0.28
    if (r2.current) r2.current.rotation.x += delta * 0.19
    if (r3.current) { r3.current.rotation.y += delta * 0.14; r3.current.rotation.z -= delta * 0.09 }
  })

  return (
    <>
      <mesh ref={r1} rotation={[Math.PI / 2.5, 0, 0]}>
        <torusGeometry args={[2.42, 0.011, 8, 200]} />
        <meshBasicMaterial color="#00e5ff" transparent opacity={0.65} />
      </mesh>
      <mesh ref={r2} rotation={[0, Math.PI / 4, Math.PI / 5]}>
        <torusGeometry args={[2.58, 0.007, 8, 200]} />
        <meshBasicMaterial color="#7928ca" transparent opacity={0.42} />
      </mesh>
      <mesh ref={r3} rotation={[Math.PI / 3, Math.PI / 6, 0]}>
        <torusGeometry args={[2.72, 0.005, 8, 200]} />
        <meshBasicMaterial color="#00e5ff" transparent opacity={0.22} />
      </mesh>
    </>
  )
}

export default function FaceModel() {
  const groupRef = useRef()
  const { mouse } = useThree()

  useFrame((_, delta) => {
    if (!groupRef.current) return
    // Continuous 360° Y rotation for the "360 degree" effect
    groupRef.current.rotation.y += delta * 0.22
    // Mouse tilt on X axis only (subtle parallax)
    groupRef.current.rotation.x += (-mouse.y * 0.28 - groupRef.current.rotation.x) * 0.04
  })

  return (
    <group ref={groupRef}>
      <AnimatedSphere />
      <WireframeSphere />
      <Particles />
      <Rings />
    </group>
  )
}
