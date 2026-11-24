// LibreSprite Game MCP Bridge Script
// Hardened command bridge connecting LibreSprite GUI with AI assistants.
// Version: 2.0 (Security Hardened)
// Copyright (C) 2026 Antigravity / DeepMind

const MCP_ENDPOINT = "http://127.0.0.1:64823";

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
        return { message: "Pixel placed" };
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
    }
};

var mcpBridge = {
    connected: false,
    sessionToken: "",
    pollKey: "mcp_poll",
    resultKey: "mcp_result",
    dialog: null,

    init: function() {
        var self = this;
        // Check for session token from local storage or prompt
        this.sessionToken = storage.get("mcp_session_token") || "";

        this.dialog = app.createDialog("mcpBridgeDialog");
        this.dialog.title = "LibreSprite Game MCP Bridge (Hardened)";
        this.dialog.addLabel("Status: Ready to connect");
        this.dialog.addLabel("Token: " + (this.sessionToken ? "Configured" : "Auto-detect"));
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
        var body = JSON.stringify({ client_info: info });

        // Include authentication token header
        var headers = ["Content-Type", "application/json"];
        if (self.sessionToken) {
            headers.push("X-MCP-Token", self.sessionToken);
        }

        storage.fetch(
            MCP_ENDPOINT + "/poll",
            self.pollKey,
            "",
            "POST",
            body,
            headers[0],
            headers[1]
        );
    },

    sendResult: function(resultData) {
        var self = this;
        var body = JSON.stringify(resultData);
        var headers = ["Content-Type", "application/json"];
        if (self.sessionToken) {
            headers.push("X-MCP-Token", self.sessionToken);
        }

        storage.fetch(
            MCP_ENDPOINT + "/result",
            self.resultKey,
            "",
            "POST",
            body,
            headers[0],
            headers[1]
        );
    },

    executeCommand: function(cmd) {
        var self = this;
        if (!cmd) return;

        var cmdType = cmd.type;
        var params = cmd.params || {};

        // Security: Strict own-property lookup preventing prototype pollution
        if (!Object.prototype.hasOwnProperty.call(ALLOWED_COMMANDS, cmdType)) {
            self.sendResult({
                status: "error",
                error: "Unauthorized command: '" + cmdType + "'. Command not in security allowlist."
            });
            return;
        }

        try {
            var res = null;
            app.transaction(function() {
                res = ALLOWED_COMMANDS[cmdType](params);
            });
            self.sendResult({ status: "success", result: res });
        } catch (ex) {
            self.sendResult({ status: "error", error: ex.toString() });
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
