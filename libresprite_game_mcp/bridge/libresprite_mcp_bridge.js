// LibreSprite Game MCP Bridge Script
// Connects LibreSprite GUI with AI assistants for real-time game asset creation.
// Copyright (C) 2026 Antigravity / DeepMind

const MCP_ENDPOINT = "http://127.0.0.1:64823";

var mcpBridge = {
    connected: false,
    pollKey: "mcp_poll",
    resultKey: "mcp_result",
    dialog: null,

    init: function() {
        var self = this;
        // Show status dialog
        this.dialog = app.createDialog("mcpBridgeDialog");
        this.dialog.title = "LibreSprite Game MCP";
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

        // Storage fetch to poll endpoint
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

        try {
            if (cmdType === "eval") {
                // Execute arbitrary JS inside transaction
                var res = null;
                app.transaction(function() {
                    res = eval(params.code);
                });
                self.sendResult({ status: "success", result: res });
            } else if (cmdType === "get_preview") {
                if (app.activeImage) {
                    var pngBase64 = app.activeImage.getPNGData();
                    self.sendResult({ status: "success", png_base64: pngBase64 });
                } else {
                    self.sendResult({ status: "error", error: "No active image in canvas" });
                }
            } else if (cmdType === "create_sprite") {
                var w = params.width || 16;
                var h = params.height || 16;
                app.command.NewFile({
                    width: w,
                    height: h,
                    colorMode: params.colorMode || "rgba",
                    background: "transparent"
                });
                self.sendResult({ status: "success", message: "Created new sprite " + w + "x" + h });
            } else if (cmdType === "save") {
                if (app.activeSprite) {
                    if (params.path) {
                        app.activeSprite.saveAs(params.path);
                    } else {
                        app.activeSprite.save();
                    }
                    self.sendResult({ status: "success", message: "Sprite saved" });
                } else {
                    self.sendResult({ status: "error", error: "No active sprite to save" });
                }
            } else {
                self.sendResult({ status: "error", error: "Unknown command type: " + cmdType });
            }
        } catch (ex) {
            self.sendResult({ status: "error", error: ex.toString() });
        }
    }
};

// Event handlers
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

        // Schedule next poll tick (approx 5-10 frames)
        if (mcpBridge.connected) {
            app.yield("mcp_next_tick", 6);
        }
    } else if (event === "mcp_next_tick") {
        mcpBridge.poll();
    }
}
