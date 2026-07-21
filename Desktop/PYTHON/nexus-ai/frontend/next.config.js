/** @type {import('next').NextConfig} */
const nextConfig = {
  // Produce a self-contained build artefact — dramatically shrinks the
  // production Docker image (no node_modules in the runtime stage).
  output: "standalone",
};

module.exports = nextConfig;
