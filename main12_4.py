import numpy as np
import pandas as pd
import warnings
from pathlib import Path
from typing import Optional
import subprocess
import os

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

if __name__ == "__main__":
    import sys

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
    print(f"\nBASIC.ISAC参数值: {isac_value}")
    #BASIC.Senario参数值: 0-场景V2X；1-UAV；2-ship
    #BASIC.ISAC参数值: 0-单独通信仿真；1-单独感知仿真；2-联合仿真
    if  senario == "0":
        if isac_value == "0": #单独通信仿真
            # 定义文件路径
            origin_path = "/home/xu/projet/ISAC_Commv0605/ISAC_Comm/ISAC_Comm_V2X/inputfiles/OverWriteDL_origin.txt"
            output_path = "/home/xu/projet/ISAC_Commv0605/ISAC_Comm/ISAC_Comm_V2X/inputfiles/OverWriteDL.txt"
            # 创建新的参数文件
            create_overwrite_v2x(origin_path, output_path, params)
            # 执行ISAC可执行文件
            isac_path = "/home/xu/projet/ISAC_Commv0605/ISAC_Comm/ISAC_Comm_V2X/ISAC"
            work_dir = "/home/xu/projet/ISAC_Commv0605/ISAC_Comm/ISAC_Comm_V2X"
            if os.path.exists(isac_path):
                print(f"\n开始执行ISAC可执行文件: {isac_path}")
                try:
                    # 切换到工作目录并执行ISAC
                    result = subprocess.run([isac_path], cwd=work_dir, check=True)
                    print(f"ISAC执行成功，返回码: {result.returncode}")
                except subprocess.CalledProcessError as e:
                    print(f"ISAC执行失败，返回码: {e.returncode}")
                except Exception as e:
                    print(f"执行ISAC时发生错误: {e}")
            else:
                print(f"错误: ISAC可执行文件不存在: {isac_path}")

        elif isac_value == "1" : #单独感知仿真
            # 定义文件路径
            origin_path = "/home/xu/projet/ISAC_Sensingv0530/ISAC_Sensing-master-V2X/Inputfiles/OverWrite.txt"
            output_path = "/home/xu/projet/ISAC_Sensingv0530/ISAC_Sensing-master-V2X/Inputfiles/OverWriteNew.txt"
            # 建新的参数文件
            create_overwrite_v2x_sensing(origin_path, output_path, params)
            project_dir = "/home/xu/projet/ISAC_Sensingv0530/ISAC_Sensing-master-V2X"
            build_dir = "build_v2x"
            isac_path = os.path.join(project_dir, build_dir, "isac_sensing")
            work_dir = project_dir
            if os.path.exists(isac_path):
                print(f"\n开始执行ISAC可执行文件: {isac_path}")
                try:
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
                    # 切换到工作目录并执行ISAC
                    result = subprocess.run([isac_path], cwd=work_dir, check=True)
                    print(f"ISAC执行成功，返回码: {result.returncode}")
                except subprocess.CalledProcessError as e:
                    print(f"ISAC执行失败，返回码: {e.returncode}")
                except Exception as e:
                    print(f"执行ISAC时发生错误: {e}")
            else:
                print(f"错误: ISAC可执行文件不存在: {isac_path}")

    # 获取特定参数用于后续处理
    grid_resolution = float(params.get("BASIC.COMM_RADIUS", 50.0))
    ue_height = float(params.get("BASIC.UE_HEIGHT", 100.0))
    
    print(f"\n测试用网格分辨率 (BASIC.COMM_RADIUS): {grid_resolution} 米")
    print(f"当前UE高度 (BASIC.UE_HEIGHT): {ue_height} 米")
    
    # 如果需要，这里可以调用其他函数进行处理
    # config = get_runtime_config(
    #     grid_resolution=grid_resolution,
    #     ue_height=ue_height,
    # )
    # main(config)
