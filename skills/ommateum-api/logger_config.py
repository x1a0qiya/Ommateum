"""
Ommateum API — 统一日志与错误存储系统

提供:
  - 滚动文件日志 (app.log / error.log)
  - 结构化错误存储 (errors.json)
  - 请求追踪中间件 (x-request-id)
  - Flask request/response 自动日志
"""

import logging
import logging.handlers
import json
import os
import sys
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------- 路径 ----------
LOG_DIR = os.path.join(Path(__file__).resolve().parent.parent.parent, 'logs')
APP_LOG = os.path.join(LOG_DIR, 'app.log')
ERR_LOG = os.path.join(LOG_DIR, 'error.log')
ERR_STORE = os.path.join(LOG_DIR, 'errors.json')

os.makedirs(LOG_DIR, exist_ok=True)

# ---------- 线程安全的错误存储 ----------
_err_lock = threading.Lock()
_BACKUP_COUNT = 5
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB 轮转


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class JsonFormatter(logging.Formatter):
    """结构化 JSON 日志格式器"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': _now_iso(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'message': record.getMessage(),
        }
        # 注入自定义上下文（若有）
        for attr in ('request_id', 'client_ip', 'method', 'path', 'status_code', 'duration_ms'):
            val = getattr(record, attr, None)
            if val is not None:
                log_entry[attr] = val

        if record.exc_info and record.exc_info[1]:
            log_entry['exception'] = {
                'type': type(record.exc_info[1]).__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_entry, ensure_ascii=False)


# ---------- 全局 logger ----------
_app_logger = None


def get_logger(name: str = 'ommateum') -> logging.Logger:
    """获取已配置的 logger 实例"""
    global _app_logger
    if _app_logger is None:
        setup_logging()
    return logging.getLogger(name)


def setup_logging(name: str = 'ommateum', level: int = logging.INFO) -> logging.Logger:
    """
    初始化日志系统。

    每次启动时调用一次即可。
    - 控制台输出: 人类可读格式
    - app.log: JSON 结构化日志（所有级别）
    - error.log: JSON 结构化日志（仅 WARNING+）

    Returns:
        logging.Logger: 根 logger
    """
    global _app_logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()  # 避免重复添加

    # --- 控制台 handler（可读格式） ---
    console_h = logging.StreamHandler(sys.stdout)
    console_h.setLevel(level)
    console_fmt = logging.Formatter(
        '[%(asctime)s] %(levelname)-7s %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_h.setFormatter(console_fmt)
    logger.addHandler(console_h)

    # --- 文件 handler：app.log（滚动，所有级别，JSON） ---
    app_h = logging.handlers.RotatingFileHandler(
        APP_LOG, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding='utf-8'
    )
    app_h.setLevel(logging.DEBUG)
    app_h.setFormatter(JsonFormatter())
    logger.addHandler(app_h)

    # --- 文件 handler：error.log（滚动，WARNING+，JSON） ---
    err_h = logging.handlers.RotatingFileHandler(
        ERR_LOG, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding='utf-8'
    )
    err_h.setLevel(logging.WARNING)
    err_h.setFormatter(JsonFormatter())
    logger.addHandler(err_h)

    _app_logger = logger
    logger.info('Logging system initialized')
    return logger


# ================================================================
#  错误持久化存储
# ================================================================

def store_error(
    *,
    request_id: str | None = None,
    endpoint: str = '',
    method: str = '',
    client_ip: str = '',
    error_type: str = '',
    error_message: str = '',
    trace: str = '',
    request_body: str | None = None,
) -> None:
    """
    将错误记录持久化到 errors.json。

    所有参数均为关键字参数，按需传入。
    """
    entry = OrderedErrorEntry(
        timestamp=_now_iso(),
        request_id=request_id or '—',
        endpoint=endpoint,
        method=method,
        client_ip=client_ip,
        error_type=error_type,
        error_message=error_message,
        traceback=trace.split('\n') if trace else [],
    )
    if request_body:
        entry['request_body'] = request_body[:2000]  # 截断长请求体

    with _err_lock:
        errors = []
        if 'errors' in entry:
            del entry['errors']  # guard
        try:
            if os.path.exists(ERR_STORE) and os.path.getsize(ERR_STORE) > 0:
                with open(ERR_STORE, 'r', encoding='utf-8') as f:
                    errors = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            errors = []

        # errors.json 结构: { "errors": [...], "updated_at": "..." }
        if isinstance(errors, dict):
            lst = errors.get('errors', [])
        else:
            lst = errors if isinstance(errors, list) else []
            errors = {'errors': lst}

        lst.insert(0, entry)
        # 只保留最近 500 条
        if len(lst) > 500:
            lst = lst[:500]
        errors['errors'] = lst
        errors['updated_at'] = _now_iso()

        with open(ERR_STORE, 'w', encoding='utf-8') as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)


def OrderedErrorEntry(**kwargs) -> dict:
    """保持字段顺序的结构化错误条目"""
    return {
        'timestamp': kwargs.get('timestamp', ''),
        'request_id': kwargs.get('request_id', ''),
        'endpoint': kwargs.get('endpoint', ''),
        'method': kwargs.get('method', ''),
        'client_ip': kwargs.get('client_ip', ''),
        'error_type': kwargs.get('error_type', ''),
        'error_message': kwargs.get('error_message', ''),
        'traceback': kwargs.get('traceback', []),
    }


def read_errors(limit: int = 50) -> dict:
    """读取错误存储"""
    try:
        if not os.path.exists(ERR_STORE) or os.path.getsize(ERR_STORE) == 0:
            return {'errors': [], 'total': 0}
        with open(ERR_STORE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        lst = data.get('errors', [])
        return {'errors': lst[:limit], 'total': len(lst)}
    except Exception:
        return {'errors': [], 'total': 0}


def clear_errors() -> None:
    """清空错误存储"""
    with _err_lock:
        with open(ERR_STORE, 'w', encoding='utf-8') as f:
            json.dump({'errors': [], 'updated_at': _now_iso()}, f)


# ================================================================
#  Flask 中间件辅助
# ================================================================

_REQUEST_ID_HEADER = 'X-Request-ID'


def generate_request_id() -> str:
    return uuid.uuid4().hex[:12]


def setup_flask_logging(app):
    """
    为 Flask app 注册请求日志中间件。

    在 before_request 中注入 request_id，
    在 after_request 中记录请求耗时与状态码。
    """
    import time as _time
    from flask import g, request as _req

    logger = get_logger('ommateum')

    @app.before_request
    def _before():
        g.start_time = _time.perf_counter()
        g.request_id = _req.headers.get(_REQUEST_ID_HEADER) or generate_request_id()
        # 存入 logging context
        _req.environ['ommateum_request_id'] = g.request_id

    @app.after_request
    def _after(response):
        duration = round((_time.perf_counter() - g.get('start_time', 0)) * 1000, 2)
        rid = g.get('request_id', '—')
        client_ip = _req.headers.get('X-Forwarded-For', _req.remote_addr or '—')
        status = response.status_code

        # 注入响应头方便前端追踪
        response.headers[_REQUEST_ID_HEADER] = rid

        extra = {
            'request_id': rid,
            'client_ip': client_ip,
            'method': _req.method,
            'path': _req.path,
            'status_code': status,
            'duration_ms': duration,
        }

        if 200 <= status < 400:
            logger.info(
                '%s %s → %d  (%s ms)',
                _req.method, _req.path, status, duration,
                extra=extra,
            )
        elif 400 <= status < 500:
            logger.warning(
                '%s %s → %d  (%s ms)',
                _req.method, _req.path, status, duration,
                extra=extra,
            )
        else:
            logger.error(
                '%s %s → %d  (%s ms)',
                _req.method, _req.path, status, duration,
                extra=extra,
            )
        return response

    logger.info('Flask request logging middleware registered')
