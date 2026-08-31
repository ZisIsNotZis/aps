<p align="center">
  <img src="aps-logo.svg" width="112" alt="APS 标志">
</p>

<h1 align="center">APS · 高级计划与排程</h1>

<p align="center"><strong>把物料流、资源、规则和订单转换成可执行的生产计划。</strong><br>
APS 是一个实验性的本地优先计划工作台：用类型化 JSON/Pydantic 模型描述制造系统，编译为约束，使用可替换算法求解，并在浏览器中查看排程。</p>

<p align="center"><a href="README.md">English</a> · 简体中文</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0--only-blue.svg" alt="AGPL-3.0-only"></a>
  <a href="backend/pyproject.toml"><img src="https://img.shields.io/badge/Python-%E2%89%A53.12-3776AB?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="frontend/package.json"><img src="https://img.shields.io/badge/Vue%203%20%2B%20Vite-42b883?logo=vuedotjs&logoColor=white" alt="Vue 3 与 Vite"></a>
  <a href="backend/tests"><img src="https://img.shields.io/badge/tests-Pytest%20%2B%20Playwright-45ba63" alt="Pytest 与 Playwright"></a>
</p>

> 🚧 **状态：持续实验中。** APS 是研究/产品原型，不是经过验证的 MES/ERP 替代品；API 和求解器行为可能变化。

## 为什么是 APS？

生产计划经常散落在表格、封闭的商业系统和一次性脚本中。APS 尝试提供一个透明的中间层：模型、编译器、求解器以及最终甘特排程都能在同一处检查。

当前的特点包括 **统一的物料流模型**、**多种求解策略**、**9 个内置制造场景**，以及能直接展示计划的本地 Web 界面。仓库中的基准记录显示，在其场景套件上 greedy、CP-SAT 和 fluid 求解器达到 **9/9 正确率**；这只是项目内实验结果，并不代表普遍保证。

## ✨ 包含什么

- **APS Studio**：浏览器中的计划模型与业务资源探索界面。
- **Unified Planner**：加载场景、编辑实体/规则/订单、运行计划，并查看订单结果、计划块和 SVG 甘特图。
- **类型化计划模型**：实体、选择器、转换规则、订单、库存持有规则、截止时间、释放时间和货币目标。
- **编译与评估器**：验证模型、编译受限表达式、模拟库存/资源影响并计算结果分数。
- **求解器插件**：greedy 列表排程、OR-Tools CP-SAT、fluid 比例公平模拟，以及可选的 Gurobi 和 Java Timefold 集成。
- **场景库**：离散制造、电子、作业车间、装配线、食品、汽车、家具、制药和半导体示例。

### 求解器速览

仓库记录的基准可作方向参考：在其测试设置中，**greedy 约 1 秒**、**fluid 约 14 秒**、**CP-SAT 约 20 秒**。greedy 最快，CP-SAT 通常更擅长货币目标，fluid 则是面向可行性的不同路线。硬件、依赖版本和模型规模都会影响结果。

## 🚀 快速开始

依赖：Python **3.12+**、Node.js/npm，以及 `uv` 或 Python 虚拟环境。默认后端依赖包括 FastAPI、Pydantic、OR-Tools、Gurobi Python bindings 和 PyTorch；可选求解器还有额外要求。

```bash
git clone https://github.com/zisisnotzis/aps.git
cd aps
cd frontend && npm ci && cd ..
./run.sh
```

打开 <http://localhost:5173>。后端地址为 <http://localhost:8000>，健康检查为 `/api/health`。也可以使用 `./run.sh -b` 或 `./run.sh -f` 只启动一端。

后端测试：

```bash
cd backend
uv sync
uv run pytest
uv run ruff check .
```

## 🧭 使用方式

1. 打开 **Unified Planner** 并选择内置场景。
2. 加载场景，检查实体、规则和订单。
3. 按需在浏览器编辑模型，然后点击 **Run Plan**。
4. 查看状态、总工期、计划块数量、订单结果、计划块和甘特图。

核心接口很小：`GET /api/health`、`GET /api/unified/scenarios`、`GET /api/unified/scenarios/{id}`、`POST /api/unified/plan` 和 `POST /api/unified/validate`。模型契约见 [`backend/aps/unified/_schema.py`](backend/aps/unified/_schema.py) 与 [`docs/unified-aps-model.md`](docs/unified-aps-model.md)。

## 🔬 进阶方向

- 使用 `backend/benchmark_solvers.py`、`backend/benchmark_scale.py` 和 [`docs/benchmark-results.md`](docs/benchmark-results.md) 比较算法。
- 在 `backend/aps/unified/scenarios/registry.py` 注册新的场景生成器。
- 在 `backend/aps/unified/solvers/` 添加求解器插件；插件注册表将调度与模型/API 解耦。
- 查看 [`backend/aps/unified/_expr.py`](backend/aps/unified/_expr.py) 中的受限表达式 DSL，避免执行任意 Python。

## 🎯 目标与非目标

**目标：** 可读的计划内核；可复现的场景生成；可替换求解器；可检查的约束和结果；帮助理解和迭代的实用 UI。

**非目标：** 替代生产 ERP/MES；承诺所有模型都能得到全局最优解；提供多租户托管服务；接受任意可执行表达式；把求解器取舍隐藏成一个“最佳”答案。

## 路线图

- 稳定模型/schema 与错误信息。
- 在 UI/API 中明确求解器选择和时间限制。
- 用可复现的硬件/配置扩充正确性和性能基准。
- 改进持久化、导入导出和场景编写。
- 在面向网络部署前完善认证、安全和可观测性。

长期来看，APS 可以成为透明的排程实验室，或成为可嵌入的调度服务。实现这一愿景需要更强的验证、可解释性和生产级加固。

## ⚠️ 注意事项

- 默认开发服务器面向本地使用；CORS 只配置了本地前端来源。
- Gurobi 需要有效安装和许可证；Timefold 需要 Java 21+ 以及构建好的 JAR，两者都是可选项。
- 求解结果可能是启发式、受时间限制或实验性的。投入生产前，务必根据实际产能、日历、质量、安全和业务约束复核计划。
- 仓库包含归档设计文档和未完成实验；在依赖某个接口前请先查看状态说明和测试。

## 贡献

欢迎提交 issue 和聚焦的 Pull Request。修改求解器时请附带可复现的小模型；行为变化请更新测试，并说明目标值、总工期和计划块数量的影响。详见 [`CONTRIBUTING.md`](CONTRIBUTING.md)、[`SECURITY.md`](SECURITY.md) 和 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)。

Agent 可以协助分类 issue、调查故障、添加测试、更新文档和实现已接受的变更；维护者负责审查并合并贡献。

## 版本管理

后端包当前为 `0.1.0`，前端应用为内部 `0.0.0`。公开发布应从测试和文档一致的审查提交创建标签；范围与证据见 [`docs/project-status.md`](docs/project-status.md)。

## 许可证

APS 使用 [GNU Affero General Public License v3.0-only](LICENSE) 授权。
