// LibreSprite Game MCP Bridge Script
// Secure, allowlisted command bridge connecting LibreSprite GUI with AI assistants.
// Copyright (C) 2026 Antigravity / DeepMind

const MCP_ENDPOINT = "http://127.0.0.1:64823";

// Strict allowlist of permitted commands to prevent arbitrary code execution
const ALLOWED_COMMANDS = {
    create_canvas: function(params) {
        var w = params.width || 16;
        var h = params.height || 16;
        app.command.NewFile({
            width: w,
            height: h,
            colorMode: params.colorMode || "rgba",
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
        if (params.path) {
            app.activeSprite.saveAs(params.path);
        } else {
            app.activeSprite.save();
        }
        return { message: "Sprite saved successfully" };
    },

    put_pixel: function(params) {
        if (!app.activeImage) throw new Error("No active image");
        var col = app.pixelColor;
        var c = col.rgba(params.r, params.g, params.b, params.a !== undefined ? params.a : 255);
        app.activeImage.putPixel(params.x, params.y, c);
        return { message: "Pixel placed" };
    },

    draw_rect: function(params) {
        if (!app.activeImage) throw new Error("No active image");
        var col = app.pixelColor;
        var c = col.rgba(params.r, params.g, params.b, params.a !== undefined ? params.a : 255);
        var rx = params.x || 0;
        var ry = params.y || 0;
        var rw = params.w || 1;
        var rh = params.h || 1;
        for (var y = ry; y < ry + rh; y++) {
            for (var x = rx; x < rx + rw; x++) {
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
    pollKey: "mcp_poll",
    resultKey: "mcp_result",
    dialog: null,

    init: function() {
        var self = this;
        this.dialog = app.createDialog("mcpBridgeDialog");
        this.dialog.title = "LibreSprite Game MCP Bridge (Secure)";
        this.dialog.addLabel("Status: Ready to connect");
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

    sendResult: function(resultData) {
        var self = this;
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

        var cmdType = cmd.type;
        var params = cmd.params || {};

        if (!(cmdType in ALLOWED_COMMANDS)) {
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
