"""
数据库迁移脚本
将分散的 .db 文件迁移到统一的 data/ 目录结构
"""
import sqlite3
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

OLD_DB_MAPPING = {
    "core.db": {
        "source_files": ["users.db", "api_keys.db", "chat_history.db", "analytics.db"],
        "description": "核心业务数据"
    },
    "knowledge.db": {
        "source_files": ["documents.db", "feedback.db", "code_analysis.db"],
        "description": "知识库数据"
    },
    "ai.db": {
        "source_files": ["knowledge_graph.db", "mentor.db", "recommendation.db"],
        "description": "AI 功能数据"
    },
    "community.db": {
        "source_files": ["community.db"],
        "description": "社区数据"
    },
    "sync.db": {
        "source_files": ["sync_config.db", "github_repos.db"],
        "description": "同步配置数据"
    }
}


def get_tables_from_db(db_path: Path) -> list:
    """获取数据库中的所有表名"""
    if not db_path.exists():
        return []
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables


def get_table_schema(db_path: Path, table_name: str) -> str:
    """获取表的创建语句"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def migrate_table(source_db: Path, target_db: Path, table_name: str):
    """迁移单个表"""
    source_conn = sqlite3.connect(str(source_db))
    target_conn = sqlite3.connect(str(target_db))
    
    cursor = target_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    )
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        schema = get_table_schema(source_db, table_name)
        if schema:
            target_conn.execute(schema)
    
    cursor = source_conn.execute(f"SELECT * FROM {table_name}")
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    
    if rows:
        placeholders = ", ".join(["?" for _ in columns])
        column_names = ", ".join(columns)
        target_conn.executemany(
            f"INSERT OR IGNORE INTO {table_name} ({column_names}) VALUES ({placeholders})",
            rows
        )
    
    target_conn.commit()
    source_conn.close()
    target_conn.close()
    print(f"  ✓ 迁移表: {table_name} ({len(rows)} 条记录)")


def migrate_databases():
    """执行数据库迁移"""
    print("=" * 60)
    print("开始数据库迁移...")
    print("=" * 60)
    
    for target_db_name, config in OLD_DB_MAPPING.items():
        target_path = DATA_DIR / target_db_name
        
        if target_path.exists():
            print(f"\n[跳过] {target_db_name} 已存在")
            continue
        
        print(f"\n[创建] {target_db_name} - {config['description']}")
        
        for source_file in config["source_files"]:
            source_path = BASE_DIR / source_file
            
            if not source_path.exists():
                print(f"  - 源文件不存在: {source_file}")
                continue
            
            tables = get_tables_from_db(source_path)
            print(f"  源: {source_file} ({len(tables)} 个表)")
            
            for table in tables:
                migrate_table(source_path, target_path, table)
    
    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)
    
    print("\n新数据库结构:")
    for db_file in DATA_DIR.glob("*.db"):
        tables = get_tables_from_db(db_file)
        size = db_file.stat().st_size / 1024
        print(f"  {db_file.name}: {len(tables)} 个表, {size:.1f} KB")


def backup_old_databases():
    """备份旧数据库文件"""
    backup_dir = BASE_DIR / "db_backup"
    backup_dir.mkdir(exist_ok=True)
    
    print("\n备份旧数据库文件到:", backup_dir)
    
    for db_file in BASE_DIR.glob("*.db"):
        if db_file.name == "chroma.db":
            continue
        target = backup_dir / db_file.name
        shutil.copy2(db_file, target)
        print(f"  ✓ 备份: {db_file.name}")


if __name__ == "__main__":
    migrate_databases()
    backup_old_databases()
