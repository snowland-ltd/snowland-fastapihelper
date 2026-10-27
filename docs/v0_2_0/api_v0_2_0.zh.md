# snowland-fastapihelper API 参考（v0.2.0）

本文档逐条描述 `snowland_fastapihelper` 的全部公开 API，包含**输入、输出与行为**。
以代码为准。

> 英文版：[api_v0_2_0.md](api_v0_2_0.md)

---

## 1. 统一响应 — `snowland_fastapihelper.response`

所有接口共用固定的 4 字段外包裹：

| 字段         | 类型 | 含义                                          |
|--------------|------|-----------------------------------------------|
| `successful` | bool | 成功为 `true`，失败为 `false`                 |
| `code`       | int  | 成功为 `0`；否则为 `astartool.common.ErrorCode` 值 |
| `message`    | str  | 可读描述（成功为 `"ok"`）                      |
| `data`       | any  | 业务载荷；失败为 `null`                        |

`code` 取值来自 `astartool.common.ErrorCode`。

### `ok(data=None, message="ok") -> dict`
构造成功（非列表）响应。
- **输入**：`data`（任意载荷）、`message`（字符串）。
- **输出**：`{"successful": True, "code": 0, "message": message, "data": data}`。

### `ok_list(items, total, page, page_size) -> dict`
构造成功（列表）响应。
- **输入**：`items`（列表）、`total`（匹配总数 int）、`page`（int）、`page_size`（int）。
- **输出**：`{"successful": True, "code": 0, "message": "ok", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}`。

### `fail(code, message, data=None) -> dict`
构造失败响应。
- **输入**：`code`（int）、`message`（str）、`data`（任意，默认 `None`）。
- **输出**：`{"successful": False, "code": code, "message": message, "data": data}`。

### `class Pagination`
保存解析后的分页参数。
- **构造**：`Pagination(page: int, page_size: int)`。
- **属性**：`page`（int，从 1 开始）、`page_size`（int）、`offset`（int = `(page-1)*page_size`）、`limit`（int，等于 `page_size`）。

### `pagination(page=Query(1,ge=1), page_size=Query(20,ge=1,le=200)) -> Pagination`
FastAPI 依赖项，解析并校验分页查询参数。
- **输入**：查询参数 `page`（>=1）、`page_size`（1..200）。
- **输出**：一个 `Pagination` 实例。

### `http_status_to_code(status_code: int) -> int`
将 HTTP 状态码映射为 `ErrorCode` 值（供异常处理器使用）。
- **输入**：`status_code`（int）。
- **输出**：int。映射：`400->1`、`401->3`、`403->10`、`404->9`、`409->5`、`423->6`、`429->8`、`>=500->99`、其余 `-1`。

### 常量
- `DEFAULT_PAGE_SIZE = 20`
- `MAX_PAGE_SIZE = 200`

---

## 2. 异常 — `snowland_fastapihelper.exceptions`

### `class BizError(Exception)`
业务异常：携带 `ErrorCode` 值与描述，由 `biz_error_handler` 转为统一响应。
- **构造**：`BizError(code: int = 1, message: str = "operation failed", data: Any = None)`。
- **属性**：`code`、`message`、`data`。

### 处理器（通过 `register_exception_handlers` 注册）
- `biz_error_handler(request, exc: BizError)` → `JSONResponse(200, fail(code, message, data))`。
- `http_exception_handler(request, exc: StarletteHTTPException)` → 经 `http_status_to_code` 映射状态码，返回 `JSONResponse(200, fail(...))`。
- `validation_exception_handler(request, exc: RequestValidationError)` → `JSONResponse(200, fail(2, "request validation failed", exc.errors()))`。
- `unhandled_exception_handler(request, exc: Exception)` → `JSONResponse(200, fail(99, "internal server error", None))`（兜底，不泄露堆栈）。

> 说明：所有处理器均返回 **HTTP 200** 与统一外包裹；成败由 `successful`/`code` 表达。

### `register_exception_handlers(app: FastAPI) -> None`
将上述所有处理器注册到 FastAPI 应用。

---

## 3. 应用工厂 — `snowland_fastapihelper.app`

### `create_app(*args, **kwargs) -> FastAPI`
创建 `FastAPI` 应用并装配统一异常处理器。
- **输入**：同 `FastAPI(...)`。
- **输出**：已注册异常处理器的 `FastAPI` 实例。

```python
from snowland_fastapihelper import create_app
app = create_app(title="My API")
```

---

## 4. 数据库抽象层 — `snowland_fastapihelper.database`

与具体 ORM 无关。业务层只依赖 `get_crud(model, session)`；具体 ORM（此处为
SQLAlchemy）以自注册后端形式提供。

### `class CRUDProtocol(ABC, Generic[ModelType])`
各后端必须实现的统一 CRUD 接口。

| 方法 | 输入 | 输出 |
|------|------|------|
| `create(**kwargs)` | 字段值 | 创建后的模型实例 |
| `get_by_uuid(uuid, *, include_deleted=False)` | uuid 字符串 | 实例或 `None` |
| `list(*, page=1, page_size=20, include_deleted=False, **filters)` | 分页 + 等值过滤 | `(items: 序列, total: int)` |
| `update(uuid, **kwargs)` | 待更新字段 | 更新后实例或 `None` |
| `soft_delete(uuid)` | uuid 字符串 | 标记为已删除返回 `True`，否则 `False` |
| `delete(uuid)` | uuid 字符串 | 物理删除返回 `True`，否则 `False` |

约定：
- `list` 返回 `(items, total)`，其中 `total` 为匹配总数。
- `get_by_uuid`/`list` 默认过滤软删除记录；`include_deleted=True` 强制包含。
- `soft_delete` 置逻辑删除标记；`delete` 为物理删除。

### `get_crud(model, session, *, backend=None) -> CRUDProtocol`
统一入口。默认按 `type(session)` 派发到对应后端；也可通过 `backend=` 显式指定后端名。
- **输入**：`model`（模型类）、`session`（ORM 会话）、`backend`（字符串，可选）。
- **输出**：`CRUDProtocol` 实例。
- **异常**：`TypeError`（无匹配 session 类型的后端）、`KeyError`（`backend=` 名未注册）。

### `register_backend(name, session_type, factory) -> None`
为某 ORM 后端注册 CRUD 工厂。`factory` 签名为 `(model, session) -> CRUDProtocol`。
- 后端自注册时使用（如 SQLAlchemy 在 import 时自动注册）。

### `class BackendRegistry`
保存 `session 类型 -> 工厂` 映射并负责派发。对外暴露全局实例 `registry`；
`get_crud`/`register_backend` 均作用于它。

---

## 5. SQLAlchemy 后端 — `snowland_fastapihelper.database.sqlalchemy`

*（可选依赖：`sqlalchemy`）* —— import 本子包即自动注册后端，`get_crud` 随后
会把 `AsyncSession` 派发到本实现。

### 模型 — `models.py`
- `class Base(DeclarativeBase)`：所有模型的声明基类。
- `class GUID(TypeDecorator)`：UUID 字段类型；PostgreSQL 用原生 UUID，其余库用 `CHAR(36)`。`gen_uuid()` 返回 UUID 字符串默认值。
- `class UuidMixin`：提供 `uuid`（唯一、索引化的业务主键）。
- `class TimestampMixin`：提供 `created_at`、`updated_at`（UTC、带时区）。
- `class TenantMixin`：提供 `tenant_id`（GUID，外键指向 `tenants.uuid`，已索引）。
- `class MerchantMixin`：提供 `merchant_id`（GUID，已索引；不建库级外键，由应用层保证）。
- `class SoftDeleteMixin`：提供 `is_deleted`（bool，默认 `False`）。

> 注意：`Base`/`UuidMixin` 仅暴露业务 `uuid`，**未声明数据库物理主键**。请在每个模型上自行定义 `id` 自增主键。

### CRUD — `crud.py`
- `class CRUD(CRUDProtocol, Generic[ModelType])`：绑定 SQLAlchemy `AsyncSession` 的异步 CRUD。实现全部 `CRUDProtocol` 方法；自动应用 `SoftDeleteMixin` 过滤；对未知过滤/更新字段抛 `AttributeError`，模型未继承 `SoftDeleteMixin` 时 `soft_delete` 抛 `TypeError`。

### 示例
```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from snowland_fastapihelper import (
    Base, UuidMixin, TimestampMixin, SoftDeleteMixin, get_crud,
)

class User(Base, UuidMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)

async def create_user(session: AsyncSession, name: str):
    return await get_crud(User, session).create(name=name)
```

---

## 6. 顶层导出 — `snowland_fastapihelper`

始终可用（无需 `sqlalchemy`）：
`ok`、`ok_list`、`fail`、`Pagination`、`pagination`、`DEFAULT_PAGE_SIZE`、
`MAX_PAGE_SIZE`、`BizError`、`register_exception_handlers`、`create_app`、
`CRUDProtocol`、`get_crud`、`register_backend`。

懒加载可用（首次访问时 import `sqlalchemy`）：
`Base`、`CRUD`、`GUID`、`gen_uuid`、`UuidMixin`、`TimestampMixin`、`TenantMixin`、
`MerchantMixin`、`SoftDeleteMixin`。

`auth` 与 `captcha` 特性位于子包 `snowland_fastapihelper.auth` 与
`snowland_fastapihelper.captcha`（见 §7、§8），不在顶层重新导出。

---

## 7. 身份与用户 — `snowland_fastapihelper.auth`

参照 `django.contrib.auth` 的设计：本包统管所有身份相关原语（用户类、无账户
虚拟用户、可替换用户模型），使验证码等其它特性只依赖身份契约、无需自行定义
用户类。这些都是**纯 dataclass、不依赖 ORM**，可与任意持久层（如
`database.sqlalchemy`）配合使用。

### `class AbstractBaseUser(ABC)`
所有身份都必须满足的最小契约。
- **抽象属性**：`identity_key: str` — 稳定且唯一的身份标识，用作身份绑定数据（验证码、令牌等）的存储命名空间。

### `class AbstractUser(AbstractBaseUser)`（dataclass）
真实用户账户的可复用基类。
- **字段**：`uuid: str`（业务主键，指向 `users.uuid`）、`username: Optional[str] = None`、`tenant_id: Optional[str] = None`（→ `tenants.uuid`，租户隔离）、`merchant_id: Optional[str] = None`（→ `merchants.uuid`，商户隔离）。
- **属性**：`identity_key` → `"user:{uuid}"`。
- **校验**：`__post_init__` 在 `uuid` 为空时抛 `ValueError`。

### `class User(AbstractUser)`
默认的具体用户模型。可用 `set_user_model()` 替换；`get_user_model()` 随后返回你的子类。

### `class VirtualUser(AbstractBaseUser)`（dataclass）
无账户身份，适用于没有真实账户的流程（如注册前的手机号）。
- **字段**：`identity_type: str`（如 `"phone"` / `"email"` / `"device"` / `"session"`）、`identity_value: str`（如 `"+8613800000000"`）、`tenant_id: Optional[str] = None`、`merchant_id: Optional[str] = None`。
- **属性**：`identity_key` → `"virtual:{type}:{value}"`。
- **校验**：`identity_type` 或 `identity_value` 为空时抛 `ValueError`。

### `get_user_model() -> Type[AbstractUser]`
返回当前生效的用户模型（默认 `User`；返回经 `set_user_model` 注册者）。

### `set_user_model(model: Type[AbstractUser]) -> None`
替换生效的用户模型。`model` 不是 `AbstractUser` 子类时抛 `TypeError`。

```python
from snowland_fastapihelper.auth import User, VirtualUser, get_user_model, set_user_model

user = User(uuid="u-1", merchant_id="m-1")
print(user.identity_key)            # "user:u-1"

virtual = VirtualUser(identity_type="phone", identity_value="+8613800000000")

set_user_model(User)                 # 也可注册自定义的 AbstractUser 子类
```

---

## 8. 验证码 — `snowland_fastapihelper.captcha`

与 ORM 无关的验证码服务。两个独立的时间窗口控制验证码的生命周期：

- `expire_seconds`：有效期，仅在窗口内验证可通过。
- `retain_seconds`：记录在缓存中的保留时长（须 `>= expire_seconds`）。过期之后的这段时间，正是用来区分「验证码已过期」与「从未生成」。

验证码由 `astartool.random.random_digit_string` 生成（基于 `SystemRandom`、
密码学安全），而非标准库伪随机 `random`。

### `class CaptchaConfig`（dataclass）
时间配置。
- **字段**：`expire_seconds: int = 300`、`retain_seconds: int = 900`、`code_length: int = 6`。
- **校验**（`ValueError`）：`expire_seconds > 0`、`retain_seconds >= expire_seconds`、`code_length > 0`。

### `class VerifyStatus(Enum)`
- `SUCCESS = "success"` — 记录存在、仍在有效期内且码匹配。
- `EXPIRED = "expired"` — 记录存在但已过有效期（仍在保留期内）。
- `NOT_FOUND = "not_found"` — 无任何记录：从未生成，或已过保留期被清除。
- `MISMATCH = "mismatch"` — 记录有效但提交的码不一致。

### `class CaptchaService`
为某身份签发与校验验证码。
- **构造**：`CaptchaService(cache: Optional[CacheBackend] = None, config: Optional[CaptchaConfig] = None, key_prefix: str = "captcha:")`。
  - `cache`：记录存储后端；默认 `get_cache("memory")`。
  - `config`：时间配置；默认 `CaptchaConfig()`。
  - `key_prefix`：每个缓存键的命名空间前缀。
- **`async generate(principal, *, code: Optional[str] = None, length: Optional[int] = None) -> str`**：签发新码，覆盖已有码。`code` 指定确切验证码（测试用）；`length` 覆盖 `config.code_length`。返回签发的码以便下发（短信 / 邮件 / …）。
- **`async verify(principal, code: str, *, consume: bool = True) -> VerifyStatus`**：校验。`consume=True`（默认）在成功时删除记录，使验证码一次性生效。
- **`async invalidate(principal) -> None`**：丢弃当前已签发的验证码。
- **`async remaining_seconds(principal) -> Optional[int]`**：距过期还剩的秒数；无记录为 `None`，已过期但仍保留时为 `0`。

### 缓存后端 — `backends.py`
- **`class CacheBackend(ABC)`**：异步接口 `set(key, value, ttl)`、`get(key) -> Optional[str]`、`delete(key)`、`exists(key) -> bool`。
- **`get_cache(name: str = "memory") -> CacheBackend`**：返回 `name` 注册的共享后端实例。
- **`register_cache(name, factory) -> None`**：注册后端工厂（用于自注册）。
- **`class CacheRegistry`**：`name → 实例` 映射；对外暴露全局实例 `registry`。

### `class MemoryCache(CacheBackend)` — `memory.py`
内置、进程内缓存（无外部依赖），默认后端。
- **构造**：`MemoryCache(sweep_interval: float = 60.0)`。守护线程每 `sweep_interval` 秒清理一次过期条目（`<= 0` 关闭后台清理，仅保留惰性过期）。
- 过期回收既是惰性的（`get`/`exists` 命中时删除），也是主动的（后台 sweep），因此「生成但未验证」的验证码不会泄漏内存。

### `class RedisCache(CacheBackend)` — `redis_cache.py` *（可选：`redis`）*
跨进程 / 跨 worker 共享。`set` 以 `ex=ttl` 写入，Redis 在服务端主动回收过期键
（active expiration），无需 sweeper。导入本模块即注册 `"redis"` 后端（读取
`REDIS_URL` 环境变量，默认 `redis://localhost:6379/0`）。

```python
from snowland_fastapihelper.auth import VirtualUser
from snowland_fastapihelper.captcha import CaptchaService, CaptchaConfig, VerifyStatus

service = CaptchaService(config=CaptchaConfig(expire_seconds=300, retain_seconds=900))
principal = VirtualUser(identity_type="phone", identity_value="+8613800000000")

code = await service.generate(principal)        # 签发并下发
status = await service.verify(principal, code)   # SUCCESS / MISMATCH / EXPIRED / NOT_FOUND
```
