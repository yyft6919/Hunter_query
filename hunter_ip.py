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
    "api_url": "https://hunter.qianxin.com/openApi/search",  # API接口地址
    "page_size": 100,  # 每页结果数量
    "max_page": 5,    # 最大查询页数
    "delay": 1        # 请求间隔时间(秒)
}


def search_by_domain_or_ip(target, is_domain=True):
    """
    根据域名或IP地址搜索ICP备案信息，返回企业名称和备案信息
    """
    if not CONFIG["api_key"]:
        print("[错误] 请先在脚本中配置API密钥")
        sys.exit(1)

    results = []
    # 构建查询字符串
    if is_domain:
        query = f'domain="{target}"'
    else:
        query = f'ip="{target}"'
    
    # 使用Base64编码处理查询参数
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

            print(f"[信息] 正在查询 {target} 的第 {page} 页结果...")
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

            # 提取企业名称和备案信息
            for item in data.get("data", {}).get("arr", []):
                domain = item.get("domain")
                ip = item.get("ip")
                # 直接获取网站标题作为辅助信息
                web_title = item.get("web_title", "")
                
                # 尝试多种方式获取ICP信息
                company_name = None
                icp_number = None
                
                # 方式1：直接从company和number字段获取（API返回的主要格式）
                if item.get("company"):
                    company_name = item.get("company")
                if item.get("number"):
                    icp_number = item.get("number")
                
                # 方式2：从icp字段获取（兼容旧格式）
                if not company_name and item.get("icp") and isinstance(item.get("icp"), dict):
                    company_name = item.get("icp", {}).get("name")
                    icp_number = item.get("icp", {}).get("number")
                
                # 方式3：从icp_info字段获取（兼容旧格式）
                if not company_name and item.get("icp_info") and isinstance(item.get("icp_info"), dict):
                    company_name = item.get("icp_info", {}).get("name")
                    icp_number = item.get("icp_info", {}).get("number")
                
                # 方式3：如果有企业名称但没有备案号，设置默认值
                if company_name and not icp_number:
                    icp_number = "未获取到备案号"
                
                # 方式4：如果网站标题中包含学院/大学等关键词，可能是教育机构
                if not company_name and web_title and ("学院" in web_title or "大学" in web_title or "学校" in web_title):
                    company_name = web_title
                    icp_number = "未获取到备案号"
                
                # 使用集合记录已添加的企业名称，确保相同企业名称只记录一次
                # 检查是否已存在该企业
                company_exists = False
                if company_name:
                    for result in results:
                        if result.get("企业名称") == company_name:
                            company_exists = True
                            break
                
                if company_name and not company_exists:
                    results.append({
                        "企业名称": company_name, 
                        "备案号": icp_number if icp_number else "未获取到备案号",
                        "域名": domain if domain else "",
                        "IP地址": ip if ip else "未获取到IP",
                        "网站标题": web_title
                    })
                # 即使没有企业名称，也记录IP和域名信息，但确保域名不重复
                elif domain and not any(r.get("域名") == domain for r in results):
                    results.append({
                        "企业名称": web_title if web_title else "未获取到企业名称", 
                        "备案号": "未获取到备案号",
                        "域名": domain,
                        "IP地址": ip if ip else "未获取到IP",
                        "网站标题": web_title
                    })

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


def process_target(target, is_domain=True):
    """
    处理单个域名或IP地址
    """
    target_type = "域名" if is_domain else "IP地址"
    print(f"\n[信息] 开始查询{target_type}: {target}")
    results = search_by_domain_or_ip(target, is_domain)
    
    if results:
        print(f"[成功] 找到 {len(results)} 个企业信息")
        return {"查询目标": target, "查询类型": target_type, "企业列表": results}
    else:
        print(f"[警告] 未找到 {target} 的企业信息")
        return {"查询目标": target, "查询类型": target_type, "企业列表": []}


def process_file(file_path, is_domain=True):
    """
    处理包含多个域名或IP地址的文件
    """
    if not os.path.exists(file_path):
        print(f"[错误] 文件不存在: {file_path}")
        sys.exit(1)

    results = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            targets = [line.strip() for line in f if line.strip()]
        
        target_type = "域名" if is_domain else "IP地址"
        print(f"[信息] 从文件中读取到 {len(targets)} 个{target_type}")
        for target in targets:
            result = process_target(target, is_domain)
            results.append(result)
    except Exception as e:
        print(f"[错误] 读取文件失败: {str(e)}")
        sys.exit(1)

    return results


def export_to_excel(results, output_file="hunter_reverse_results.xlsx"):
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
        target = result["查询目标"]
        target_type = result["查询类型"]
        companies = result["企业列表"]
        
        if companies:
            for company in companies:
                data.append({
                    "查询目标": target,
                    "查询类型": target_type,
                    "企业名称": company["企业名称"],
                    "备案号": company["备案号"],
                    "域名": company["域名"],
                    "IP地址": company["IP地址"],
                    "网站标题": company.get("网站标题", "")
                })
        else:
            data.append({
                "查询目标": target,
                "查询类型": target_type,
                "企业名称": "未找到企业信息",
                "备案号": "无",
                "域名": "无" if target_type == "IP地址" else target,
                "IP地址": target if target_type == "IP地址" else "无"
            })
    
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
        alt_output_file = f"hunter_reverse_results_{int(time.time())}.xlsx"
        try:
            df.to_excel(alt_output_file, index=False)
            print(f"[信息] 已将结果保存到备用文件: {alt_output_file}")
        except Exception as e:
            print(f"[错误] 导出到备用文件也失败: {str(e)}")
    except Exception as e:
        print(f"[错误] 导出Excel失败: {str(e)}")


def is_domain(target):
    """
    判断输入是域名还是IP地址
    """
    # 简单判断是否为IP地址（四组0-255的数字，用点分隔）
    import re
    ip_pattern = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')
    match = ip_pattern.match(target)
    if match:
        # 验证每个数字是否在0-255范围内
        for group in match.groups():
            if int(group) > 255:
                return True  # 不是有效IP，当作域名处理
        return False  # 是IP地址
    return True  # 不匹配IP模式，当作域名处理


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

下载地址：{Fore.GREEN}https://github.com{Style.RESET_ALL}
"""
    print(banner)

def main():
    # 先打印banner
    print_banner()
    
    parser = argparse.ArgumentParser(description="Hunter 域名/IP反查ICP备案企业工具")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-d", "--domain", help="指定单个域名")
    group.add_argument("-i", "--ip", help="指定单个IP地址")
    group.add_argument("-f", "--file", help="指定包含域名或IP地址的文本文件路径")
    group.add_argument("-a", "--auto", help="自动识别输入是域名还是IP地址")
    parser.add_argument("-t", "--type", choices=['domain', 'ip'], default='domain', 
                        help="指定文件中包含的是域名还是IP地址（与-f一起使用）")
    parser.add_argument("-o", "--output", default="结果/反查ICP.xlsx", help="输出Excel文件路径")
    
    args = parser.parse_args()
    
    # 如果使用默认输出路径，确保结果目录存在
    if args.output == "结果/反查ICP.xlsx":
        os.makedirs("结果", exist_ok=True)
    
    results = []
    if args.domain:
        result = process_target(args.domain, is_domain=True)
        results.append(result)
    elif args.ip:
        result = process_target(args.ip, is_domain=False)
        results.append(result)
    elif args.auto:
        is_domain_target = is_domain(args.auto)
        target_type = "域名" if is_domain_target else "IP地址"
        print(f"[信息] 自动识别输入为{target_type}")
        result = process_target(args.auto, is_domain=is_domain_target)
        results.append(result)
    elif args.file:
        is_domain_input = args.type == 'domain'
        results = process_file(args.file, is_domain=is_domain_input)
    
    if results:
        export_to_excel(results, args.output)


if __name__ == "__main__":
    main()