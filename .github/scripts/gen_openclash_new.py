import os
import yaml
from urllib.parse import quote
from datetime import datetime

# ================= 配置常量 =================
SOURCE_BASE = "THEYAMLS"
OUTPUT_BASE = "Overwrite/THENEWOPENCLASH"
REPO_RAW = f"https://raw.githubusercontent.com/{os.getenv('GITHUB_REPOSITORY')}/main"

yaml.add_multi_constructor("!", lambda loader, suffix, node: None, Loader=yaml.SafeLoader)


def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")


def to_yaml_str(obj) -> str:
    """将 Python 对象序列化为 YAML 字符串，去除末尾空行"""
    return yaml.dump(obj, allow_unicode=True, default_flow_style=False, indent=2).rstrip()


def comment_lines(text: str, prefix: str = "# ") -> str:
    """给每行加注释前缀，空行只加 #"""
    result = []
    for line in text.splitlines():
        result.append(("# " + line) if line.strip() else "#")
    return "\n".join(result)


def section(title: str, body_lines: list) -> str:
    """生成一个带标题和分隔线的注释段落"""
    bar = "# " + "=" * 58
    lines = [bar, f"# {title}", bar]
    lines.extend(body_lines)
    return "\n".join(lines)


def build_yaml_block(data: dict, raw_url: str, filename: str) -> str:
    """
    生成完整的 [YAML] 块。

    按官方示例格式，每个操作符段落独立注释，取消注释即生效。
    内容分三部分：
      1. 操作符速查 + 常用示例（通用模板，全注释）
      2. proxy-providers 从源文件直接提取，用 proxy-providers: 顶层键写入（注释）
      3. 其他提取自源文件的内容（proxy-groups、rules、rule-providers 等，注释）
    """
    out = []

    # ── [YAML] 标记 ──────────────────────────────────────────
    out.append("# " + "=" * 58)
    out.append("# [YAML] 是新版 OpenClash 覆写模块的识别标记")
    out.append("# 此行本身不可注释，内容写在此标记之后")
    out.append("# 注释状态不生效；取消注释后重载覆写模块即可生效")
    out.append("# " + "=" * 58)
    out.append("[YAML]")
    out.append("")

    # ── 操作符速查 ────────────────────────────────────────────
    out.append("# " + "=" * 58)
    out.append("# 操作符速查")
    out.append("# " + "-" * 58)
    out.append("#  key       默认合并：Hash 递归合并，其他类型直接覆盖原值")
    out.append("#  key!      强制覆盖：整个值全部替换，不做任何合并")
    out.append("#  key+      数组后置追加：在数组末尾加入新元素")
    out.append("#  +key      数组前置插入：在数组开头插入（规则越靠前越优先匹配）")
    out.append("#  key-      数组差集删除：从数组移除指定元素；非数组则删除该键")
    out.append("#  key*      批量条件更新：配合 where/set，按条件匹配后批量修改")
    out.append("# " + "=" * 58)
    out.append("")

    # ── 示例一：追加 rule-provider + rule（官方示例格式）────
    out.append("# " + "=" * 58)
    out.append("# 示例：追加自定义 rule-provider 并在规则末尾加入对应规则")
    out.append("# 取消注释后，Steam 流量将走 Proxy 策略组")
    out.append("# " + "-" * 58)
    out.append("# +rule-providers:")
    out.append("#   Steam:")
    out.append("#     type: http")
    out.append("#     behavior: domain")
    out.append("#     format: mrs")
    out.append('#     url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/steam.mrs"')
    out.append("#     interval: 86400")
    out.append("# +rules:")
    out.append("#   - RULE-SET,Steam,Proxy")
    out.append("# " + "=" * 58)
    out.append("")

    # ── 示例二：前置插入高优先级规则 ─────────────────────────
    out.append("# " + "=" * 58)
    out.append("# 示例：在规则列表最前面插入高优先级规则（最先匹配）")
    out.append("# " + "-" * 58)
    out.append("# +rules:")
    out.append("#   - DOMAIN-SUFFIX,example.com,DIRECT")
    out.append("#   - IP-CIDR,192.168.0.0/16,DIRECT,no-resolve")
    out.append("# " + "=" * 58)
    out.append("")

    # ── 示例三：强制替换整个 rules ────────────────────────────
    out.append("# " + "=" * 58)
    out.append("# 示例：强制替换整个 rules 数组（原有规则全部丢弃）")
    out.append("# " + "-" * 58)
    out.append("# rules!:")
    out.append("#   - DOMAIN-SUFFIX,example.com,DIRECT")
    out.append("#   - MATCH,PROXY")
    out.append("# " + "=" * 58)
    out.append("")

    # ── 示例四：修改 dns 部分字段（其余字段保留）─────────────
    out.append("# " + "=" * 58)
    out.append("# 示例：修改 dns 配置中的部分字段，其余字段保持不变")
    out.append("# " + "-" * 58)
    out.append("# dns:")
    out.append("#   enable: true")
    out.append("#   cache-algorithm: lru")
    out.append("# " + "=" * 58)
    out.append("")

    # ── 示例五：给策略组追加节点 ─────────────────────────────
    out.append("# " + "=" * 58)
    out.append("# 示例：给所有 url-test 类型的策略组在 proxies 末尾追加节点")
    out.append("# " + "-" * 58)
    out.append("# proxy-groups*:")
    out.append("#   where:")
    out.append("#     type: url-test")
    out.append("#   set:")
    out.append("#     proxies+:")
    out.append("#       - '节点名称'")
    out.append("# " + "=" * 58)
    out.append("")

    # ================================================================
    # proxy-providers：从源文件提取，直接以正确的顶层键格式写出（注释）
    # ================================================================
    providers = data.get('proxy-providers', {})
    if providers:
        out.append("# " + "=" * 58)
        out.append("# proxy-providers（从源文件直接提取）")
        out.append("# " + "-" * 58)
        out.append("# 以下内容原样复制自源 YAML 的 proxy-providers 块。")
        out.append("# 使用方法：")
        out.append("#   1. 将需要替换的 provider 的 url: 改为你自己的订阅链接")
        out.append("#   2. 删除这整块前面的 # 号，保存后重载覆写模块即可")
        out.append("# " + "=" * 58)
        out.append("#")
        # 用 proxy-providers: 顶层键格式输出，这是正确的 [YAML] 块写法
        providers_yaml = to_yaml_str({'proxy-providers': providers})
        out.append(comment_lines(providers_yaml))
        out.append("")

    # ================================================================
    # proxy-groups：从源文件提取（注释）
    # ================================================================
    proxy_groups = data.get('proxy-groups', [])
    if proxy_groups:
        out.append("# " + "=" * 58)
        out.append("# proxy-groups（从源文件直接提取）")
        out.append("# " + "-" * 58)
        out.append("# 原始策略组配置，默认注释不启用。")
        out.append("# 如需覆写策略组，可取消注释后修改，或参考上方示例使用 proxy-groups* 条件更新。")
        out.append("# 直接取消注释将强制替换整个 proxy-groups（等同于 proxy-groups! 操作）。")
        out.append("# " + "=" * 58)
        out.append("#")
        groups_yaml = to_yaml_str({'proxy-groups': proxy_groups})
        out.append(comment_lines(groups_yaml))
        out.append("")

    # ================================================================
    # rule-providers：从源文件提取（注释）
    # ================================================================
    rule_providers = data.get('rule-providers', {})
    if rule_providers:
        out.append("# " + "=" * 58)
        out.append("# rule-providers（从源文件直接提取）")
        out.append("# " + "-" * 58)
        out.append("# 原始规则集配置，默认注释不启用。")
        out.append("# 如需追加新的 rule-provider，参考上方示例一使用 +rule-providers: 操作符。")
        out.append("# " + "=" * 58)
        out.append("#")
        rp_yaml = to_yaml_str({'rule-providers': rule_providers})
        out.append(comment_lines(rp_yaml))
        out.append("")

    # ================================================================
    # rules：从源文件提取（注释）
    # ================================================================
    rules = data.get('rules', [])
    if rules:
        out.append("# " + "=" * 58)
        out.append("# rules（从源文件直接提取）")
        out.append("# " + "-" * 58)
        out.append("# 原始规则列表，默认注释不启用。")
        out.append("# 常用操作：")
        out.append("#   +rules: [...]   在规则列表开头插入（优先匹配）")
        out.append("#   rules+: [...]   在规则列表末尾追加")
        out.append("#   rules!: [...]   强制替换整个规则列表（丢弃原有规则）")
        out.append("# 参考上方示例，通常不需要取消注释整个 rules，而是用 +rules/rules+ 追加即可。")
        out.append("# " + "=" * 58)
        out.append("#")
        rules_yaml = to_yaml_str({'rules': rules})
        out.append(comment_lines(rules_yaml))
        out.append("")

    # ================================================================
    # dns：从源文件提取（注释）
    # ================================================================
    dns = data.get('dns', {})
    if dns:
        out.append("# " + "=" * 58)
        out.append("# dns（从源文件直接提取）")
        out.append("# " + "-" * 58)
        out.append("# 原始 DNS 配置，默认注释不启用。")
        out.append("# 如只需修改部分字段，直接写需要修改的键值即可（默认合并，不影响其他字段）。")
        out.append("# 如需完整替换 DNS 配置，使用 dns!: 操作符。")
        out.append("# " + "=" * 58)
        out.append("#")
        dns_yaml = to_yaml_str({'dns': dns})
        out.append(comment_lines(dns_yaml))
        out.append("")

    return "\n".join(out)


def gen_openclash_new():
    print("🚀 开始生成新版 OpenClash 覆写配置（[YAML] 块格式）...")
    os.makedirs(OUTPUT_BASE, exist_ok=True)

    total_count = 0
    categories = {}

    for root, dirs, files in os.walk(SOURCE_BASE):
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            if not file.endswith(('.yaml', '.yml')):
                continue

            full_path = os.path.join(root, file)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    raw_text = f.read()
                    data = yaml.safe_load(raw_text)

                if not isinstance(data, dict):
                    continue

                providers = data.get('proxy-providers', {})
                if not providers:
                    continue

                rel_dir = os.path.relpath(root, SOURCE_BASE)
                out_dir = os.path.join(OUTPUT_BASE, rel_dir)
                os.makedirs(out_dir, exist_ok=True)

                raw_url = f"{REPO_RAW}/{quote(f'{SOURCE_BASE}/{rel_dir}/{file}'.replace(os.sep, '/'))}"
                out_name = os.path.splitext(file)[0] + ".yaml"
                out_file = os.path.join(out_dir, out_name)
                provider_keys = list(providers.keys())

                header = "\n".join([
                    f"# OpenClash 覆写模块 - {file}",
                    f"# 生成日期：{get_current_date()}",
                    f"# 源文件：{raw_url}",
                    "# 格式：新版 OpenClash [YAML] 块覆写",
                    "#",
                    "# 本文件仅包含 [YAML] 块覆写内容，不含任何 [General] 插件设置。",
                    "# 所有内容默认注释，不影响现有配置；取消注释对应段落即可启用该覆写。",
                    "",
                ])

                content = header + build_yaml_block(data, raw_url, file)

                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                if rel_dir not in categories:
                    categories[rel_dir] = []
                categories[rel_dir].append({
                    'name': out_name,
                    'source': file,
                    'providers': provider_keys,
                    'raw_url': f"{REPO_RAW}/{quote(f'{OUTPUT_BASE}/{rel_dir}/{out_name}'.replace(os.sep, '/'))}"
                })

                total_count += 1
                print(f"  ✅ 生成: {out_file}  (providers: {', '.join(provider_keys)})")

            except Exception as e:
                print(f"  ⚠️ 处理出错 {file}: {e}")

    # ==== 分类 README ====
    for cat, items in categories.items():
        cat_path = os.path.join(OUTPUT_BASE, cat)
        readme_lines = [
            f"# 📁 {cat}",
            "",
            "新版 OpenClash 覆写模块（[YAML] 块格式）。所有内容默认注释，不影响现有配置。",
            "",
            "| 文件名 | proxy-providers | Raw 链接 |",
            "| :--- | :--- | :--- |",
        ]
        for item in sorted(items, key=lambda x: x['name']):
            prov_str = "、".join(item['providers'])
            readme_lines.append(
                f"| **{item['name']}** | {prov_str} | [下载/查看]({item['raw_url']}) |"
            )
        readme_lines += ["", "---", "[🔙 返回总览](../README.md)"]
        with open(os.path.join(cat_path, "README.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(readme_lines))

    # ==== 主 README ====
    main_readme = [
        "# 📦 OpenClash 新版覆写模块",
        "",
        "基于新版 OpenClash `[YAML]` 块覆写格式自动生成。",
        "",
        "**设计原则：**",
        "- 所有覆写内容默认全部注释，加载后对现有配置零影响",
        "- `proxy-providers` / `proxy-groups` / `rules` / `rule-providers` / `dns`",
        "  均从源文件直接提取并以正确格式写入，对照修改后取消注释即可启用",
        "- 内置常用操作符示例（追加规则、插入节点等），参考后按需取消注释",
        "",
        "| | 旧版 `.conf` | 新版 `.yaml` |",
        "| :--- | :--- | :--- |",
        "| url 替换 | `ruby_map_edit` + `$EN_KEY` 环境变量 | 直接修改 `proxy-providers:` 块中的 `url:` 字段 |",
        "| 修改能力 | 仅能替换指定路径的值 | 合并 / 强制覆盖 / 追加 / 删除 / 批量条件更新 |",
        "| 默认行为 | 启用后立即覆写 | 全部注释，零影响，取消注释即启用 |",
        "",
        "## 📂 目录",
        "",
        "| 分类 | 文件数 |",
        "| :--- | :--- |",
    ]
    for cat in sorted(categories.keys()):
        main_readme.append(f"| 📁 **[{cat}](./{cat}/README.md)** | {len(categories[cat])} 个 |")

    main_readme += [
        "",
        "## 🚀 使用方法",
        "",
        "1. 复制对应 `.yaml` 文件的 Raw URL",
        "2. OpenClash → 覆写设置 → 覆写模块 → 添加 URL",
        "3. 打开文件，找到 `proxy-providers:` 段落",
        "4. 将对应 provider 的 `url:` 值改为你的订阅链接",
        "5. 删除该段落前面所有行的 `# ` 前缀，保存后重载模块生效",
        "",
        "[🏠 返回主页](../../README.md)",
    ]

    with open(os.path.join(OUTPUT_BASE, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(main_readme))

    print(f"✅ 完成！共生成 {total_count} 个覆写文件。")


if __name__ == "__main__":
    gen_openclash_new()
