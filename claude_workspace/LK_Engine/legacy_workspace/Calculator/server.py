#!/usr/bin/env python3
"""
一键启动洛克王国分析工作台
  静态文件服务 + Python 引擎 API，合并在同一端口。

启动方式：
  python server.py          # 默认端口 5173
  python server.py 8080     # 自定义端口

浏览器访问 http://localhost:5173 即可使用。
"""
import os, sys, json, traceback, subprocess, signal, atexit

# ---- 路径设置 ----
CALC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CALC_DIR, '..', '..'))
ENGINE_CORE = os.path.join(PROJECT_ROOT, 'engine_core')

if not os.path.isdir(ENGINE_CORE):
    print(f'[错误] 引擎目录不存在: {ENGINE_CORE}')
    input('按回车键退出...')
    sys.exit(1)

# 让 Python 能找到 engine_core 下的模块
sys.path.insert(0, ENGINE_CORE)


# ---- 依赖检查：如果当前解释器缺 flask，自动安装 ----
try:
    from flask import Flask, send_from_directory, request, jsonify
except ImportError:
    print(f'[提示] 当前 Python ({sys.executable}) 缺少 Flask，正在自动安装 ...')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask'])
    from flask import Flask, send_from_directory, request, jsonify
    print('[提示] Flask 安装成功')

app = Flask(__name__, static_folder=None)  # 禁用默认 static，手动控制

# ---- 日志：让引擎模块的 WARNING 输出到终端 ----
import logging as _logging
_logging.basicConfig(level=_logging.WARNING,
                     format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

# ---- 全局错误处理：确保所有 400 都返回 JSON 而非 HTML ----
@app.errorhandler(400)
def _global_bad_request(e):
    _logging.getLogger('server').warning('400 BadRequest: %s', e.description)
    return jsonify({
        'error': f'请求格式错误: {e.description}',
        'hint': '请检查 JSON 请求体是否完整、格式是否正确',
    }), 400


# ---- 注册引擎 API 蓝图 ----
try:
    print('[启动] 正在加载引擎模块 ...')
    from api import engine_bp
    app.register_blueprint(engine_bp)
    print('[启动] 引擎模块加载完成')
except Exception as e:
    print(f'[错误] 引擎模块加载失败:')
    traceback.print_exc()
    input('按回车键退出...')
    sys.exit(1)


def _assert_required_routes():
    """启动时校验关键引擎接口是否已经正确注册。"""
    required = {
        '/api/analyze': 'POST',
        '/api/resolve': 'POST',
        '/api/next_states': 'POST',
        '/api/eval': 'POST',
        '/api/simulate': 'POST',
    }
    route_methods = {
        rule.rule: set(rule.methods or [])
        for rule in app.url_map.iter_rules()
    }
    missing = []
    for path, method in required.items():
        methods = route_methods.get(path, set())
        if method not in methods:
            missing.append(f'{path} [{method}]')
    if missing:
        raise RuntimeError('关键引擎路由未注册: ' + ', '.join(missing))


try:
    _assert_required_routes()
    print('[启动] 引擎关键路由校验通过')
except Exception:
    print('[错误] 引擎路由校验失败:')
    traceback.print_exc()
    input('按回车键退出...')
    sys.exit(1)

# ---- 队伍存档 API ----
DATA_FILE = os.path.join(CALC_DIR, 'Data', 'my_teams.json')
DATA_JS   = os.path.join(CALC_DIR, 'Data', 'my_teams.js')


@app.route('/api/save-teams', methods=['POST'])
def save_teams():
    try:
        data = request.json
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(DATA_JS, 'w', encoding='utf-8') as f:
            f.write('var _MY_TEAMS_RAW=' + json.dumps(data, ensure_ascii=False) + ';\n')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---- 静态文件服务 ----
@app.route('/')
def serve_index():
    return send_from_directory(CALC_DIR, 'index.html')


@app.route('/favicon.ico')
def serve_favicon():
    """返回空白 favicon，消除浏览器自动请求产生的 404 噪音。"""
    return app.response_class(
        response=b'\x00',
        status=200,
        mimetype='image/x-icon',
    )


@app.route('/<path:filename>')
def serve_static(filename):
    """静态文件回退：只在文件存在时返回，否则 404。"""
    filepath = os.path.join(CALC_DIR, filename)
    if os.path.isfile(filepath):
        return send_from_directory(CALC_DIR, filename)
    return f'Not found: {filename}', 404


# ---- 独立引擎子进程管理 ----
_ENGINE_API_PORT = 5000
_ENGINE_PID_FILE = os.path.join(CALC_DIR, '.engine_api.pid')
_engine_process = None


def _kill_pid(pid):
    """跨平台杀死指定 PID（Windows 用 taskkill /T 杀整棵进程树）。"""
    try:
        if sys.platform == 'win32':
            subprocess.call(
                ['taskkill', '/F', '/T', '/PID', str(pid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            os.kill(pid, 9)
    except Exception:
        pass


def _cleanup_stale_engine():
    """清理上次残留的 api.py 进程（通过 PID 文件追踪）。"""
    if not os.path.isfile(_ENGINE_PID_FILE):
        return
    try:
        with open(_ENGINE_PID_FILE, 'r') as f:
            old_pid = int(f.read().strip())
        _kill_pid(old_pid)
        print(f'[清理] 已终止上次残留的引擎进程 (PID={old_pid})')
    except Exception:
        pass
    finally:
        try:
            os.remove(_ENGINE_PID_FILE)
        except Exception:
            pass


def _is_port_listening(port, timeout=1.0):
    """检测端口是否正在监听。"""
    import socket
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=timeout):
            return True
    except Exception:
        return False


def _start_engine_subprocess():
    """启动 engine_core/api.py 独立引擎服务。"""
    global _engine_process
    api_script = os.path.join(ENGINE_CORE, 'api.py')
    if not os.path.isfile(api_script):
        print(f'[警告] 未找到独立引擎脚本: {api_script}，跳过启动')
        return False

    # 清理上次残留
    _cleanup_stale_engine()

    # 如果端口仍被占用，跳过启动
    if _is_port_listening(_ENGINE_API_PORT, timeout=0.5):
        print(f'[警告] 端口 {_ENGINE_API_PORT} 已被占用，跳过启动独立引擎')
        return False

    try:
        creation_flags = 0
        if sys.platform == 'win32':
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
        _engine_process = subprocess.Popen(
            [sys.executable, api_script],
            cwd=ENGINE_CORE,
            creationflags=creation_flags,
        )
        # 写 PID 文件，以便下次启动时清理残留
        try:
            with open(_ENGINE_PID_FILE, 'w') as f:
                f.write(str(_engine_process.pid))
        except Exception:
            pass

        # 等待 api.py 实际就绪（最多 15 秒）
        import time
        print(f'[启动] 正在等待独立引擎服务就绪 (PID={_engine_process.pid}) ...')
        for i in range(30):
            # 检查子进程是否已经退出（启动失败）
            if _engine_process.poll() is not None:
                print(f'[错误] 独立引擎服务启动后立即退出 (exit code={_engine_process.returncode})')
                _engine_process = None
                return False
            if _is_port_listening(_ENGINE_API_PORT, timeout=0.3):
                print(f'[启动] 独立引擎服务已就绪  http://localhost:{_ENGINE_API_PORT}')
                return True
            time.sleep(0.5)

        print(f'[警告] 独立引擎服务在 15 秒内未就绪，可能启动失败')
        return False
    except Exception as e:
        print(f'[警告] 独立引擎服务启动失败: {e}')
        return False


def _stop_engine_subprocess():
    """关闭独立引擎子进程并清理 PID 文件。"""
    global _engine_process
    if _engine_process is None:
        # 仍尝试通过 PID 文件清理（防止引用丢失时残留）
        _cleanup_stale_engine()
        return
    pid = _engine_process.pid
    try:
        _kill_pid(pid)
        _engine_process.wait(timeout=5)
    except Exception:
        pass
    print(f'[关闭] 独立引擎服务已停止 (PID={pid})')
    _engine_process = None
    try:
        os.remove(_ENGINE_PID_FILE)
    except Exception:
        pass


# ---- 入口 ----
if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5173

    # 启动独立引擎子进程，并注册退出时自动清理
    engine_ok = _start_engine_subprocess()
    atexit.register(_stop_engine_subprocess)

    def _exit_handler(*_args):
        _stop_engine_subprocess()
        sys.exit(0)

    signal.signal(signal.SIGINT, _exit_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, _exit_handler)

    print()
    print('=' * 50)
    print('  洛克王国分析工作台')
    print('=' * 50)
    print(f'  地址:         http://localhost:{port}')
    if engine_ok:
        print(f'  独立引擎 API: http://localhost:{_ENGINE_API_PORT}  ✓ 运行中')
    else:
        print(f'  独立引擎 API: http://localhost:{_ENGINE_API_PORT}  ✗ 未启动')
    print(f'  引擎 API:     /api/analyze, /api/resolve, /api/next_states, /api/eval, /api/simulate')
    print(f'  运行时控制台: /runtime-console')
    print(f'  队伍存档:     {DATA_FILE}')
    print('=' * 50)
    print()
    try:
        # use_reloader=False: 避免 reloader 子进程重复初始化引擎导致崩溃
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except OSError as e:
        if 'Address already in use' in str(e) or '10048' in str(e):
            print(f'\n[错误] 端口 {port} 已被占用，请换一个端口: python server.py {port + 1}')
        else:
            print(f'\n[错误] 服务器启动失败: {e}')
        input('按回车键退出...')
    except Exception as e:
        print(f'\n[错误] 服务器异常退出: {e}')
        traceback.print_exc()
        input('按回车键退出...')
    finally:
        _stop_engine_subprocess()
