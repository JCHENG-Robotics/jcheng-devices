# jcheng-devices

**简体中文** | [English](README.md)

`jcheng-devices` 是 JCHENG Robotics 生态的 L3 设备库：一个显式的声明式设备与
能力描述文件注册表，以及一个离线校验器，检查标识、Schema、交叉引用与验证标记。
它只描述设备；从不打开设备、不加入运行时图、不发送运动命令，也不绕过
`jcheng-system`。

> 状态：**实验性**，截至 2026-11-27。版本 0.1.0。仅离线校验：本仓库尚未打开
> 任何设备，也没有任何描述文件通过实机验证。
> 本文为英文主文档的中文对照；如有歧义，以英文版为准。

## 范围与边界

| 项 | 本仓库 |
|---|---|
| 层 | L3 |
| 输入 | `registry/registry.yaml`；设备与能力描述 YAML；两个内置 JSON Schema |
| 输出 | 校验后的描述数据、确定性列表、注册表摘要 |
| 硬件访问 | `none`（`capability.yaml`） |
| 拥有设备 | 无——设备 I/O 仍归 `jcheng-system` |
| 禁止 | 设备访问、加入运行时图、运动或租约权限、厂商代码、独立控制通道 |

v0.1.0 提供：

- 设备注册表与六个描述文件：ArmPi Ultra 机械臂、夹爪、底盘、前置 D435i
  相机、规划中的 M10 激光雷达，以及候选设备 PiPER X。
- 七个设备能力描述：机械臂位置控制与反馈、夹爪位置控制、底盘速度意图，以及
  RGB、深度与激光扫描数据流。
- `device-profile.v1` 与 `capability-profile.v1` JSON Schema、离线校验器、
  四个命令的 CLI 以及失败关闭的仓库门禁。
- URDF/Xacro、标定、硬件配置与仿真资产的组织规范。v0.1.0 不复制任何资产。

本仓库明确不做：

- 不打开串口、USB、CAN、GPIO 或视频设备。
- 不发布、不订阅任何话题，不启动运行时节点。
- 不定义命令通道，不持有租约。系统层仍是唯一运动来源。
- 不复制厂商代码、厂商网格模型或实测数据。
- 不猜测未验证参数。未验证的值要么明确标记，要么不写入。

设备描述只描述设备型号与能力。`jcheng-system` 中每台机器人的
`robot-profile.v1` 仍是伺服映射、关节限位、工作空间与工作台平面的运行时权威；
本仓库不替代、也不导出运行时配置。

## 仓库结构

```text
jcheng-devices/
├── capability.yaml
├── VERSION
├── README.md / README.zh-CN.md
├── ROADMAP.md / CHANGELOG.md / ACCEPTANCE.md
├── SCHEMA_OWNERSHIP.md        # Schema 归属、状态、消费方与提升触发条件
├── registry/
│   ├── registry.yaml          # 显式索引
│   ├── devices/               # 六个设备描述文件
│   └── capabilities/          # 七个能力描述文件
├── src/jcheng_devices/
│   ├── schemas/               # device-profile.v1、capability-profile.v1
│   ├── registry.py            # 加载与交叉引用校验
│   └── cli.py                 # list / show / validate / digest
├── tests/
├── docs/
├── assets/                    # 仅目录规范；未提交资产
├── scripts/check_repo_gate.sh
└── evidence/
```

## 依赖

- Python 3.10 或更高版本（宿主工具链在 3.12 上验证）。
- `PyYAML==6.0.2` 与 `jsonschema==4.26.0`；测试使用 `pytest==8.3.4`。
- 不需要 ROS 发行版，不需要机器人。
- 任何环节都不使用硬件访问。

## 快速开始

```bash
python3 -m pip install -e '.[test]'

# 校验注册表与全部描述文件。
jcheng-devices validate

# 查看注册表。
jcheng-devices list
jcheng-devices show hiwonder.armpi-ultra --json
jcheng-devices digest

# 不安装包也能运行测试与仓库门禁。
python3 -m pytest -q tests
bash scripts/check_repo_gate.sh
```

仅当所有描述文件都能加载、匹配 Schema、解析能力引用，并带有前后一致的验证声明
时，`validate` 才返回 `0`。发现问题返回 `1`；注册表完全无法读取时返回 `2`。

## 验证状态

| 结论 | 状态 | 证据 |
|---|---|---|
| 注册表、Schema、CLI 与交叉引用校验（离线） | 已验证（L0/L1，2026-11-27） | [evidence/20261127_scaffold/](evidence/20261127_scaffold/README.md) |
| ArmPi Ultra 参考设备事实 | 部分验证（2026-11-25） | `registry/devices/hiwonder.armpi-ultra.yaml`；系统验收与安全文档 |
| PiPER X 候选描述 | 未验证 | `registry/devices/agilex.piper-x.yaml`；工作区无该硬件 |
| M10 激光雷达规划描述 | 未验证 | `registry/devices/lslidar.m10.yaml`；设备未连接 |
| 本仓库在实机上测得的任何描述参数 | 未验证 | 无实机会话，本仓库未记录任何实测 |

完整报告：[ACCEPTANCE.md](ACCEPTANCE.md)。

## 相关仓库

- [`jcheng-interfaces`](https://github.com/JCHENG-Robotics/jcheng-interfaces) — 契约来源、Schema 与契约哈希。
- [`jcheng-system`](https://github.com/JCHENG-Robotics/jcheng-system) — 特权运行时；硬件 I/O 与运动的唯一归属。
- [`jcheng-simulation`](https://github.com/JCHENG-Robotics/jcheng-simulation) — 域 43 离线被控对象；设备描述的未来使用方。
- [`jcheng-learning`](https://github.com/JCHENG-Robotics/jcheng-learning) — 机器人适配描述；本仓库不替代它们。
- [`jcheng-perception`](https://github.com/JCHENG-Robotics/jcheng-perception) — 相机部署与标定证据。
- [`jcheng-mobile`](https://github.com/JCHENG-Robotics/jcheng-mobile) — 底盘意图与激光雷达接口预期。
- [`jcheng-teleop`](https://github.com/JCHENG-Robotics/jcheng-teleop) — 遥操作设备类别的未来使用方。
- [`jcheng-ops`](https://github.com/JCHENG-Robotics/jcheng-ops) — 无人值守巡检与看门狗。
- [`.github`](https://github.com/JCHENG-Robotics/.github) — 分类、文档标准、生态路线图与[职责边界规范](https://github.com/JCHENG-Robotics/.github/blob/main/docs/repo-boundaries.md)。

## 许可

许可证与版权审查进行中；本仓库没有 `LICENSE` 文件。
详见 [LICENSE-REVIEW.md](LICENSE-REVIEW.md)。
