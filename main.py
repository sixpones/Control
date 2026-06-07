import numpy as np
import pandas as pd
import warnings
from pathlib import Path
from typing import Optional
import subprocess
import os
import sys
import tempfile


MAP_PLOT_SCRIPT = Path(
    "/home/xu/pythonProject/python1/mapPlot4.1/mapPlot/main12_4.py"
)
MAP_PLOT_PYTHON = Path(
    "/home/xu/pythonProject/python1/mapPlot4.1/.venv/bin/python"
)
SENS_MAP_PLOT_SCRIPT = Path(
    "/home/xu/pythonProject/python2/mapPlotv0114/mapPlot/map_generate.py"
)
MAP_PLOT_PARAMS = (
    "BASIC.COMM_RADIUS",
    "BASIC.UE_HEIGHT",
    "BASIC.OutputPath",
)
SENS_MAP_PLOT_PARAMS = (
    "BASIC.SENS_RADIUS",
    "BASIC.UE_HEIGHT",
    "BASIC.OutputPath",
)

def parse_config_txt(txt_path: str) -> dict:
    """从配置txt文件中解析所有参数"""
    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    params = {}
    for line in lines:
        line = line.strip()
        if not line or not line.startswith("&"):
            continue
        
        # 移除开头的&符号
        content = line[1:].strip()
        # 按空白字符分割（制表符和空格都行），并过滤空字符串
        parts = content.split()
        
        if len(parts) >= 2:
            # 第一个部分是参数名，后续部分是参数值（可能有空格）
            key = parts[0].strip()
            # 值可能是多个部分（比如 "A file"），需要合并
            value = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
            
            if key:  # 确保键不为空
                params[key] = value

    return params


def create_overwrite_v2x_sensing(origin_path: str, output_path: str, params: dict) -> None:
    """OverWriteNew.txt文件，复制原文件内容并在末尾添加指定参数"""
    # 读取原文件内容
    with open(origin_path, "r", encoding="utf-8") as f:
        content = f.read()
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"创建目录: {output_dir}")
    # 需要添加的参数列表（从配置文件读取的键名）
    params_to_add = [
        "BASIC.BS_HEIGHT",
        "BASIC.BS_POWER_DBM",
        "BASIC.BS_ANTENNA_GAIN_DBi",
        "BASIC.ANYENNA_FIGURE",
        "BASIC.UE_HEIGHT",
        "BASIC.UE_ANTENNA_GAIN_DBi",
        "BASIC.NETWORK_FIGURE",
        "BASIC.FRAME_STRUCTURE",
        "BASIC.WAVEFORM_TYPE",
        "BASIC.CELL_RADIUS",
        "BASIC.SCENARIO_TYPE",
        "BASIC.V2X_UE_NUM",
        "BASIC.OutputPath",
    ]
    default_values = {
        "BASIC.SCENARIO_TYPE": "2",
        "BASIC.V2X_UE_NUM": "60",
    }
    # 在末尾添加参数
    additional_content = "\n"
    for param_name in params_to_add:
        param_value = params.get(param_name, default_values.get(param_name, ""))
        additional_content += f"& {param_name:<10} {param_value}\n"
    # 写入新文件（使用'w'模式会覆盖原有文件）
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content + additional_content)
    
    print(f"\n成功创建文件: {output_path}")
    print("添加的参数如下：")
    for param_name in params_to_add:
        param_value = params.get(param_name, default_values.get(param_name, ""))
        print(f"& {param_name:<10} {param_value}")


def create_overwrite_v2x(origin_path: str, output_path: str, params: dict) -> None:
    """创建OverWriteDL.txt文件，复制原文件内容并在末尾添加指定参数"""
    # 读取原文件内容
    with open(origin_path, "r", encoding="utf-8") as f:
        content = f.read()
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"创建目录: {output_dir}")
    # 需要添加的参数列表（从配置文件读取的键名）
    params_to_add = [
        "BASIC.INumSnapShot",
        "BASIC.BISMultiThread",
        "LINK_CTRL.IISShadowFadingUsed",
        "LINK_CTRL.IISFastFadingUsed",
        "LINK_CTRL.I2DOr3DChannel",
        "LINK_CTRL.I2DOr3DChannelSensing",
        "MSS.DVelocityMPS",
        "MSS.FirstBand.UL.DMaxTxPowerDbm",
        "BASIC.BS_HEIGHT",
        "BASIC.BS_POWER_DBM"
    ]
    # 键名映射：读取的键名 -> 写入的键名
    key_mapping = {
        "BASIC.BS_HEIGHT": "MSS.DAntennaHeightM",
        "BASIC.BS_POWER_DBM": "Macro.DL.DMaxTxPowerDbm"
    }
    # 在末尾添加参数
    additional_content = "\n"
    for param_name in params_to_add:
        param_value = params.get(param_name, "")
        # 使用映射后的键名（如果有映射），否则使用原键名
        output_key = key_mapping.get(param_name, param_name)
        additional_content += f"& {output_key:<10} {param_value}\n"
    # 写入新文件（使用'w'模式会覆盖原有文件）
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content + additional_content)
    
    print(f"\n成功创建文件: {output_path}")
    print("添加的参数如下：")
    for param_name in params_to_add:
        param_value = params.get(param_name, "")
        output_key = key_mapping.get(param_name, param_name)
        print(f"& {output_key:<10} {param_value}")


def run_v2x_communication(params: dict) -> bool:
    """生成V2X通信参数，编译并运行通信工程。"""
    work_dir = "/home/xu/projet/ISAC_Commv0605/ISAC_Comm/ISAC_Comm_V2X"
    build_dir = "build_v2x"
    origin_path = os.path.join(
        work_dir, "inputfiles", "OverWriteDL.txt.bak"
    )
    output_path = os.path.join(
        work_dir, "inputfiles", "OverWriteDL.txt"
    )
    isac_path = os.path.join(work_dir, build_dir, "ISAC")

    print("\n========== 开始V2X通信仿真 ==========")
    try:
        create_overwrite_v2x(origin_path, output_path, params)
        subprocess.run(
            [
                "cmake",
                "--build",
                build_dir,
                "--parallel",
                str(os.cpu_count() or 1),
            ],
            cwd=work_dir,
            check=True,
        )

        if not os.path.exists(isac_path):
            print(f"错误: 编译后未找到ISAC可执行文件: {isac_path}")
            return False

        print(f"\n开始执行ISAC可执行文件: {isac_path} v2x")
        result = subprocess.run(
            [isac_path, "v2x"],
            cwd=work_dir,
            check=True,
        )
        print(f"V2X通信仿真执行成功，返回码: {result.returncode}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"V2X通信仿真编译或执行失败，返回码: {e.returncode}")
    except Exception as e:
        print(f"执行V2X通信仿真时发生错误: {e}")
    return False


def run_v2x_sensing(params: dict) -> bool:
    """生成V2X感知参数，编译并运行感知工程。"""
    project_dir = "/home/xu/projet/ISAC_Sensingv0530/ISAC_Sensing-master-V2X"
    build_dir = "build_v2x"
    origin_path = os.path.join(project_dir, "Inputfiles", "OverWrite.txt")
    output_path = os.path.join(project_dir, "Inputfiles", "OverWriteNew.txt")
    isac_path = os.path.join(project_dir, build_dir, "isac_sensing")

    print("\n========== 开始V2X感知仿真 ==========")
    try:
        create_overwrite_v2x_sensing(origin_path, output_path, params)
        subprocess.run(
            [
                "cmake",
                "--build",
                build_dir,
                "--target",
                "isac_sensing",
                "--parallel",
                str(os.cpu_count() or 1),
            ],
            cwd=project_dir,
            check=True,
        )

        if not os.path.exists(isac_path):
            print(f"错误: 编译后未找到感知可执行文件: {isac_path}")
            return False

        print(f"\n开始执行感知可执行文件: {isac_path}")
        result = subprocess.run([isac_path], cwd=project_dir, check=True)
        print(f"V2X感知仿真执行成功，返回码: {result.returncode}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"V2X感知仿真编译或执行失败，返回码: {e.returncode}")
    except Exception as e:
        print(f"执行V2X感知仿真时发生错误: {e}")
    return False


def create_mapplot_config(config_path: Path, params: dict) -> None:
    """生成通信地图项目所需的三参数配置文件。"""
    missing_params = [
        param_name
        for param_name in MAP_PLOT_PARAMS
        if not params.get(param_name, "").strip()
    ]
    if missing_params:
        raise ValueError(
            "地图项目缺少必需参数: " + ", ".join(missing_params)
        )

    content = "".join(
        f"&\t{param_name}\t{params[param_name].strip()}\n"
        for param_name in MAP_PLOT_PARAMS
    )
    config_path.write_text(content, encoding="utf-8")


def create_sens_mapplot_config(config_path: Path, params: dict) -> None:
    """生成感知地图项目所需的三参数配置文件。"""
    missing_params = [
        param_name
        for param_name in SENS_MAP_PLOT_PARAMS
        if not params.get(param_name, "").strip()
    ]
    if missing_params:
        raise ValueError(
            "感知地图项目缺少必需参数: " + ", ".join(missing_params)
        )

    content = "".join(
        f"&\t{param_name}\t{params[param_name].strip()}\n"
        for param_name in SENS_MAP_PLOT_PARAMS
    )
    config_path.write_text(content, encoding="utf-8")


def run_comm_mapplot_project(params: dict) -> bool:
    """当 BASIC.MAP=1 时执行通信地图项目。"""
    if params.get("BASIC.MAP", "0").strip() != "1":
        print("\nBASIC.MAP=0，跳过通信地图项目。")
        return True

    if not MAP_PLOT_SCRIPT.is_file():
        print(f"错误: 地图项目入口不存在: {MAP_PLOT_SCRIPT}")
        return False

    if not MAP_PLOT_PYTHON.is_file():
        print(f"错误: 地图项目Python解释器不存在: {MAP_PLOT_PYTHON}")
        return False

    print("\n========== 开始执行通信地图项目 ==========")
    try:
        with tempfile.TemporaryDirectory(prefix="mapplot_") as temp_dir:
            mapplot_config = Path(temp_dir) / "mapplot_params.txt"
            create_mapplot_config(mapplot_config, params)

            print("传递给通信地图项目的参数：")
            for param_name in MAP_PLOT_PARAMS:
                print(f"& {param_name} {params[param_name].strip()}")

            result = subprocess.run(
                [
                    str(MAP_PLOT_PYTHON),
                    str(MAP_PLOT_SCRIPT),
                    str(mapplot_config),
                ],
                cwd=MAP_PLOT_SCRIPT.parent,
                check=True,
            )

        print(f"通信地图项目执行成功，返回码: {result.returncode}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"通信地图项目执行失败，返回码: {e.returncode}")
    except Exception as e:
        print(f"执行通信地图项目时发生错误: {e}")
    return False


def run_sens_mapplot_project(params: dict) -> bool:
    """当 BASIC.MAP=1 时执行感知地图项目。"""
    if params.get("BASIC.MAP", "0").strip() != "1":
        print("\nBASIC.MAP=0，跳过感知地图项目。")
        return True

    if not SENS_MAP_PLOT_SCRIPT.is_file():
        print(f"错误: 感知地图项目入口不存在: {SENS_MAP_PLOT_SCRIPT}")
        return False

    if not MAP_PLOT_PYTHON.is_file():
        print(f"错误: 地图项目Python解释器不存在: {MAP_PLOT_PYTHON}")
        return False

    print("\n========== 开始执行感知地图项目 ==========")
    try:
        with tempfile.TemporaryDirectory(prefix="sens_mapplot_") as temp_dir:
            mapplot_config = Path(temp_dir) / "sens_mapplot_params.txt"
            create_sens_mapplot_config(mapplot_config, params)

            print("传递给感知地图项目的参数：")
            for param_name in SENS_MAP_PLOT_PARAMS:
                print(f"& {param_name} {params[param_name].strip()}")

            result = subprocess.run(
                [
                    str(MAP_PLOT_PYTHON),
                    str(SENS_MAP_PLOT_SCRIPT),
                    str(mapplot_config),
                ],
                cwd=SENS_MAP_PLOT_SCRIPT.parent,
                check=True,
            )

        print(f"感知地图项目执行成功，返回码: {result.returncode}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"感知地图项目执行失败，返回码: {e.returncode}")
    except Exception as e:
        print(f"执行感知地图项目时发生错误: {e}")
    return False


if __name__ == "__main__":
    # 解析输入txt文件，提取所有参数
    txt_path = sys.argv[1] if len(sys.argv) > 1 else "/home/megumi/桌面/unicom_system_level/LJun_20260516094947_copy.txt"
    params = parse_config_txt(txt_path)
    print(f"配置文件: {txt_path}")
    print("解析到的所有参数如下：")
    print("-" * 50)
    for param_name, param_value in params.items():
        print(f"{param_name}: {param_value}")
    print("-" * 50)
    # 检查BASIC.ISAC参数
    isac_value = params.get("BASIC.ISAC", "1")
    senario = params.get("BASIC.Senario", "0")
    isac_map=params.get("BASIC.MAP", "0")
    print(f"\nBASIC.ISAC参数值: {isac_value}")
    #BASIC.Senario参数值: 0-场景V2X；1-UAV；2-ship
    #BASIC.ISAC参数值: 0-单独通信仿真；1-单独感知仿真；2-联合仿真
    if  senario == "0":
        if isac_value == "0": #单独通信仿真
            run_v2x_communication(params)

        elif isac_value == "1" : #单独感知仿真
            run_v2x_sensing(params)

        elif isac_value == "2": #先通信、后感知的联合仿真
            print("\n========== 开始V2X联合仿真 ==========")
            communication_ok = run_v2x_communication(params)
            if not communication_ok:
                print("警告: V2X通信仿真未成功，继续执行V2X感知仿真。")
            sensing_ok = run_v2x_sensing(params)
            if communication_ok and sensing_ok:
                print("\nV2X通信和感知仿真全部完成。")
            else:
                print("\nV2X联合仿真结束，但存在失败任务，请检查上方日志。")

        else:
            print(f"错误: 不支持的BASIC.ISAC参数值: {isac_value}")

    # 获取特定参数用于后续处理
    if  isac_map== "1":
        run_comm_mapplot_project(params)
        run_sens_mapplot_project(params)
    
    # 如果需要，这里可以调用其他函数进行处理
    # config = get_runtime_config(
    #     grid_resolution=grid_resolution,
    #     ue_height=ue_height,
    # )
    # main(config)
