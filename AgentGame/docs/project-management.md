# AgentGame 项目管理与目录约定

## 目录结构（约定）

```
AgentGame/
  docs/
    plans/            # 设计/范围/方案类文档（按日期）
  platform/           # 平台服务：match/leaderboard/replay/静态站点
  games/              # 纯规则引擎（无 IO）
  viewer/             # 观战页（静态资源，可由 platform 托管）
  site/               # 业务线展示网站（静态资源，可由 platform 托管）
  schemas/            # JSON schema（observation/action/replay）
  scripts/            # 本地工具（跑局/回放/压测等）
```

原则：
- `games/` 必须是确定性的纯逻辑（输入 → 输出），便于复盘与裁判
- `platform/` 负责 IO：存储、匹配、HTTP、静态资源托管
- 所有对外 API / schema 都要版本化（`ruleset_version` + `version` 字段）

## 里程碑（Phase 1）

- M1：平台最小闭环（match + replay）
- M2：grid-arena 可排位可观战
- M3：mini-auction 可跑局可复盘
- M4：稳定性与文档（OpenClaw 接入示例）

