"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ensureApis = ensureApis;
exports.ensureGIFApiTos = ensureGIFApiTos;
const api = require("../api");
const configstore_1 = require("../configstore");
const ensureApiEnabled_1 = require("../ensureApiEnabled");
const prefix = "dataconnect";
async function ensureApis(projectId, silent = false) {
    await Promise.all([
        (0, ensureApiEnabled_1.ensure)(projectId, api.dataconnectOrigin(), prefix, silent),
        (0, ensureApiEnabled_1.ensure)(projectId, api.cloudSQLAdminOrigin(), prefix, silent),
    ]);
}
async function ensureGIFApiTos(projectId) {
    if (configstore_1.configstore.get("gemini")) {
        await (0, ensureApiEnabled_1.ensure)(projectId, api.cloudAiCompanionOrigin(), "");
    }
    else {
        if (!(await (0, ensureApiEnabled_1.check)(projectId, api.cloudAiCompanionOrigin(), ""))) {
            return false;
        }
    }
    return true;
}
