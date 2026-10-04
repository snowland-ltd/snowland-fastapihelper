# snowland-fastapihelper

FastAPI 开发辅助库，提供开箱即用的**统一响应格式、分页依赖、业务异常与异常处理器、应用工厂**，以及基于 **SQLAlchemy 2.0** 的**通用模型基类 / 混入**与**异步 CRUD 助手**。

## 特性

- **统一响应**：所有接口返回固定 4 字段结构（`successful` / `code` / `message` / `data`），成功 `code=0`，失败由异常处理器统一包装。
- **分页依赖**：`pagination` 作为 FastAPI `Depends`，自动校验页码/页大小，列表响应内嵌分页元信息（`items` / `total` / `page` / `page_size`）。
- **异常体系**：`BizError` 业务异常 + 一组异常处理器（HTTP 异常、参数校验异常、兜底异常），把任意失败归一为统一响应体。
- **应用工厂**：`create_app()` 一行装配好异常处理器。
- **SQLAlchemy 模型层**：`Base`、跨库兼容的 `GUID` 类型，以及 `UuidMixin` / `TimestampMixin` / `TenantMixin` / `MerchantMixin` / `SoftDeleteMixin` 等复用混入。
- **通用 CRUD**：`CRUD` 异步助手，自动感知软删除，覆盖增删改查与分页列表。

## 安装

```bash
pip install snowland-fastapihelper
# 核心功能（统一响应 / 异常 / 应用工厂）仅依赖 fastapi / starlette / astartool
```

SQLAlchemy 为**可选依赖**，仅在使用 `database.sqlalchemy`（模型 / CRUD）时需要：

```bash
# 方式一：安装包时带 extra
pip install "snowland-fastapihelper[sqlalchemy]"

# 方式二：仅装 SQLAlchemy 相关依赖
pip install -r requirements-sqlalchemy.txt
```

> 依赖中的 `astartool` 来自内部索引，请按需配置 pip 源；`fastapi` / `starlette` 来自 PyPI。

## 快速开始

### 统一响应 + 分页

```python
from typing import List
from fastapi import FastAPI
from snowland_fastapihelper import create_app, ok, ok_list, pagination, Pagination

app = create_app(title="Demo")


@app.get("/ping")
def ping():
    return ok({"hello": "world"})


@app.get("/items")
def items(page: Pagination = pagination()):
    # 这里用假数据演示；真实场景从数据库取
    items: List[dict] = [{"id": i} for i in range(page.offset, page.offset + page.page_size)]
    return ok_list(items, total=1000, page=page.page, page_size=page.page_size)
```

返回的响应体形如：

```json
{
  "successful": true,
  "code": 0,
  "message": "ok",
  "data": { "items": [...], "total": 1000, "page": 1, "page_size": 20 }
}
```

### 业务异常

```python
from snowland_fastapihelper import BizError

@app.get("/user/{uid}")
def get_user(uid: str):
    if uid != "1":
        raise BizError(code=9, message="无此用户")
    return ok({"uid": uid})
```

抛出的 `BizError` 会自动被异常处理器包装为：

```json
{ "successful": false, "code": 9, "message": "无此用户", "data": null }
```

### 模型与 CRUD（ORM 无关接口）

`database` 模块是 **ORM 无关的抽象层**：核心只定义统一的 `CRUDProtocol` 接口
与后端注册表，具体 ORM 在各自子包中实现并自注册。业务层一律通过统一入口
`get_crud(model, session)` 获取 CRUD 助手，**无需关心底层用的是哪种 ORM**。

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from snowland_fastapihelper import (
    Base, UuidMixin, TimestampMixin, SoftDeleteMixin, get_crud,
)


class User(Base, UuidMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)  # 物理主键（详见下方说明）
    name: Mapped[str] = mapped_column(nullable=False, comment="用户名")


async def create_user(session: AsyncSession, name: str):
    # 按 session 类型自动派发到对应 ORM 后端（此处为 sqlalchemy）
    crud = get_crud(User, session)
    return await crud.create(name=name)


async def list_users(session: AsyncSession, page: int = 1, page_size: int = 20):
    crud = get_crud(User, session)
    rows, total = await crud.list(page=page, page_size=page_size)
    return rows, total
```

`CRUD` 会自动过滤软删除记录；调用 `soft_delete(uuid)` 执行逻辑删除，`delete(uuid)` 执行物理删除。

> **关于物理主键**：`Base` / `UuidMixin` 仅提供对外暴露的业务 `uuid`，并未声明
> 数据库物理主键。请在模型上自行定义 `id` 自增主键（或你所选 ORM 的对应主键），
> 否则映射会失败。

### 接入其他 ORM

要支持 SQLAlchemy 之外的 ORM（如 Tortoise / Piccolo / Peewee），只需：

1. 在 `snowland_fastapihelper/database/<your_orm>/` 中实现 `CRUDProtocol`；
2. 用该 ORM 的 session 类型向注册表自注册（import 子包即生效）：

   ```python
   from snowland_fastapihelper.database import register_backend

   register_backend("tortoise", TortoiseSession, lambda model, session: TortoiseCRUD(model, session))
   ```

此后业务层调用 `get_crud(model, session)` 的方式**完全不变**，自动按 session 类型
派发到对应后端。也可显式 `get_crud(model, session, backend="tortoise")` 指定。

> 注意：`Base` / `UuidMixin` 等模型基类属于 SQLAlchemy 实现，位于
> `snowland_fastapihelper.database.sqlalchemy`；其他 ORM 的模型基类应各自在其
> 子包中定义，本库不强制统一模型声明（各 ORM 字段写法不同）。统一的是 **CRUD 行为接口**。

## 响应格式约定

无论 HTTP 层状态码如何，业务层统一返回 **HTTP 200**，由响应体内的 `successful` 与 `code` 表达成败。`code` 取值来自 `astartool.common.ErrorCode`。

## 测试

```bash
# 开发模式安装后
python -m unittest discover -s tests
```

## 目录结构

```
snowland_fastapihelper/
├── __init__.py            # 公共 API 导出
├── response.py            # 统一响应 / 分页依赖
├── exceptions.py          # 业务异常与异常处理器
├── app.py                 # 应用工厂 create_app
└── database/
    └── sqlalchemy/
        ├── models.py     # Base / GUID / 混入
        └── crud.py       # 通用异步 CRUD 助手
```

## 许可证

BSD 3-Clause，见 [LICENSE](./LICENSE)。
