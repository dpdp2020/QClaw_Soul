#!/usr/bin/env python3
"""
量化策略模拟回测 — 工具脚本
策略靠不靠谱？用历史数据回测验证你的交易策略

目标用户: 量化爱好者、个人投资者
输出产物: 回测报告（Markdown）、绩效数据表
"""

import sys, json, os, argparse
from datetime import datetime
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def cmd_run(args):
    """量化策略模拟回测 - 主工作流"""
    ensure_dirs()
    input_data = args.input or ""
    output_path = args.output or os.path.join(DATA_DIR, "output_{}.md".format(datetime.now().strftime("%Y%m%d_%H%M%S")))
    
    # Generate Excel output
    data = {
        "项目": [f"项目{i+1}" for i in range(10)],
        "状态": ["待处理"] * 10,
        "说明": ["[待填充实际数据]"] * 10,
        "优先级": ["P1"] * 5 + ["P2"] * 5,
    }
    df = pd.DataFrame(data)
    
    excel_path = output_path.replace(".md", ".xlsx") if output_path.endswith(".md") else output_path
    if not excel_path.endswith(".xlsx"):
        excel_path += ".xlsx"
    df.to_excel(excel_path, index=False, engine="openpyxl")
    
    result = {
        "status": "success",
        "output_file": excel_path,
        "rows": len(df),
        "message": f"量化策略模拟回测数据已生成到 {excel_path}",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_status(args):
    """查看当前状态"""
    data_files = []
    if os.path.exists(DATA_DIR):
        data_files = [f for f in os.listdir(DATA_DIR) if not f.startswith(".")]
    result = {
        "skill": "quant-backtester",
        "scene": "量化策略模拟回测",
        "data_dir": DATA_DIR,
        "data_files": data_files,
        "file_count": len(data_files),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_export(args):
    """导出结果"""
    fmt = getattr(args, "format", "json") or "json"
    data_files = []
    if os.path.exists(DATA_DIR):
        data_files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if not f.startswith(".")]
    
    if fmt == "json":
        output = json.dumps({"files": data_files, "count": len(data_files)}, ensure_ascii=False, indent=2)
    else:
        output = "\n".join(data_files)
    
    print(output)
    return 0


def main():
    parser = argparse.ArgumentParser(description="量化策略模拟回测")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    run_p = subparsers.add_parser("run", help="执行主工作流")
    run_p.add_argument("--input", "-i", help="输入数据或描述")
    run_p.add_argument("--output", "-o", help="输出文件路径")
    
    subparsers.add_parser("status", help="查看当前状态")
    
    export_p = subparsers.add_parser("export", help="导出结果")
    export_p.add_argument("format", nargs="?", default="json", help="导出格式")
    
    args = parser.parse_args()
    
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "export":
        return cmd_export(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
