#!/usr/bin/env python3
"""
Split V16 database DDL into individual SQL files for V17 delivery.
Reads the complete V16 markdown and extracts each section's SQL into separate files.
"""
import re
import os

source_path = "/home/jim/DevFlow/projects/devflow/docs/devflow_DATABASE_V16.md"
output_dir = "/home/jim/DevFlow/projects/devflow/docs/sql"

os.makedirs(output_dir, exist_ok=True)

with open(source_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Map section numbers to file names and descriptions
section_files = {
    '2.1': ('01-enums.sql', '基础设置 - 扩展与枚举类型定义'),
    '2.2': ('02-users.sql', '用户表'),
    '2.3': ('03-projects.sql', '项目表'),
    '2.4': ('04-requirements.sql', '需求表（软件需求说明书）'),
    '2.5': ('05-agents.sql', 'Agent角色表'),
    '2.6': ('06-tasks.sql', '任务表'),
    '2.7': ('07-task-dependencies.sql', '任务依赖表'),
    '2.8': ('08-agent-execution-logs.sql', 'Agent执行日志表'),
    '2.9': ('09-qa-records.sql', 'QA检验记录表'),
    '2.10': ('10-groups.sql', '群组表'),
    '2.11': ('11-group-members.sql', '群组-成员关联表'),
    '2.12': ('12-group-messages.sql', '群聊消息表'),
    '2.13': ('13-meeting-outcomes.sql', '会议结果表'),
    '2.14': ('14-swarms.sql', 'Agent蜂群表'),
    '2.15': ('15-swarm-members.sql', '蜂群-成员关联表'),
    '2.16': ('16-notifications.sql', '通知表'),
    '2.17': ('17-repos.sql', '代码仓库表'),
    '2.18': ('18-repo-branches.sql', '分支表'),
    '2.19': ('19-pull-requests.sql', 'Pull Request表'),
    '2.20': ('20-commits.sql', '提交记录表'),
    '2.21': ('21-task-commits.sql', '任务与提交关联表'),
}

# Extract content between section headings for each target section
# Strategy: split by ### headings, then extract SQL blocks + comments for each

# Split content by ### section headings
section_pattern = r'^(###\s+(.+?))\n'
parts = re.split(section_pattern, content, flags=re.MULTILINE)

# parts[0] is content before first ###
# Then alternating: full_heading, section_name, body, full_heading, section_name, body...
section_map = {}
for i in range(1, len(parts) - 1, 3):
    if i + 2 < len(parts):
        full_heading = parts[i]
        section_name = parts[i+1]
        body = parts[i+2]
        # Extract section number from heading
        num_match = re.match(r'(\d+\.\d+)', section_name.strip())
        if num_match:
            section_num = num_match.group(1)
            section_map[section_num] = body
            print(f"  Section {section_num} ({section_name.strip()[:50]}): {len(body)} chars")

# Write each section's SQL to separate files
for section_num, (filename, description) in section_files.items():
    if section_num not in section_map:
        print(f"  WARNING: Section {section_num} not found in source!")
        continue

    body = section_map[section_num]
    
    # Extract SQL code blocks and inline comments from the section body
    sql_blocks = re.findall(r'```sql\n(.*?)```', body, re.DOTALL)
    # Also get comments between code blocks
    non_sql = re.split(r'```sql\n.*?```', body, flags=re.DOTALL)
    
    sql_content = f"-- ============================================================\n"
    sql_content += f"-- DevFlow DATABASE V17 - {description}\n"
    sql_content += f"-- File: {filename}\n"
    sql_content += f"-- Source: section {section_num} of devflow_DATABASE_V16.md\n"
    sql_content += f"-- ============================================================\n\n"
    
    # Include the full body content with SQL blocks and comments
    # Strip the section heading markdown but keep comments and SQL
    cleaned_body = body
    # Remove the ### heading line itself
    cleaned_body = re.sub(r'^###\s+.*?\n', '', cleaned_body, count=1)
    # Remove ```sql and ``` markers, keeping SQL content
    cleaned_body = re.sub(r'```sql\n', '', cleaned_body)
    cleaned_body = re.sub(r'```$', '', cleaned_body, flags=re.MULTILINE)
    # Remove empty ``` lines
    cleaned_body = re.sub(r'^```\s*$', '', cleaned_body, flags=re.MULTILINE)
    
    sql_content += cleaned_body.strip() + '\n'
    
    file_path = os.path.join(output_dir, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(sql_content)
    print(f"  Written: {filename} ({len(sql_content)} chars)")

# Now handle the non-section files (views, init data, permissions, soft delete)

# Section 3: Views
section3_match = re.search(r'## 3\. 视图和存储过程\n(.*?)(?=## \d+\.|\Z)', content, re.DOTALL)
if section3_match:
    views_content = section3_match.group(1)
    sql = "-- ============================================================\n"
    sql += "-- DevFlow DATABASE V17 - 视图定义\n"
    sql += "-- File: 99-views.sql\n"
    sql += "-- Source: section 3 of devflow_DATABASE_V16.md\n"
    sql += "-- ============================================================\n\n"
    sql += re.sub(r'^###\s+.*?\n', '', views_content, flags=re.MULTILINE)
    sql = re.sub(r'```sql\n', '', sql)
    sql = re.sub(r'```$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'^```\s*$', '', sql, flags=re.MULTILINE)
    with open(os.path.join(output_dir, '99-views.sql'), 'w', encoding='utf-8') as f:
        f.write(sql.strip() + '\n')
    print(f"  Written: 99-views.sql ({len(sql)} chars)")

# Section 4: Init data
section4_match = re.search(r'## 4\. 数据初始化\n(.*?)(?=## \d+\.|\Z)', content, re.DOTALL)
if section4_match:
    init_content = section4_match.group(1)
    sql = "-- ============================================================\n"
    sql += "-- DevFlow DATABASE V17 - 数据初始化\n"
    sql += "-- File: 98-init-data.sql\n"
    sql += "-- Source: section 4 of devflow_DATABASE_V16.md\n"
    sql += "-- ============================================================\n\n"
    sql += re.sub(r'^###\s+.*?\n', '', init_content, flags=re.MULTILINE)
    sql = re.sub(r'```sql\n', '', sql)
    sql = re.sub(r'```$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'^```\s*$', '', sql, flags=re.MULTILINE)
    with open(os.path.join(output_dir, '98-init-data.sql'), 'w', encoding='utf-8') as f:
        f.write(sql.strip() + '\n')
    print(f"  Written: 98-init-data.sql ({len(sql)} chars)")

# Section 5: Permissions
section5_match = re.search(r'## 5\. 权限设置\n(.*?)(?=## \d+\.|\Z)', content, re.DOTALL)
if section5_match:
    perm_content = section5_match.group(1)
    sql = "-- ============================================================\n"
    sql += "-- DevFlow DATABASE V17 - 数据库权限设置\n"
    sql += "-- File: 97-permissions.sql\n"
    sql += "-- Source: section 5 of devflow_DATABASE_V16.md\n"
    sql += "-- ============================================================\n\n"
    sql = re.sub(r'```sql\n', '', perm_content)
    sql = re.sub(r'```$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'^```\s*$', '', sql, flags=re.MULTILINE)
    with open(os.path.join(output_dir, '97-permissions.sql'), 'w', encoding='utf-8') as f:
        f.write(sql.strip() + '\n')
    print(f"  Written: 97-permissions.sql ({len(sql)} chars)")

# Section 6: Soft delete
section6_match = re.search(r'## 6\. 软删除说明\n(.*?)(?=## \d+\.|\Z)', content, re.DOTALL)
if section6_match:
    sdel_content = section6_match.group(1)
    sql = "-- ============================================================\n"
    sql += "-- DevFlow DATABASE V17 - 软删除说明与物理清理存储过程\n"
    sql += "-- File: 96-soft-delete-cleanup.sql\n"
    sql += "-- Source: section 6 of devflow_DATABASE_V16.md\n"
    sql += "-- ============================================================\n\n"
    # Include the markdown description as SQL comments
    desc_part = re.sub(r'^###\s+.*?\n', '', sdel_content, flags=re.MULTILINE)
    # Convert markdown bullets to SQL comments
    lines = desc_part.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- **') or stripped.startswith('- ') or stripped.startswith('**'):
            result.append(f"-- {stripped.strip('* ')}")
        elif stripped.startswith('###'):
            result.append(f"-- {stripped}")
        else:
            result.append(line)
    desc_sql = '\n'.join(result)
    desc_sql = re.sub(r'```sql\n', '', desc_sql)
    desc_sql = re.sub(r'```$', '', desc_sql, flags=re.MULTILINE)
    desc_sql = re.sub(r'^```\s*$', '', desc_sql, flags=re.MULTILINE)
    sql += desc_sql.strip() + '\n'
    with open(os.path.join(output_dir, '96-soft-delete-cleanup.sql'), 'w', encoding='utf-8') as f:
        f.write(sql.strip() + '\n')
    print(f"  Written: 96-soft-delete-cleanup.sql ({len(sql)} chars)")

print("\nDone! All SQL files created.")
