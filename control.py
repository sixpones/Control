from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent
ALL_DOMAINS = ("communication", "sensing")
ALL_SCENARIOS = ("uav", "v2x", "ship")
V2X_SENSING_PROJECT = Path("/home/xu/projet/ISAC_Sensingv0530/ISAC_Sensing-master-V2X")
SHIP_SENSING_PROJECT = Path("/home/xu/projet/ISAC_Sensingv0530/ISAC_Sensing-master-Ship")

# 建议前端后续使用 BASIC.SIM_MODE 做三态控制：
# 0: 只跑通信仿真, 1: 只跑感知仿真, 2: 通信和感知都跑。
# 为了兼容现有参数表，当前代码会在没有 BASIC.SIM_MODE 时读取 BASIC.ISAC。
SIMULATION_MODE_MAP = {
    "0": ("communication",),
    "1": ("sensing",),
    "2": ("communication", "sensing"),
    "comm": ("communication",),
    "communication": ("communication",),
    "通信": ("communication",),
    "sens": ("sensing",),
    "sensing": ("sensing",),
    "感知": ("sensing",),
    "both": ("communication", "sensing"),
    "all": ("communication", "sensing"),
    "isac": ("communication", "sensing"),
    "通感": ("communication", "sensing"),
    "通信感知": ("communication", "sensing"),
}

SCENARIO_ALIASES = {
    "uav": "uav",
    "无人机": "uav",
    "v2x": "v2x",
    "车联网": "v2x",
    "vehicle": "v2x",
    "ship": "ship",
    "ships": "ship",
    "boat": "ship",
    "船": "ship",
    "船只": "ship",
}

# 如果地图导入总是同时跑通信地图和感知地图，把这里改成 False。
MAP_FOLLOWS_SIMULATION_DOMAINS = True

V2X_SENSING_SYNC_PARAMS = (
    "BASIC.NETWORK_FIGURE",
    "BASIC.FRAME_STRUCTURE",
    "BASIC.WAVEFORM_TYPE",
    "BASIC.CELL_RADIUS",
    "BASIC.BS_HEIGHT",
    "BASIC.BS_POWER_DBM",
    "BASIC.BS_ANTENNA_GAIN_DBi",
    "BASIC.ANYENNA_FIGURE",
    "BASIC.ANTENNA_POLARIZATION_BS",
    "BASIC.ANTENNA_POLARIZATION_UE",
    "BASIC.UE_HEIGHT",
    "BASIC.UE_ANTENNA_GAIN_DBi",
    "BASIC.OutputPath",
)


@dataclass(frozen=True)
class ProjectCommand:
    """一个独立工程的启动方式。

    commands 里的 {config} 会替换为 txt 参数文件路径，{output} 会替换为
    BASIC.OutputPath，{jobs} 会替换为 CPU 核心数。
    """

    display_name: str
    cwd: Path
    commands: tuple[tuple[str, ...], ...]
    prepare: str | None = None


@dataclass(frozen=True)
class Task:
    kind: str
    domain: str
    scenario: str | None
    project: ProjectCommand


# TODO: 把下面 cwd 和 command 改成你 8 个独立工程的真实路径与启动命令。
PROJECT_REGISTRY: dict[tuple[str, str, str | None], ProjectCommand] = {
    ("map", "communication", None): ProjectCommand(
        display_name="通信地图导入",
        cwd=PROJECT_ROOT / "TODO_comm_map_python_project",
        commands=(("python3", "main.py", "{config}"),),
    ),
    ("map", "sensing", None): ProjectCommand(
        display_name="感知地图导入",
        cwd=PROJECT_ROOT / "TODO_sensing_map_python_project",
        commands=(("python3", "main.py", "{config}"),),
    ),
    ("simulation", "communication", "uav"): ProjectCommand(
        display_name="通信仿真-UAV",
        cwd=PROJECT_ROOT / "TODO_comm_uav_cpp_project",
        commands=(("./run.sh", "{config}"),),
    ),
    ("simulation", "communication", "v2x"): ProjectCommand(
        display_name="通信仿真-V2X",
        cwd=PROJECT_ROOT / "TODO_comm_v2x_cpp_project",
        commands=(("./run.sh", "{config}"),),
    ),
    ("simulation", "communication", "ship"): ProjectCommand(
        display_name="通信仿真-船只",
        cwd=PROJECT_ROOT / "TODO_comm_ship_cpp_project",
        commands=(("./run.sh", "{config}"),),
    ),
    ("simulation", "sensing", "uav"): ProjectCommand(
        display_name="感知仿真-UAV",
        cwd=PROJECT_ROOT / "TODO_sensing_uav_cpp_project",
        commands=(("./run.sh", "{config}"),),
    ),
    ("simulation", "sensing", "v2x"): ProjectCommand(
        display_name="感知仿真-V2X",
        cwd=V2X_SENSING_PROJECT,
        prepare="v2x_sensing_overwrite",
        commands=(
            (
                "cmake",
                "--build",
                "build_v2x",
                "--target",
                "isac_sensing",
                "--parallel",
                "{jobs}",
            ),
            ("./build_v2x/isac_sensing",),
        ),
    ),
    ("simulation", "sensing", "ship"): ProjectCommand(
        display_name="感知仿真-船只",
        cwd=SHIP_SENSING_PROJECT,
        commands=(
            (
                "cmake",
                "--build",
                "build-debug",
                "--target",
                "isac_sensing",
                "--parallel",
                "{jobs}",
            ),
            ("./build-debug/isac_sensing",),
        ),
    ),
}


def parse_config_txt(txt_path: str | Path) -> dict[str, str]:
    """解析形如 '&\tBASIC.ISAC\t1' 的前端参数文件。"""
    params: dict[str, str] = {}
    with Path(txt_path).open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(maxsplit=2)
            if len(parts) < 3 or parts[0] != "&":
                continue

            params[parts[1].strip()] = parts[2].strip()

    return params


def read_simulation_domains(params: dict[str, str]) -> tuple[str, ...]:
    raw_mode = params.get("BASIC.SIM_MODE", params.get("BASIC.ISAC", "2"))
    mode = raw_mode.strip().lower()
    domains = SIMULATION_MODE_MAP.get(mode)
    if domains is None:
        raise ValueError(
            f"不支持的仿真模式 {raw_mode!r}。请使用 0/1/2、通信、感知、both 等值。"
        )
    return domains


def read_scenarios(params: dict[str, str]) -> tuple[str, ...]:
    raw_scene = first_existing_param(
        params,
        (
            "BASIC.SCENE",
            "BASIC.SCENARIO",
            "BASIC.SCENES",
            "BASIC.SCENARIOS",
            "BASIC.SIM_SCENE",
        ),
    )
    if raw_scene is None or raw_scene.strip().lower() in {"", "all", "全部", "*"}:
        return ALL_SCENARIOS

    scenarios: list[str] = []
    for token in re.split(r"[,，;/、\s]+", raw_scene.strip()):
        if not token:
            continue
        scenario = SCENARIO_ALIASES.get(token.lower(), SCENARIO_ALIASES.get(token))
        if scenario is None:
            valid_values = ", ".join(ALL_SCENARIOS)
            raise ValueError(f"不支持的场景 {token!r}。可选场景: {valid_values}")
        if scenario not in scenarios:
            scenarios.append(scenario)

    return tuple(scenarios)


def first_existing_param(params: dict[str, str], keys: Iterable[str]) -> str | None:
    for key in keys:
        if key in params:
            return params[key]
    return None


def read_bool_param(params: dict[str, str], key: str, default: bool = False) -> bool:
    raw_value = params.get(key)
    if raw_value is None:
        return default

    value = raw_value.strip().lower()
    if value in {"1", "true", "yes", "y", "on", "启用", "是", "跑"}:
        return True
    if value in {"0", "false", "no", "n", "off", "禁用", "否", "不跑"}:
        return False

    raise ValueError(f"参数 {key} 的值 {raw_value!r} 不是有效开关，请使用 0 或 1。")


def build_execution_plan(
    params: dict[str, str],
    domains: tuple[str, ...] | None = None,
    scenarios: tuple[str, ...] | None = None,
) -> list[Task]:
    domains = domains or read_simulation_domains(params)
    scenarios = scenarios or read_scenarios(params)
    map_enabled = read_bool_param(params, "BASIC.MAP", default=False)

    tasks: list[Task] = []
    if map_enabled:
        map_domains = domains if MAP_FOLLOWS_SIMULATION_DOMAINS else ALL_DOMAINS
        for domain in map_domains:
            tasks.append(make_task("map", domain, None))

    for domain in domains:
        for scenario in scenarios:
            tasks.append(make_task("simulation", domain, scenario))

    return tasks


def make_task(kind: str, domain: str, scenario: str | None) -> Task:
    key = (kind, domain, scenario)
    project = PROJECT_REGISTRY.get(key)
    if project is None:
        raise KeyError(f"没有配置工程启动项: {key}")
    return Task(kind=kind, domain=domain, scenario=scenario, project=project)


def render_command(
    command: tuple[str, ...], config_path: Path, params: dict[str, str]
) -> list[str]:
    output_path = params.get("BASIC.OutputPath", "")
    replacements = {
        "config": str(config_path),
        "jobs": str(os.cpu_count() or 1),
        "output": output_path,
    }
    return [item.format(**replacements) for item in command]


def prepare_project(task: Task, config_path: Path, params: dict[str, str]) -> None:
    if task.project.prepare is None:
        return
    if task.project.prepare == "v2x_sensing_overwrite":
        prepare_v2x_sensing_overwrite(task.project.cwd, params)
        return
    raise ValueError(f"未知准备步骤: {task.project.prepare}")


def prepare_v2x_sensing_overwrite(project_dir: Path, params: dict[str, str]) -> None:
    input_dir = project_dir / "Inputfiles"
    overwrite_new = input_dir / "OverWriteNew.txt"
    template = overwrite_new if overwrite_new.exists() else input_dir / "OverWrite.txt"

    if not template.exists():
        raise FileNotFoundError(f"V2X感知参数模板不存在: {template}")

    replacements = {
        key: params[key]
        for key in V2X_SENSING_SYNC_PARAMS
        if key in params
    }
    replacements["BASIC.SCENARIO_TYPE"] = params.get("BASIC.SCENARIO_TYPE", "2")
    replacements["BASIC.V2X_UE_NUM"] = params.get("BASIC.V2X_UE_NUM", "60")

    lines = template.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    updated_lines: list[str] = []
    param_line = re.compile(r"^(\s*&\s*)([\w.]+)(\s+)(\S+)(.*)$")

    for line in lines:
        match = param_line.match(line)
        if not match:
            updated_lines.append(line)
            continue

        prefix, key, spaces, _old_value, suffix = match.groups()
        if key in replacements:
            updated_lines.append(f"{prefix}{key}{spaces}{replacements[key]}{suffix}")
            seen.add(key)
        else:
            updated_lines.append(line)

    for key, value in replacements.items():
        if key not in seen:
            updated_lines.append(f"&\t{key}\t{value}")

    overwrite_new.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    print(f"[准备] 已同步V2X感知参数: {overwrite_new}")


def print_plan(tasks: list[Task], config_path: Path, params: dict[str, str]) -> None:
    print("执行计划:")
    if not tasks:
        print("  - 无任务")
        return

    for index, task in enumerate(tasks, start=1):
        print(f"  {index}. {task.project.display_name}")
        print(f"     cwd: {task.project.cwd}")
        if task.project.prepare:
            print(f"     prepare: {task.project.prepare}")
        for command in task.project.commands:
            rendered = shlex.join(render_command(command, config_path, params))
            print(f"     cmd: {rendered}")


def run_task(task: Task, config_path: Path, params: dict[str, str]) -> None:
    cwd = task.project.cwd

    if not cwd.exists():
        raise FileNotFoundError(
            f"{task.project.display_name} 的工程目录不存在: {cwd}\n"
            "请先在 PROJECT_REGISTRY 中配置真实 cwd。"
        )

    prepare_project(task, config_path, params)

    for command_template in task.project.commands:
        command = render_command(command_template, config_path, params)
        print(f"       $ {shlex.join(command)}")
        completed = subprocess.run(command, cwd=cwd, check=False)
        if completed.returncode != 0:
            raise subprocess.CalledProcessError(completed.returncode, command)


def run_plan(
    tasks: list[Task],
    config_path: Path,
    params: dict[str, str],
    continue_on_error: bool,
) -> int:
    failed = 0
    for index, task in enumerate(tasks, start=1):
        print(f"[{index}/{len(tasks)}] 开始: {task.project.display_name}")
        try:
            run_task(task, config_path, params)
        except Exception as exc:
            failed += 1
            print(f"[失败] {task.project.display_name}: {exc}", file=sys.stderr)
            if not continue_on_error:
                return 1
        else:
            print(f"[完成] {task.project.display_name}")

    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="通信/感知/地图导入总控脚本")
    parser.add_argument(
        "config",
        nargs="?",
        default="LJun_20260516094947.txt",
        help="前端生成的参数 txt 文件路径",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="真正执行工程命令；不加该参数时只打印计划",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="某个工程失败后继续执行后续任务",
    )
    parser.add_argument(
        "--domain",
        action="append",
        choices=ALL_DOMAINS,
        help="临时覆盖仿真类型，可重复传入；例如 --domain sensing",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        choices=ALL_SCENARIOS,
        help="临时覆盖仿真场景，可重复传入；例如 --scenario ship",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    params = parse_config_txt(config_path)
    domains = tuple(args.domain) if args.domain else read_simulation_domains(params)
    scenarios = tuple(args.scenario) if args.scenario else read_scenarios(params)
    tasks = build_execution_plan(params, domains=domains, scenarios=scenarios)

    print(f"参数文件: {config_path}")
    print(f"BASIC.ISAC/SIM_MODE -> {', '.join(domains)}")
    print(f"BASIC.MAP -> {'启用' if read_bool_param(params, 'BASIC.MAP') else '禁用'}")
    print(f"场景 -> {', '.join(scenarios)}")
    print_plan(tasks, config_path, params)

    if not args.execute:
        print("当前为预演模式；确认 PROJECT_REGISTRY 后可加 --execute 真正运行。")
        return 0

    return run_plan(tasks, config_path, params, args.continue_on_error)


if __name__ == "__main__":
    raise SystemExit(main())
