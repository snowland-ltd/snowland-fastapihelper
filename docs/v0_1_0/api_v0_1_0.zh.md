# snowland-fastapihelper API 参考（v0.1.0）

本文档逐条描述 `snowland_fastapihelper` 的全部公开 API，包含**输入、输出与行为**。
以代码为准。

> 英文版：[api.md](api_v0_1_0.md)

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
