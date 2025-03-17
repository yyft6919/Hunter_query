# Hunter 网络资产归属查询工具集

这是一套用于网络安全资产归属查询的工具集，可以帮助安全研究人员、渗透测试人员或网络管理员快速确定IP地址或域名的归属信息，以及根据企业名称查询其拥有的网络资产。

## 工具概述

本工具集基于奇安信Hunter API，包含两个主要功能模块：

1. **域名/IP反查ICP备案企业工具**：通过域名或IP地址反向查询ICP备案企业信息
2. **ICP反查域名工具**：通过企业名称查询其拥有的域名

## 环境要求

- Python 3.6+
- 依赖包：requests, pandas, colorama
- 奇安信Hunter API密钥

## 1. Hunter 域名/IP反查ICP备案企业工具

### 功能介绍

本工具可以通过域名或IP地址反向查询ICP备案企业信息，帮助确定网络资产的归属。支持单个查询和批量查询功能，结果将导出为Excel表格。

### 使用方法

#### 配置API密钥

在使用前，请先在脚本中的CONFIG字典里填写你的奇安信Hunter API密钥：

```python
CONFIG = {
    "api_key": "你的API密钥",  # 在此处填写您的奇安信Hunter API密钥
    # 其他配置...
}
```

#### 查询命令

1. **单个域名查询**：

   ```bash
   python hunter_ip.py -d "example.com"
   ```

2. **单个IP地址查询**：

   ```bash
   python hunter_ip.py -i "1.2.3.4"
   ```

3. **自动识别输入类型**：

   ```bash
   python hunter_ip.py -a "example.com"  # 自动识别是域名还是IP
   ```

4. **批量查询**（文件中每行一个域名或IP）：

   ```bash
   python hunter_ip.py -f "文件路径" -t domain  # 查询域名
   python hunter_ip.py -f "文件路径" -t ip      # 查询IP
   ```

5. **指定输出文件**（默认输出到：/结果/反查ICP.xlsx）：

   ```bash
   python hunter_ip.py -d "example.com" -o "结果.xlsx"
   ```

### 输出结果

查询结果将导出到Excel表格中，包含以下信息：

- 查询目标（域名或IP）
- 查询类型
- 企业名称
- 备案号
- 域名
- IP地址

## 2. Hunter ICP反查域名工具

### 功能介绍

本工具可以通过企业名称查询其拥有的域名资产，帮助了解企业的网络资产分布情况。支持单个企业查询和批量企业查询功能。

### 使用方法

#### 配置API密钥

在使用前，请先在脚本中的CONFIG字典里填写你的奇安信Hunter API密钥：

```python
CONFIG = {
    "api_key": "你的API密钥",  # 在此处填写您的奇安信Hunter API密钥
    # 其他配置...
}
```

#### 查询命令

1. **单个企业查询**：

   ```bash
   python hunter_icp.py -c "企业名称"
   ```

   例如：
   
   ```bash
   python hunter_icp.py -c "上海建设管理职业技术学院"
   ```

2. **批量企业查询**：

   ```bash
   python hunter_icp.py -f "文件路径"
   ```

   文件中每行包含一个企业名称。

3. **指定输出文件**（默认输出到：/结果/反查域名.xlsx）：

   ```bash
   python hunter_icp.py -c "企业名称" -o "结果.xlsx"
   ```

### 输出结果

查询结果将导出到Excel表格中，包含企业名称和对应的域名信息。

## 注意事项

1. API密钥安全：请妥善保管您的API密钥，避免泄露
2. 请求频率限制：API可能有请求频率限制，批量查询时建议适当设置延迟
3. 结果准确性：查询结果取决于奇安信Hunter数据库的更新情况
4. 合法使用：请确保在合法合规的情况下使用本工具

## 常见问题

**Q: 为什么查询结果为空？**  
A: 可能是API密钥无效、目标不在数据库中，或者查询格式不正确。

**Q: 如何提高批量查询效率？**  
A: 可以在CONFIG中调整`delay`参数，但请注意不要设置过小导致API请求被限制。

**Q: 如何处理API请求失败？**  
A: 脚本会自动重试，如果持续失败，请检查网络连接和API密钥有效性。
