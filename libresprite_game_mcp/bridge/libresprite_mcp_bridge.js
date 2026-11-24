// LibreSprite Game MCP Bridge Script
// Hardened command bridge connecting LibreSprite GUI with AI assistants.
// Version: 2.2 (Body-Only Authentication & Headless Test Support)
// Copyright (C) 2026 Antigravity / DeepMind

const MCP_ENDPOINT = "http://127.0.0.1:64823";
const SCRIPT_DOMAIN = "libresprite_mcp_bridge.js";

// Strict allowlist with parameter validation and boundary enforcement
const ALLOWED_COMMANDS = {
    create_canvas: function(params) {
        params = params || {};
        var w = Number(params.width) || 16;
        var h = Number(params.height) || 16;

        // Enforce boundary limits (1 to 2048)
        if (w < 1 || w > 2048 || h < 1 || h > 2048) {
            throw new Error("Invalid canvas dimensions: " + w + "x" + h + ". Allowed range: 1..2048");
        }

        var colorMode = params.colorMode === "indexed" ? "indexed" : "rgba";
        app.command.NewFile({
            width: Math.floor(w),
            height: Math.floor(h),
            colorMode: colorMode,
            background: "transparent"
        });
        return { message: "Canvas created " + w + "x" + h };
    },

    get_preview: function(params) {
        if (!app.activeImage) {
            throw new Error("No active image in canvas");
        }
        return { png_base64: app.activeImage.getPNGData() };
    },

    save_sprite: function(params) {
        if (!app.activeSprite) {
            throw new Error("No active sprite to save");
        }
        params = params || {};
        var savePath = params.path ? String(params.path) : null;

        if (savePath) {
            // Block path traversal in save path
            if (savePath.indexOf("..") !== -1) {
                throw new Error("Path traversal forbidden in save path: " + savePath);
            }
            app.activeSprite.saveAs(savePath);
        } else {
            app.activeSprite.save();
        }
        return { message: "Sprite saved successfully" };
    },

    put_pixel: function(params) {
        if (!app.activeImage) throw new Error("No active image");
        params = params || {};
        var x = Number(params.x);
        var y = Number(params.y);

        if (isNaN(x) || isNaN(y) || x < 0 || y < 0 || x >= app.activeImage.width || y >= app.activeImage.height) {
            throw new Error("Coordinates (" + x + ", " + y + ") out of image bounds.");
        }

        var r = Math.min(255, Math.max(0, Number(params.r) || 0));
        var g = Math.min(255, Math.max(0, Number(params.g) || 0));
        var b = Math.min(255, Math.max(0, Number(params.b) || 0));
        var a = params.a !== undefined ? Math.min(255, Math.max(0, Number(params.a))) : 255;

        var col = app.pixelColor;
        var c = col.rgba(r, g, b, a);
        app.activeImage.putPixel(Math.floor(x), Math.floor(y), c);

        // Verification: Read back written pixel directly from active image
        var readback = app.activeImage.getPixel(Math.floor(x), Math.floor(y));
        return {
            message: "Pixel placed",
            x: Math.floor(x),
            y: Math.floor(y),
            color: [r, g, b, a],
            pixel_value: readback,
            verified: (readback === c)
        };
    },

    draw_rect: function(params) {
        if (!app.activeImage) throw new Error("No active image");
        params = params || {};
        var rx = Math.floor(Number(params.x) || 0);
        var ry = Math.floor(Number(params.y) || 0);
        var rw = Math.floor(Number(params.w) || 1);
        var rh = Math.floor(Number(params.h) || 1);

        if (rw < 1 || rh < 1 || rw > 2048 || rh > 2048) {
            throw new Error("Invalid rectangle dimensions: " + rw + "x" + rh);
        }

        var r = Math.min(255, Math.max(0, Number(params.r) || 0));
        var g = Math.min(255, Math.max(0, Number(params.g) || 0));
        var b = Math.min(255, Math.max(0, Number(params.b) || 0));
        var a = params.a !== undefined ? Math.min(255, Math.max(0, Number(params.a))) : 255;

        var col = app.pixelColor;
        var c = col.rgba(r, g, b, a);

        var maxX = Math.min(app.activeImage.width, rx + rw);
        var maxY = Math.min(app.activeImage.height, ry + rh);

        for (var y = Math.max(0, ry); y < maxY; y++) {
            for (var x = Math.max(0, rx); x < maxX; x++) {
                app.activeImage.putPixel(x, y, c);
            }
        }
        return { message: "Rectangle drawn" };
    },

    clear_canvas: function(params) {
        if (!app.activeImage) throw new Error("No active image");
        var col = app.pixelColor;
        app.activeImage.clear(col.rgba(0, 0, 0, 0));
        return { message: "Canvas cleared" };
    },

    exit_session: function(params) {
        mcpBridge.stop();
        if (app.command && typeof app.command.Exit === "function") {
            app.command.Exit();
        }
        return { message: "Bridge session closed and application exited." };
    }
};

var mcpBridge = {
    connected: false,
    testMode: false,
    sessionToken: "",
    pollKey: "mcp_poll",
    resultKey: "mcp_result",
    dialog: null,

    init: function(options) {
        options = options || {};
        var self = this;

        // Auto-load session token from LibreSprite native storage using explicit domain
        if (typeof storage !== "undefined" && typeof storage.load === "function") {
            if (storage.load("session_token", SCRIPT_DOMAIN) || storage.load("session_token")) {
                this.sessionToken = storage.get("session_token", SCRIPT_DOMAIN) || storage.get("session_token") || "";
            }
            if (storage.load("test_mode", SCRIPT_DOMAIN) || storage.load("test_mode")) {
                this.testMode = (storage.get("test_mode", SCRIPT_DOMAIN) === "true") || (storage.get("test_mode") === "true");
            }
        }

        if (options.testMode) {
            this.testMode = true;
        }

        // Test Mode: Auto-connect immediately without showing blocking modal GUI dialog
        if (this.testMode) {
            this.start();
            return;
        }

        // Interactive GUI Mode: Present connection dialog
        this.dialog = app.createDialog("mcpBridgeDialog");
        this.dialog.title = "LibreSprite Game MCP Bridge (Hardened)";
        this.dialog.addLabel("Status: Ready to connect");
        var maskedToken = this.sessionToken ? (this.sessionToken.substring(0, 6) + "...[MASKED]") : "Not found";
        this.dialog.addLabel("Token: " + maskedToken);
        this.dialog.addButton("Connect", function() {
            self.start();
        });
        this.dialog.addButton("Close", function() {
            self.stop();
            self.dialog.close();
        });
        this.dialog.show();
    },

    start: function() {
        this.connected = true;
        this.poll();
    },

    stop: function() {
        this.connected = false;
    },

    getSpriteInfo: function() {
        if (!app.activeSprite) return null;
        var s = app.activeSprite;
        return {
            width: s.width,
            height: s.height,
            colorMode: s.colorMode,
            layerCount: s.layerCount,
            filename: s.filename
        };
    },

    poll: function() {
        if (!this.connected) return;
        var self = this;
        var info = this.getSpriteInfo();

        // Security: Token passed strictly in JSON body, never in URL query parameter
        var body = JSON.stringify({
            session_token: self.sessionToken,
            client_info: info
        });

        storage.fetch(
            MCP_ENDPOINT + "/poll",
            self.pollKey,
            "",
            "POST",
            body,
            "Content-Type",
            "application/json"
        );
    },

    sendResult: function(commandId, status, payload) {
        var self = this;
        var resultData = {
            session_token: self.sessionToken,
            command_id: commandId,
            status: status
        };
        if (status === "success") {
            resultData.result = payload;
        } else {
            resultData.error = payload;
        }

        // Security: Token passed strictly in JSON body, never in URL query parameter
        var body = JSON.stringify(resultData);

        storage.fetch(
            MCP_ENDPOINT + "/result",
            self.resultKey,
            "",
            "POST",
            body,
            "Content-Type",
            "application/json"
        );
    },

    executeCommand: function(cmd) {
        var self = this;
        if (!cmd) return;

        var commandId = cmd.command_id || null;
        var cmdType = cmd.type;
        var params = cmd.params || {};

        // Security: Strict own-property lookup preventing prototype pollution
        if (!Object.prototype.hasOwnProperty.call(ALLOWED_COMMANDS, cmdType)) {
            self.sendResult(
                commandId,
                "error",
                "Unauthorized command: '" + cmdType + "'. Command not in security allowlist."
            );
            return;
        }

        try {
            var res = null;
            if (typeof app.transaction === "function") {
                app.transaction(function() {
                    res = ALLOWED_COMMANDS[cmdType](params);
                });
            } else {
                res = ALLOWED_COMMANDS[cmdType](params);
            }
            self.sendResult(commandId, "success", res);
        } catch (ex) {
            self.sendResult(commandId, "error", ex.toString());
        }
    }
};

function onEvent(event) {
    if (event === "init") {
        mcpBridge.init();
    } else if (event === "mcp_poll_fetch") {
        var raw = storage.get(mcpBridge.pollKey);
        try {
            var data = JSON.parse(raw);
            if (data && data.command) {
                mcpBridge.executeCommand(data.command);
            }
        } catch(e) {}

        if (mcpBridge.connected) {
            app.yield("mcp_next_tick", 6);
        }
    } else if (event === "mcp_next_tick") {
        mcpBridge.poll();
    }
}
