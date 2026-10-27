# 发布说明 — v0.2.0

**发布日期：** 2026-10-27

## 核心亮点

- 新增两个功能包：**身份与用户**（`auth`）和**验证码**（`captcha`）。
- 验证码改用**密码学安全**的随机源（`SystemRandom`），替换可被预测的 `random` 模块。
- 进程内内存缓存新增**后台主动回收**过期条目的机制，堵住「生成但未验证」导致的内存泄漏。
- 包版本号改为**单一来源**，从 `snowland_fastapihelper.__version__` 读取。

## 新功能

### 身份与用户 — `snowland_fastapihelper.auth`

参照 `django.contrib.auth` 的设计，身份相关原语统一放在此处，其它特性（如验证码）只依赖契约、不自行定义用户类。

- `AbstractBaseUser` — 最小身份契约（`identity_key`）。
- `AbstractUser` / `User` — 真实用户账户（`uuid` 指向 `users.uuid`，可选 `tenant_id` / `merchant_id` 做数据隔离）。
- `VirtualUser` — 无账户身份（如注册前的手机号）。
- `get_user_model()` / `set_user_model()` — 替换生效的用户模型。

### 验证码 — `snowland_fastapihelper.captcha`

与 ORM 无关的验证码服务。

- 双时间窗口：**过期时间**（有效期）与**保留时间**（记录保留时长，≥ 过期时间），可区分「已过期」与「从未生成」。
- `CaptchaService.generate` / `verify` / `invalidate` / `remaining_seconds`。
- `VerifyStatus`：`SUCCESS` / `MISMATCH` / `EXPIRED` / `NOT_FOUND`。
- 后端：内置 `MemoryCache`，或可选 `RedisCache`（`redis` 可选依赖）跨 worker 共享。

## 改进

- **安全随机生成** — 由伪随机 `random` 模块改为 `astartool.random.random_digit_string`（基于 `SystemRandom`），验证码不可被预测或重放。
- **内存缓存 sweeper** — 后台守护线程周期性清理过期条目。此前仅惰性过期（访问时才删），「生成但未查询」的验证码会一直驻留内存造成泄漏，现已解决。

## 打包

- 版本号改为从 `snowland_fastapihelper.__version__` 读取（`pyproject.toml` 使用 `dynamic = ["version"]`）。发布流程以 `--no-isolation` 构建，并预装运行时依赖（`fastapi`、`starlette`、`astartool`）以便解析版本。
- `redis` 仍是验证码 Redis 后端的**可选依赖**（extra）。

## 升级说明

- 对 v0.1.x 的公开接口（`response`、`exceptions`、`app` 工厂、`database`）**无破坏性改动**；`auth` / `captcha` 为新增子包。
- 若使用**多 worker / 多进程**部署，验证码缓存请改用 Redis 后端以跨进程共享；`MemoryCache` 为进程内单例。
- Redis 键自带服务端 TTL（= 保留时间），过期码由 Redis 自行回收，无需 sweeper。

## API 参考

见 [`api_v0_2_0.zh.md`](api_v0_2_0.zh.md)。
