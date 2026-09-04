import vue from "@vitejs/plugin-vue";

export default {
  base: "./",
  plugins: [vue()],
  server: {
    port: 5173,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
};

