"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.readdirRecursive = readdirRecursive;
const fs_extra_1 = require("fs-extra");
const ignore_1 = require("ignore");
const _ = require("lodash");
const minimatch = require("minimatch");
const path_1 = require("path");
async function readdirRecursiveHelper(options) {
    const dirContents = (0, fs_extra_1.readdirSync)(options.path, { withFileTypes: true });
    const fullPaths = dirContents
        .filter((n) => !options.ignoreSymlinks || !n.isSymbolicLink())
        .map((n) => (0, path_1.join)(options.path, n.name));
    const filteredPaths = fullPaths.filter((p) => !options.filter(p));
    const filePromises = [];
    for (const p of filteredPaths) {
        const fstat = (0, fs_extra_1.statSync)(p);
        if (fstat.isFile()) {
            filePromises.push(Promise.resolve({ name: p, mode: fstat.mode }));
        }
        if (!fstat.isDirectory()) {
            continue;
        }
        if (options.maxDepth > 1) {
            filePromises.push(readdirRecursiveHelper({
                path: p,
                filter: options.filter,
                maxDepth: options.maxDepth - 1,
                ignoreSymlinks: options.ignoreSymlinks,
            }));
        }
    }
    const files = await Promise.all(filePromises);
    let flatFiles = _.flattenDeep(files);
    flatFiles = flatFiles.filter((f) => f !== null);
    return flatFiles;
}
async function readdirRecursive(options) {
    const mmopts = { matchBase: true, dot: true };
    const rules = (options.ignore || []).map((glob) => {
        return (p) => minimatch(p, glob, mmopts);
    });
    const gitIgnoreRules = (0, ignore_1.default)()
        .add(options.ignore || [])
        .createFilter();
    const filter = (t) => {
        if (options.isGitIgnore) {
            return !gitIgnoreRules((0, path_1.relative)(options.path, t));
        }
        return rules.some((rule) => {
            return rule(t);
        });
    };
    const maxDepth = options.maxDepth && options.maxDepth > 0 ? options.maxDepth : Infinity;
    return await readdirRecursiveHelper({
        path: options.path,
        filter: filter,
        maxDepth,
        ignoreSymlinks: !!options.ignoreSymlinks,
    });
}
