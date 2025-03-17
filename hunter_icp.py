#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import base64
import json
import os
import random
import sys
import time
from urllib.parse import quote, urlencode

import pandas as pd
import requests
from colorama import init, Fore, Style

# 初始化colorama
init(autoreset=True, convert=True)

# 配置信息
CONFIG = {
    "api_key": "",  # 在此处填写您的奇安信Hunter API密钥
    "api_url": "https://hunter.qianxin.com/openApi/search",  # 更新为正确的API接口地址
    "page_size": 100,  # 每页结果数量
    "max_page": 5,    # 最大查询页数
    "delay": 1        # 请求间隔时间(秒)
}


def search_by_icp(company_name):
    """
    根据公司名称搜索ICP备案信息，返回域名和IP地址
    """
    if not CONFIG["api_key"]:
        print("[错误] 请先在脚本中配置API密钥")
        sys.exit(1)

    results = []
    # 构建查询字符串
    query = f'icp.name="{company_name}"'
    
    # 尝试使用Base64编码处理查询参数
    query_base64 = base64.urlsafe_b64encode(query.encode('utf-8')).decode('utf-8')
    
    for page in range(1, CONFIG["max_page"] + 1):
        try:
            # 构建查询参数
            params = {
                "api-key": CONFIG["api_key"],
                "search": query_base64,  # 使用Base64编码后的查询参数
                "page": str(page),
                "page_size": str(CONFIG["page_size"]),
                "is_web": "1"  # 只搜索网站资产
            }
            
            # 打印完整URL以便调试
            print(f"[调试] 请求URL: {CONFIG['api_url']}?" + "&".join([f"{k}={v}" for k, v in params.items()]))

            print(f"[信息] 正在查询 {company_name} 的第 {page} 页结果...")
            # 添加请求头
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            response = requests.get(CONFIG["api_url"], params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            # 检查API返回状态
            if data.get("code") != 200:
                print(f"[错误] API请求失败: {data.get('message', '未知错误')}")
                break

            # 提取域名和IP信息
            for item in data.get("data", {}).get("arr", []):
                domain = item.get("domain")
                ip = item.get("ip")
                
                # 检查是否已存在该域名
                domain_exists = False
                for result in results:
                    if result["domain"] == domain:
                        domain_exists = True
                        break
                
                if domain and not domain_exists:
                    results.append({"domain": domain, "ip": ip})

            # 检查是否有更多页
            total = data.get("data", {}).get("total", 0)
            if page * CONFIG["page_size"] >= total:
                break

            # 添加延迟，避免请求过快
            time.sleep(CONFIG["delay"])

        except requests.exceptions.RequestException as e:
            print(f"[错误] 请求异常: {str(e)}")
            break
        except json.JSONDecodeError:
            print("[错误] 解析API响应失败")
            break
        except Exception as e:
            print(f"[错误] 未知异常: {str(e)}")
            break

    return results


def process_company(company_name):
    """
    处理单个公司名称
    """
    print(f"\n[信息] 开始查询公司: {company_name}")
    results = search_by_icp(company_name)
    
    if results:
        print(f"[成功] 找到 {len(results)} 个域名")
        return {"企业名称": company_name, "资产列表": results}
    else:
        print(f"[警告] 未找到 {company_name} 的域名信息")
        return {"企业名称": company_name, "资产列表": []}


def process_file(file_path):
    """
    处理包含多个公司名称的文件
    """
    if not os.path.exists(file_path):
        print(f"[错误] 文件不存在: {file_path}")
        sys.exit(1)

    results = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            companies = [line.strip() for line in f if line.strip()]
        
        print(f"[信息] 从文件中读取到 {len(companies)} 个公司名称")
        for company in companies:
            result = process_company(company)
            results.append(result)
    except Exception as e:
        print(f"[错误] 读取文件失败: {str(e)}")
        sys.exit(1)

    return results


def export_to_excel(results, output_file="结果/反查域名.xlsx"):
    """
    将结果导出到Excel文件
    """
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # 准备数据
    data = []
    for result in results:
        company = result["企业名称"]
        assets = result["资产列表"]
        
        if assets:
            for asset in assets:
                data.append({
                    "企业名称": company, 
                    "域名": asset["domain"], 
                    "IP地址": asset["ip"] if asset["ip"] else "未获取到IP"
                })
        else:
            data.append({"企业名称": company, "域名": "未找到域名", "IP地址": "无"})
    
    # 创建DataFrame
    new_df = pd.DataFrame(data)
    
    # 检查文件是否存在，如果存在则追加数据而不是覆盖
    if os.path.exists(output_file):
        try:
            # 尝试读取现有文件
            existing_df = pd.read_excel(output_file)
            # 合并现有数据和新数据
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            # 去除可能的重复项
            combined_df = combined_df.drop_duplicates()
            df = combined_df
            print(f"[信息] 已将新数据追加到现有文件 {output_file}")
        except Exception as e:
            print(f"[警告] 无法读取现有文件: {str(e)}，将创建新文件")
            # 如果读取失败，使用时间戳创建新文件
            file_name, file_ext = os.path.splitext(output_file)
            output_file = f"{file_name}_{int(time.time())}{file_ext}"
            df = new_df
    else:
        df = new_df
    
    try:
        # 尝试多次保存，以应对文件可能被占用的情况
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                df.to_excel(output_file, index=False)
                print(f"\n[成功] 结果已导出到 {output_file}")
                return
            except PermissionError:
                if attempt < max_attempts - 1:
                    print(f"[警告] 文件 {output_file} 可能被占用，正在重试...({attempt+1}/{max_attempts})")
                    time.sleep(2)  # 等待2秒后重试
                else:
                    raise
    except PermissionError:
        print(f"[错误] 无法写入文件 {output_file}，请确保该文件未被其他程序打开")
        # 尝试使用不同的文件名
        alt_output_file = f"hunter_results_{int(time.time())}.xlsx"
        try:
            df.to_excel(alt_output_file, index=False)
            print(f"[信息] 已将结果保存到备用文件: {alt_output_file}")
        except Exception as e:
            print(f"[错误] 导出到备用文件也失败: {str(e)}")
    except Exception as e:
        print(f"[错误] 导出Excel失败: {str(e)}")





def print_banner():
    """打印ASCII艺术字横幅，使用随机颜色"""
    # 定义可用的颜色列表
    colors = [Fore.RED, Fore.GREEN, Fore.BLUE, Fore.YELLOW, Fore.MAGENTA, Fore.CYAN]
    # 随机选择颜色
    banner_color = random.choice(colors)
    text_color = random.choice(colors)
    url_color = random.choice(colors)
    
    banner = f"""
{banner_color}┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ██╗  ██╗██╗   ██╗███╗   ██╗████████╗███████╗██████╗           │
│  ██║  ██║██║   ██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗          │
│  ███████║██║   ██║██╔██╗ ██║   ██║   █████╗  ██████╔╝          │
│  ██╔══██║██║   ██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗          │
│  ██║  ██║╚██████╔╝██║ ╚████║   ██║   ███████╗██║  ██║          │
│  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝          │
│                                                                 │
│{text_color}                      by: yyft --                             {banner_color}│
│{text_color}          -- 该工具仅用于学习参考，均与作者无关 --                {banner_color}│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

下载地址：{url_color}https://github.com{Style.RESET_ALL}
"""
    print(banner)

def main():
    # 先打印banner
    print_banner()
    
    parser = argparse.ArgumentParser(description="Hunter ICP备案反查工具")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-c", "--company", help="指定单个企业名称")
    group.add_argument("-f", "--file", help="指定包含企业名称的文本文件路径")
    parser.add_argument("-o", "--output", default="结果/反查域名.xlsx", help="输出Excel文件路径")
    
    args = parser.parse_args()
    
    results = []
    if args.company:
        result = process_company(args.company)
        results.append(result)
    elif args.file:
        results = process_file(args.file)
    
    if results:
        export_to_excel(results, args.output)


if __name__ == "__main__":
    main()
