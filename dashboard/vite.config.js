import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig(function (_a) {
    var mode = _a.mode;
    var env = loadEnv(mode, ".", "");
    var gateway = env.GATEWAY_PROXY_TARGET || "http://127.0.0.1:9000";
    return {
        plugins: [react()],
        server: {
            port: 3000,
            proxy: {
                "/api": {
                    target: gateway,
                    rewrite: function (path) { return path.replace(/^\/api/, ""); },
                },
            },
        },
    };
});
