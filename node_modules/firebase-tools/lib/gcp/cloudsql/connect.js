"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.execute = execute;
exports.executeSqlCmdsAsIamUser = executeSqlCmdsAsIamUser;
exports.executeSqlCmdsAsSuperUser = executeSqlCmdsAsSuperUser;
exports.getDataConnectP4SA = getDataConnectP4SA;
exports.getIAMUser = getIAMUser;
exports.setupIAMUsers = setupIAMUsers;
exports.toDatabaseUser = toDatabaseUser;
const pg = require("pg");
const cloud_sql_connector_1 = require("@google-cloud/cloud-sql-connector");
const requireAuth_1 = require("../../requireAuth");
const projectUtils_1 = require("../../projectUtils");
const api_1 = require("../../api");
const cloudSqlAdminClient = require("./cloudsqladmin");
const utils = require("../../utils");
const logger_1 = require("../../logger");
const error_1 = require("../../error");
const fbToolsAuthClient_1 = require("./fbToolsAuthClient");
async function execute(sqlStatements, opts) {
    const logFn = opts.silent ? logger_1.logger.debug : logger_1.logger.info;
    const instance = await cloudSqlAdminClient.getInstance(opts.projectId, opts.instanceId);
    const user = await cloudSqlAdminClient.getUser(opts.projectId, opts.instanceId, opts.username);
    const connectionName = instance.connectionName;
    if (!connectionName) {
        throw new error_1.FirebaseError(`Could not get instance connection string for ${opts.instanceId}:${opts.databaseId}`);
    }
    let connector;
    let authType;
    switch (user.type) {
        case "CLOUD_IAM_USER": {
            connector = new cloud_sql_connector_1.Connector({
                auth: new fbToolsAuthClient_1.FBToolsAuthClient(),
            });
            authType = cloud_sql_connector_1.AuthTypes.IAM;
            break;
        }
        case "CLOUD_IAM_SERVICE_ACCOUNT": {
            connector = new cloud_sql_connector_1.Connector();
            authType = cloud_sql_connector_1.AuthTypes.IAM;
            break;
        }
        default: {
            if (!opts.password) {
                throw new error_1.FirebaseError(`Cannot connect as BUILT_IN user without a password.`);
            }
            connector = new cloud_sql_connector_1.Connector({
                auth: new fbToolsAuthClient_1.FBToolsAuthClient(),
            });
            authType = cloud_sql_connector_1.AuthTypes.PASSWORD;
            break;
        }
    }
    const connectionOpts = {
        instanceConnectionName: connectionName,
        ipType: instance.ipAddresses.some((ip) => ip.type === "PRIMARY")
            ? cloud_sql_connector_1.IpAddressTypes.PUBLIC
            : cloud_sql_connector_1.IpAddressTypes.PRIVATE,
        authType: authType,
    };
    const pool = new pg.Pool({
        ...(await connector.getOptions(connectionOpts)),
        password: opts.password,
        user: opts.username,
        database: opts.databaseId,
    });
    const cleanUpFn = async () => {
        conn.release();
        await pool.end();
        connector.close();
    };
    const conn = await pool.connect();
    const results = [];
    logFn(`Logged in as ${opts.username}`);
    if (opts.transaction) {
        sqlStatements.unshift("BEGIN;");
        sqlStatements.push("COMMIT;");
    }
    for (const s of sqlStatements) {
        logFn(`> ${s}`);
        try {
            results.push(await conn.query(s));
        }
        catch (err) {
            logFn(`Rolling back transaction due to error ${err}}`);
            await conn.query("ROLLBACK;");
            await cleanUpFn();
            throw new error_1.FirebaseError(`Error executing ${err}`);
        }
    }
    await cleanUpFn();
    logFn(``);
    return results;
}
async function executeSqlCmdsAsIamUser(options, instanceId, databaseId, cmds, silent = false, transaction = false) {
    const projectId = (0, projectUtils_1.needProjectId)(options);
    const { user: iamUser } = await getIAMUser(options);
    return await execute(cmds, {
        projectId,
        instanceId,
        databaseId,
        username: iamUser,
        silent: silent,
        transaction: transaction,
    });
}
async function executeSqlCmdsAsSuperUser(options, instanceId, databaseId, cmds, silent = false, transaction = false) {
    const projectId = (0, projectUtils_1.needProjectId)(options);
    const superuser = "firebasesuperuser";
    const temporaryPassword = utils.generatePassword(20);
    await cloudSqlAdminClient.createUser(projectId, instanceId, "BUILT_IN", superuser, temporaryPassword);
    return await execute([`SET ROLE = '${superuser}'`, ...cmds], {
        projectId,
        instanceId,
        databaseId,
        username: superuser,
        password: temporaryPassword,
        silent: silent,
        transaction: transaction,
    });
}
function getDataConnectP4SA(projectNumber) {
    return `service-${projectNumber}@${(0, api_1.dataconnectP4SADomain)()}`;
}
async function getIAMUser(options) {
    const account = await (0, requireAuth_1.requireAuth)(options);
    if (!account) {
        throw new error_1.FirebaseError("No account to set up! Run `firebase login` or set Application Default Credentials");
    }
    return toDatabaseUser(account);
}
async function setupIAMUsers(instanceId, options) {
    const projectId = (0, projectUtils_1.needProjectId)(options);
    const { user, mode } = await getIAMUser(options);
    await cloudSqlAdminClient.createUser(projectId, instanceId, mode, user);
    const projectNumber = await (0, projectUtils_1.needProjectNumber)(options);
    const { user: fdcP4SAUser, mode: fdcP4SAmode } = toDatabaseUser(getDataConnectP4SA(projectNumber));
    await cloudSqlAdminClient.createUser(projectId, instanceId, fdcP4SAmode, fdcP4SAUser);
    return user;
}
function toDatabaseUser(account) {
    let mode = "CLOUD_IAM_USER";
    let user = account;
    if (account.endsWith(".gserviceaccount.com")) {
        user = account.replace(".gserviceaccount.com", "");
        mode = "CLOUD_IAM_SERVICE_ACCOUNT";
    }
    return { user, mode };
}
