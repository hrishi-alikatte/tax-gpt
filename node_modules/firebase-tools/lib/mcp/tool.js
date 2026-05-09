"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.tool = tool;
const zod_to_json_schema_1 = require("zod-to-json-schema");
const util_1 = require("./util");
const availability_1 = require("./util/availability");
function tool(feature, options, fn) {
    const { isAvailable, ...mcpOptions } = options;
    return {
        mcp: { ...mcpOptions, inputSchema: (0, util_1.cleanSchema)((0, zod_to_json_schema_1.zodToJsonSchema)(options.inputSchema)) },
        fn,
        isAvailable: (ctx) => {
            const isAvailableFunc = isAvailable || (0, availability_1.getDefaultFeatureAvailabilityCheck)(feature);
            return isAvailableFunc(ctx);
        },
    };
}
