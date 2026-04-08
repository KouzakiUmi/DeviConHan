#!/usr/bin/env node
/**
 * ASAR 命令行包装工具
 *
 * 将 ASAR CLI 转换为命令行接口，供 Python 脚本调用
 *
 * 使用方法：
 *   node asar_cli.mjs stat <asar_path> <file_path>
 *   node asar_cli.mjs extract-file <asar_path> <file_path>
 *   node asar_cli.mjs extract <asar_path> <dest_dir>
 *   node asar_cli.mjs pack <src_dir> <dest_file> [--unpack <pattern>]
 */

import { execFile } from 'child_process';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import util from 'util';
import crypto from 'crypto';

const execFileAsync = util.promisify(execFile);

// 调试模式标志
const DEBUG = process.env.DEBUG === '1';

/**
 * 记录调试日志
 */
function debugLog(...args) {
    if (DEBUG) {
        console.error('[DEBUG]', new Date().toISOString(), ...args);
    }
}

/**
 * 记录信息日志
 */
function infoLog(...args) {
    console.error('[INFO]', new Date().toISOString(), ...args);
}

/**
 * 记录警告日志
 */
function warnLog(...args) {
    console.error('[WARN]', new Date().toISOString(), ...args);
}

/**
 * 异步检查文件或目录是否存在
 */
async function fileExists(p) {
    try {
        await fs.promises.access(p);
        return true;
    } catch {
        return false;
    }
}

/**
 * 异步清理临时目录（带日志）
 */
async function cleanupTempDir(tempDir, operation) {
    if (tempDir && await fileExists(tempDir)) {
        try {
            // 在 Windows 上，防病毒软件可能会短暂锁定刚刚提取的文件
            // 使用 maxRetries 选项来重试删除
            await fs.promises.rm(tempDir, { 
                recursive: true, 
                force: true, 
                maxRetries: 10, 
                retryDelay: 300 
            });
            debugLog(`Cleaned up temp directory (${operation}): ${tempDir}`);
        } catch (cleanupErr) {
            warnLog(`Failed to cleanup temp directory (${operation}): ${cleanupErr.message}`);
        }
    }
}

// 获取当前脚本所在目录（处理 URL 编码和 Windows 路径）
function getScriptDir() {
    try {
        const url = import.meta.url;
        const pathname = fileURLToPath(url);
        const dir = dirname(pathname);
        return dir;
    } catch (e) {
        // 回退方法：使用 argv[1] 获取脚本路径
        // 在 PyInstaller 环境下，argv[1] 指向临时目录
        // 我们需要从 tools 目录向上查找
        const scriptPath = process.argv[1];
        if (scriptPath) {
            const scriptDir = dirname(scriptPath);
            // 检查是否在 tools 目录下
            if (scriptDir.endsWith('tools') || scriptDir.endsWith('tools\\')) {
                return scriptDir;
            }
            // 如果在 tools/tools 目录下，回退到父目录
            if (scriptDir.endsWith('tools\\tools') || scriptDir.endsWith('tools/tools')) {
                return dirname(scriptDir);
            }
        }
        throw new Error(`Failed to get script directory: ${e.message}`);
    }
}

// 尝试多种方法获取 node 可执行文件路径
async function findNodeExe(scriptDir) {
    // 方法1：使用 process.execPath（在 PyInstaller 打包后指向临时目录的 node.exe）
    if (process.platform === 'win32') {
        const execDir = path.dirname(process.execPath);
        const nodeExePath = path.join(execDir, 'tools', 'node.exe');
        if (await fileExists(nodeExePath)) {
            return nodeExePath;
        }
        // 方法2：在脚本同目录下查找 node.exe
        const scriptNodeExe = path.join(scriptDir, 'node.exe');
        if (await fileExists(scriptNodeExe)) {
            return scriptNodeExe;
        }
        // 方法3：尝试系统 node
        return 'node';
    }
    return 'node';
}

// 规范化路径（处理 Windows 反斜杠和前导斜杠问题）
function normalizePath(p) {
    if (!p) return p;
    // 使用 path.normalize 让 Node 自动处理不同系统的路径分隔符
    // 移除不必要的前缀如 / 或 \，但不能破坏绝对路径
    return path.normalize(p);
}

/**
 * 显示使用帮助
 */
function showUsage() {
    console.error('Usage: node asar_cli.mjs <command> [arguments]');
    console.error('');
    console.error('Commands:');
    console.error('  stat <asar_path> <file_path>           Get file info from ASAR archive');
    console.error('  extract-file <asar_path> <file_path>   Extract single file from ASAR archive');
    console.error('  extract <asar_path> <dest_dir>          Extract entire ASAR archive');
    console.error('  pack <src_dir> <dest_file> [options]    Create ASAR archive from directory');
    console.error('');
    console.error('Pack options:');
    console.error('  --unpack <pattern>  Exclude files matching pattern from packing');
}

/**
 * 执行 ASAR CLI 命令
 */
async function runAsarCommand(nodeExe, asarCli, cliArgs) {
    try {
        const { stdout, stderr } = await execFileAsync(nodeExe, [asarCli, ...cliArgs], {
            encoding: 'utf8',
            windowsHide: true
        });
        return { stdout, stderr: stderr || '', exitCode: 0 };
    } catch (error) {
        return {
            stdout: error.stdout || '',
            stderr: error.stderr || error.message,
            exitCode: error.code !== undefined ? error.code : (error.status || 1)
        };
    }
}

/**
 * 解析 ASAR 列表输出
 */
function parseListOutput(output) {
    const files = [];
    const lines = output.trim().split('\n');
    for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed) {
            // 规范化路径：移除前导的反斜杠，转换反斜杠为正斜杠
            let normalized = trimmed.replace(/^\\+/, '').replace(/\\/g, '/');
            if (normalized) {
                files.push(normalized);
            }
        }
    }
    return files;
}

/**
 * 主函数
 */
async function main() {
    let scriptDir;
    try {
        scriptDir = getScriptDir();
    } catch (e) {
        console.error(JSON.stringify({
            success: false,
            error: `Failed to determine script directory: ${e.message}`,
            error_type: 'invalid_asar',
            debug: {
                argv: process.argv,
                platform: process.platform
            }
        }));
        process.exit(1);
    }

    // 找到正确的 node 可执行文件
    const nodeExe = await findNodeExe(scriptDir);

    // 在 PyInstaller 打包后，asarCli 需要相对于 _MEIPASS 目录
    // 使用 argv[1] 来确定脚本的实际位置
    let asarCli;
    if (process.argv[1] && await fileExists(process.argv[1])) {
        // 使用 argv[1] 的目录
        asarCli = path.join(path.dirname(process.argv[1]), 'bundled_asar', 'index.mjs');
    } else {
        // 回退到 scriptDir
        asarCli = path.join(scriptDir, 'bundled_asar', 'index.mjs');
    }

    const command = process.argv[2];
    const argsRaw = process.argv.slice(3);

    try {
        if (!command) {
            showUsage();
            process.exit(1);
        }

        switch (command) {
            case 'stat': {
                const [asarPathRaw, filePathRaw] = argsRaw;
                const asarPath = normalizePath(asarPathRaw);
                const filePath = normalizePath(filePathRaw);
                debugLog(`stat command: asar=${asarPath}, file=${filePath}`);
                
                if (!asarPath || !filePath) {
                    console.error(JSON.stringify({
                        success: false,
                        error: 'Missing required parameters',
                        error_type: 'invalid_args'
                    }));
                    process.exit(1);
                }
                
                const basename = path.basename(filePath);
                const tempDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), '__temp_stat_'));
                
                try {
                    // 使用 list 命令检查文件是否在包中
                    debugLog(`Checking if file exists in ASAR: ${asarPath}`);
                    const result = await runAsarCommand(nodeExe, asarCli, ['list', asarPath]);
                    
                    if (result.exitCode !== 0) {
                        let errorType = 'unknown';
                        const errorMsg = result.stderr.toLowerCase();
                        
                        if (errorMsg.includes('not found') || errorMsg.includes('no such file') || errorMsg.includes('does not exist')) {
                            errorType = 'file_not_found';
                        } else if (errorMsg.includes('corrupted') || errorMsg.includes('invalid') || errorMsg.includes('malformed')) {
                            errorType = 'file_corrupted';
                        } else if (errorMsg.includes('asar')) {
                            errorType = 'invalid_asar';
                        }
                        
                        console.error(JSON.stringify({
                            success: false,
                            error: result.stderr || 'Unknown error',
                            error_type: errorType
                        }));
                        process.exit(1);
                    }
                    
                    // 检查文件是否在列表中
                    const files = parseListOutput(result.stdout);
                    const normalizedFilePath = filePath.replace(/\\/g, '/');
                    const found = files.some(f => f === normalizedFilePath || f === '/' + normalizedFilePath);
                    
                    if (!found) {
                        console.error(JSON.stringify({
                            success: false,
                            error: `File not found in archive: ${filePath}`,
                            error_type: 'file_not_found'
                        }));
                        process.exit(1);
                    }
                    
                    // 在临时目录中运行 ASAR CLI
                    debugLog(`Extracting file for stat: ${filePath}`);
                    await execFileAsync(nodeExe, [asarCli, 'extract-file', asarPath, filePath], {
                        cwd: tempDir,
                        encoding: 'utf8',
                        windowsHide: true
                    });
                    
                    const outputFile = path.join(tempDir, basename);
                    if (await fileExists(outputFile)) {
                        const stats = await fs.promises.stat(outputFile);
                        debugLog(`File stat: ${outputFile}, size=${stats.size}`);
                        
                        // 清理临时目录
                        await cleanupTempDir(tempDir, 'stat-complete');
                        
                        // 返回与 Python 代码期望格式一致的响应
                        console.log(JSON.stringify({
                            success: true,
                            size: stats.size,
                            offset: 0,
                            executable: false,
                            mtime: null,
                            atime: null
                        }));
                    } else {
                        await cleanupTempDir(tempDir, 'stat-fail');
                        console.error(JSON.stringify({
                            success: false,
                            error: 'Failed to extract file to temp directory',
                            error_type: 'unknown'
                        }));
                        process.exit(1);
                    }
                } catch (error) {
                    await cleanupTempDir(tempDir, 'stat-error');
                    
                    console.error(JSON.stringify({
                        success: false,
                        error: error.message,
                        error_type: 'unknown'
                    }));
                    process.exit(1);
                }
                break;
            }
            
            case 'extract-file': {
                const [asarPathRaw, filePathRaw] = argsRaw;
                const asarPath = normalizePath(asarPathRaw);
                const filePath = normalizePath(filePathRaw);
                debugLog(`extract-file command: asar=${asarPath}, file=${filePath}`);
                
                if (!asarPath || !filePath) {
                    console.error(JSON.stringify({
                        success: false,
                        error: 'Missing required parameters',
                        error_type: 'invalid_args'
                    }));
                    process.exit(1);
                }
                
                const basename = path.basename(filePath);
                const tempDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), '__temp_extract_'));
                
                try {
                    // 在临时目录中运行 ASAR CLI
                    debugLog(`Extracting file: ${asarPath} -> ${filePath}`);
                    await execFileAsync(nodeExe, [asarCli, 'extract-file', asarPath, filePath], {
                        cwd: tempDir,
                        encoding: 'utf8',
                        windowsHide: true
                    });
                    debugLog('File extracted successfully');
                    
                    // 读取提取的文件
                    const outputFile = path.join(tempDir, basename);
                    if (await fileExists(outputFile)) {
                        const content = await fs.promises.readFile(outputFile, 'utf8');
                        // 清理临时目录
                        await cleanupTempDir(tempDir, 'extract-complete');
                        console.log(content);
                    } else {
                        await cleanupTempDir(tempDir, 'extract-fail');
                        console.error(JSON.stringify({
                            success: false,
                            error: 'Failed to extract file',
                            error_type: 'unknown'
                        }));
                        process.exit(1);
                    }
                } catch (error) {
                    await cleanupTempDir(tempDir, 'extract-error');
                    
                    let errorType = 'unknown';
                    const errorMsg = (error.stderr || error.message || '').toLowerCase();
                    
                    if (errorMsg.includes('not found') || errorMsg.includes('no such file') || errorMsg.includes('does not exist')) {
                        errorType = 'file_not_found';
                    } else if (errorMsg.includes('corrupted') || errorMsg.includes('invalid') || errorMsg.includes('malformed')) {
                        errorType = 'file_corrupted';
                    } else if (errorMsg.includes('asar')) {
                        errorType = 'invalid_asar';
                    }
                    
                    console.error(JSON.stringify({
                        success: false,
                        error: error.stderr || error.message || 'Unknown error',
                        error_type: errorType
                    }));
                    process.exit(1);
                }
                break;
            }
            
            case 'hash-file': {
                const [asarPathRaw, filePathRaw] = argsRaw;
                const asarPath = normalizePath(asarPathRaw);
                const filePath = normalizePath(filePathRaw);
                debugLog(`hash-file command: asar=${asarPath}, file=${filePath}`);
                
                if (!asarPath || !filePath) {
                    console.error(JSON.stringify({
                        success: false,
                        error: 'Missing required parameters',
                        error_type: 'invalid_args'
                    }));
                    process.exit(1);
                }
                
                const basename = path.basename(filePath);
                const tempDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), '__temp_hash_'));
                
                try {
                    // 在临时目录中运行 ASAR CLI 提取文件
                    debugLog(`Extracting file for hash: ${asarPath} -> ${filePath}`);
                    await execFileAsync(nodeExe, [asarCli, 'extract-file', asarPath, filePath], {
                        cwd: tempDir,
                        encoding: 'utf8',
                        windowsHide: true
                    });
                    
                    const outputFile = path.join(tempDir, basename);
                    if (await fileExists(outputFile)) {
                        const fileBuffer = await fs.promises.readFile(outputFile);
                        const hash = crypto.createHash('sha256').update(fileBuffer).digest('hex');
                        
                        // 清理临时目录
                        await cleanupTempDir(tempDir, 'hash-complete');
                        console.log(JSON.stringify({ success: true, hash: hash }));
                    } else {
                        await cleanupTempDir(tempDir, 'hash-fail');
                        console.error(JSON.stringify({
                            success: false,
                            error: 'Failed to extract file',
                            error_type: 'file_not_found'
                        }));
                        process.exit(1);
                    }
                } catch (error) {
                    await cleanupTempDir(tempDir, 'hash-error');
                    
                    let errorType = 'unknown';
                    const errorMsg = (error.stderr || error.message || '').toLowerCase();
                    
                    if (errorMsg.includes('not found') || errorMsg.includes('no such file') || errorMsg.includes('does not exist')) {
                        errorType = 'file_not_found';
                    } else if (errorMsg.includes('corrupted') || errorMsg.includes('invalid') || errorMsg.includes('malformed')) {
                        errorType = 'file_corrupted';
                    } else if (errorMsg.includes('asar')) {
                        errorType = 'invalid_asar';
                    }
                    
                    console.error(JSON.stringify({
                        success: false,
                        error: error.stderr || error.message || 'Unknown error',
                        error_type: errorType
                    }));
                    process.exit(1);
                }
                break;
            }

            case 'extract': {
                const [asarPathRaw, destDirRaw] = argsRaw;
                const asarPath = normalizePath(asarPathRaw);
                const destDir = normalizePath(destDirRaw);
                debugLog(`extract command: asar=${asarPath}, dest=${destDir}`);
                
                if (!asarPath || !destDir) {
                    console.error(JSON.stringify({
                        success: false,
                        error: 'Missing required parameters',
                        error_type: 'invalid_args'
                    }));
                    process.exit(1);
                }
                
                try {
                    // 确保目标目录存在
                    if (!(await fileExists(destDir))) {
                        await fs.promises.mkdir(destDir, { recursive: true });
                        debugLog(`Created destination directory: ${destDir}`);
                    }
                    
                    // 使用 extract 命令
                    infoLog(`Extracting ASAR: ${asarPath} -> ${destDir}`);
                    const result = await runAsarCommand(nodeExe, asarCli, ['extract', asarPath, destDir]);
                    
                    if (result.exitCode !== 0) {
                        let errorType = 'unknown';
                        const errorMsg = result.stderr.toLowerCase();
                        
                        if (errorMsg.includes('not found') || errorMsg.includes('no such file') || errorMsg.includes('does not exist')) {
                            errorType = 'file_not_found';
                        } else if (errorMsg.includes('corrupted') || errorMsg.includes('invalid') || errorMsg.includes('malformed')) {
                            errorType = 'file_corrupted';
                        } else if (errorMsg.includes('asar')) {
                            errorType = 'invalid_asar';
                        }
                        
                        console.error(JSON.stringify({
                            success: false,
                            error: result.stderr || 'Unknown error',
                            error_type: errorType
                        }));
                        process.exit(1);
                    }
                    
                    infoLog('ASAR extraction completed successfully');
                    console.log('SUCCESS');
                } catch (error) {
                    console.error(JSON.stringify({
                        success: false,
                        error: error.message,
                        error_type: 'unknown'
                    }));
                    process.exit(1);
                }
                break;
            }
            
            case 'pack': {
                const srcDirRaw = argsRaw[0];
                const destFileRaw = argsRaw[1];
                const optionsArgs = argsRaw.slice(2);
                
                const srcDir = normalizePath(srcDirRaw);
                const destFile = normalizePath(destFileRaw);
                debugLog(`pack command: src=${srcDir}, dest=${destFile}`);
                
                if (!srcDir || !destFile) {
                    console.error(JSON.stringify({
                        success: false,
                        error: 'Missing required parameters',
                        error_type: 'invalid_args'
                    }));
                    process.exit(1);
                }
                
                try {
                    // 确保目标目录存在
                    const destDir = path.dirname(destFile);
                    if (destDir && !(await fileExists(destDir))) {
                        await fs.promises.mkdir(destDir, { recursive: true });
                        debugLog(`Created destination directory: ${destDir}`);
                    }
                    
                    // 构建 CLI 参数
                    const cliArgs = ['pack', srcDir, destFile];
                    
                    // 处理选项 (--unpack, --unpack-dir 等)
                    let i = 0;
                    while (i < optionsArgs.length) {
                        if (optionsArgs[i].startsWith('--')) {
                            cliArgs.push(optionsArgs[i]);
                            // 检查下一个参数是否也是值（非选项）
                            if (i + 1 < optionsArgs.length && !optionsArgs[i + 1].startsWith('--')) {
                                cliArgs.push(optionsArgs[i + 1]);
                                i++;
                            }
                        }
                        i++;
                    }
                    
                    // 使用子进程调用 ASAR CLI
                    infoLog(`Packing ASAR: ${srcDir} -> ${destFile}`);
                    const result = await runAsarCommand(nodeExe, asarCli, cliArgs);
                    
                    if (result.exitCode !== 0) {
                        let errorType = 'unknown';
                        const errorMsg = (result.stderr || '').toLowerCase();
                        
                        if (errorMsg.includes('not found') || errorMsg.includes('no such file') || errorMsg.includes('does not exist')) {
                            errorType = 'file_not_found';
                        } else if (errorMsg.includes('corrupted') || errorMsg.includes('invalid') || errorMsg.includes('malformed')) {
                            errorType = 'file_corrupted';
                        } else if (errorMsg.includes('asar')) {
                            errorType = 'invalid_asar';
                        } else if (errorMsg.includes('permission') || errorMsg.includes('access')) {
                            errorType = 'permission_error';
                        }
                        
                        console.error(JSON.stringify({
                            success: false,
                            error: result.stderr || 'Unknown error',
                            error_type: errorType
                        }));
                        process.exit(1);
                    }
                    
                    infoLog('ASAR packing completed successfully');
                    console.log('SUCCESS');
                } catch (error) {
                    console.error(JSON.stringify({
                        success: false,
                        error: error.message,
                        error_type: 'unknown'
                    }));
                    process.exit(1);
                }
                break;
            }
            
            case 'list': {
                const asarPathRaw = argsRaw[0];
                const asarPath = normalizePath(asarPathRaw);
                debugLog(`list command: asar=${asarPath}`);
                
                if (!asarPath) {
                    console.error(JSON.stringify({
                        success: false,
                        error: 'Missing required parameters',
                        error_type: 'invalid_args'
                    }));
                    process.exit(1);
                }
                
                try {
                    const result = await runAsarCommand(nodeExe, asarCli, ['list', asarPath]);
                    
                    if (result.exitCode !== 0) {
                        let errorType = 'unknown';
                        const errorMsg = result.stderr.toLowerCase();
                        
                        if (errorMsg.includes('not found') || errorMsg.includes('no such file') || errorMsg.includes('does not exist')) {
                            errorType = 'file_not_found';
                        } else if (errorMsg.includes('corrupted') || errorMsg.includes('invalid') || errorMsg.includes('malformed')) {
                            errorType = 'file_corrupted';
                        } else if (errorMsg.includes('asar')) {
                            errorType = 'invalid_asar';
                        }
                        
                        console.error(JSON.stringify({
                            success: false,
                            error: result.stderr || 'Unknown error',
                            error_type: errorType
                        }));
                        process.exit(1);
                    }
                    
                    const files = parseListOutput(result.stdout);
                    debugLog(`Listed ${files.length} files from ASAR`);
                    console.log(JSON.stringify({
                        success: true,
                        files: files
                    }));
                } catch (error) {
                    console.error(JSON.stringify({
                        success: false,
                        error: error.message,
                        error_type: 'unknown'
                    }));
                    process.exit(1);
                }
                break;
            }
            
            default:
                console.error(`Error: Unknown command: ${command}`);
                showUsage();
                process.exit(1);
        }
        
        process.exit(0);
        
    } catch (error) {
        console.error(JSON.stringify({ 
            success: false, 
            error: error.message 
        }));
        process.exit(1);
    }
}

main();
