# 饮食数据库字典（临时空库初始化并执行001～004后提取）

profiles 是成员A维护的共享依赖；diet_records为基础表增量扩展。下列包含17张饮食相关表（含迁移登记表）及profiles依赖。所有DDL仅在临时库运行；本次没有升级正式库。
数据库只约束部分格式，日期、有限数、枚举组合和来源规则还由Pydantic/服务层校验。SQLite PRAGMA中主键notnull=0不表示允许业务NULL，最终以SQL和主键语义为准。

## profiles

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| display_name | TEXT | 1 | NULL | 0 |
| height_cm | REAL | 0 | NULL | 0 |
| weight_kg | REAL | 0 | NULL | 0 |
| medical_history | TEXT | 1 | '' | 0 |
| allergies | TEXT | 1 | '' | 0 |
| medications | TEXT | 1 | '' | 0 |
| preferences | TEXT | 1 | '' | 0 |
| created_at | TEXT | 1 | strftime('%Y-%m-%dT%H:%M:%SZ', 'now') | 0 |
| updated_at | TEXT | 1 | strftime('%Y-%m-%dT%H:%M:%SZ', 'now') | 0 |

### 外键

```json
[]
```

### DDL 与约束

```sql
CREATE TABLE profiles (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    display_name TEXT NOT NULL CHECK (length(trim(display_name)) BETWEEN 1 AND 50),
    height_cm REAL CHECK (height_cm > 0),
    weight_kg REAL CHECK (weight_kg > 0),
    medical_history TEXT NOT NULL DEFAULT '',
    allergies TEXT NOT NULL DEFAULT '',
    medications TEXT NOT NULL DEFAULT '',
    preferences TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
```

### 索引


## diet_records

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | 1 | 0 |
| record_date | TEXT | 1 | NULL | 0 |
| meal_type | TEXT | 1 | NULL | 0 |
| food_name | TEXT | 1 | NULL | 0 |
| amount_g | REAL | 1 | NULL | 0 |
| calories_kcal | REAL | 0 | NULL | 0 |
| notes | TEXT | 1 | '' | 0 |
| created_at | TEXT | 1 | strftime('%Y-%m-%dT%H:%M:%SZ', 'now') | 0 |
| updated_at | TEXT | 1 | strftime('%Y-%m-%dT%H:%M:%SZ', 'now') | 0 |
| food_id | INTEGER | 0 | NULL | 0 |
| nutrition_mode | TEXT | 1 | 'manual' | 0 |
| protein_g | REAL | 0 | NULL | 0 |
| fat_g | REAL | 0 | NULL | 0 |
| carbohydrate_g | REAL | 0 | NULL | 0 |
| snapshot_calories_per_100g | REAL | 0 | NULL | 0 |
| snapshot_protein_g_per_100g | REAL | 0 | NULL | 0 |
| snapshot_fat_g_per_100g | REAL | 0 | NULL | 0 |
| snapshot_carbohydrate_g_per_100g | REAL | 0 | NULL | 0 |
| food_version_at | TEXT | 0 | NULL | 0 |
| nutrition_source_note | TEXT | 1 | '' | 0 |
| is_example | INTEGER | 1 | 0 | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "food_items",
    "from": "food_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "SET NULL",
    "match": "NONE"
  },
  {
    "id": 1,
    "seq": 0,
    "table": "profiles",
    "from": "profile_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE diet_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
    record_date TEXT NOT NULL,
    meal_type TEXT NOT NULL CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    food_name TEXT NOT NULL CHECK (length(trim(food_name)) BETWEEN 1 AND 100),
    amount_g REAL NOT NULL CHECK (amount_g > 0),
    calories_kcal REAL CHECK (calories_kcal >= 0),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
, food_id INTEGER REFERENCES food_items(id) ON DELETE SET NULL, nutrition_mode TEXT NOT NULL DEFAULT 'manual' CHECK(nutrition_mode IN ('manual','catalog')), protein_g REAL CHECK(protein_g >= 0), fat_g REAL CHECK(fat_g >= 0), carbohydrate_g REAL CHECK(carbohydrate_g >= 0), snapshot_calories_per_100g REAL CHECK(snapshot_calories_per_100g >= 0), snapshot_protein_g_per_100g REAL CHECK(snapshot_protein_g_per_100g >= 0), snapshot_fat_g_per_100g REAL CHECK(snapshot_fat_g_per_100g >= 0), snapshot_carbohydrate_g_per_100g REAL CHECK(snapshot_carbohydrate_g_per_100g >= 0), food_version_at TEXT, nutrition_source_note TEXT NOT NULL DEFAULT '', is_example INTEGER NOT NULL DEFAULT 0 CHECK(is_example IN (0,1)));
```

### 索引

- `idx_diet_profile_food`：CREATE INDEX idx_diet_profile_food ON diet_records(profile_id, food_id)
- `idx_diet_profile_date`：CREATE INDEX idx_diet_profile_date ON diet_records(profile_id, record_date)

## food_categories

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | 1 | 0 |
| name | TEXT | 1 | NULL | 0 |
| name_key | TEXT | 1 | NULL | 0 |
| created_at | TEXT | 1 | NULL | 0 |
| updated_at | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "profiles",
    "from": "profile_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE food_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 50),
        name_key TEXT NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(profile_id, name_key)
    );
```

### 索引

- `sqlite_autoindex_food_categories_1`：SQLite自动生成的主键/唯一约束索引

## food_items

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | 1 | 0 |
| category_id | INTEGER | 0 | NULL | 0 |
| name | TEXT | 1 | NULL | 0 |
| calories_per_100g | REAL | 0 | NULL | 0 |
| protein_g_per_100g | REAL | 0 | NULL | 0 |
| fat_g_per_100g | REAL | 0 | NULL | 0 |
| carbohydrate_g_per_100g | REAL | 0 | NULL | 0 |
| source_type | TEXT | 1 | 'user_entered' | 0 |
| source_note | TEXT | 1 | '' | 0 |
| source_url | TEXT | 1 | '' | 0 |
| is_example | INTEGER | 1 | 0 | 0 |
| deleted_at | TEXT | 0 | NULL | 0 |
| created_at | TEXT | 1 | NULL | 0 |
| updated_at | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "food_categories",
    "from": "category_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "SET NULL",
    "match": "NONE"
  },
  {
    "id": 1,
    "seq": 0,
    "table": "profiles",
    "from": "profile_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE food_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
        category_id INTEGER REFERENCES food_categories(id) ON DELETE SET NULL,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100),
        calories_per_100g REAL CHECK(calories_per_100g >= 0),
        protein_g_per_100g REAL CHECK(protein_g_per_100g >= 0),
        fat_g_per_100g REAL CHECK(fat_g_per_100g >= 0),
        carbohydrate_g_per_100g REAL CHECK(carbohydrate_g_per_100g >= 0),
        source_type TEXT NOT NULL DEFAULT 'user_entered' CHECK(source_type IN ('user_entered','referenced','example')),
        source_note TEXT NOT NULL DEFAULT '', source_url TEXT NOT NULL DEFAULT '',
        is_example INTEGER NOT NULL DEFAULT 0 CHECK(is_example IN (0,1)),
        deleted_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        CHECK((source_type = 'example') = (is_example = 1))
    );
```

### 索引

- `idx_food_items_profile_name`：CREATE INDEX idx_food_items_profile_name ON food_items(profile_id, name)
- `idx_food_items_profile_active_category`：CREATE INDEX idx_food_items_profile_active_category ON food_items(profile_id, deleted_at, category_id)

## diet_daily_goals

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | 1 | 0 |
| effective_from | TEXT | 1 | NULL | 0 |
| calories_kcal | REAL | 0 | NULL | 0 |
| protein_g | REAL | 0 | NULL | 0 |
| fat_g | REAL | 0 | NULL | 0 |
| carbohydrate_g | REAL | 0 | NULL | 0 |
| water_ml | REAL | 0 | NULL | 0 |
| created_at | TEXT | 1 | NULL | 0 |
| updated_at | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "profiles",
    "from": "profile_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE diet_daily_goals (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
 effective_from TEXT NOT NULL,
 calories_kcal REAL CHECK(calories_kcal > 0),
 protein_g REAL CHECK(protein_g > 0),
 fat_g REAL CHECK(fat_g > 0),
 carbohydrate_g REAL CHECK(carbohydrate_g > 0),
 water_ml REAL CHECK(water_ml > 0),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(profile_id,effective_from)
);
```

### 索引

- `sqlite_autoindex_diet_daily_goals_1`：SQLite自动生成的主键/唯一约束索引

## water_records

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | 1 | 0 |
| drank_at | TEXT | 1 | NULL | 0 |
| amount_ml | INTEGER | 1 | NULL | 0 |
| notes | TEXT | 1 | '' | 0 |
| created_at | TEXT | 1 | NULL | 0 |
| updated_at | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "profiles",
    "from": "profile_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE water_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
        drank_at TEXT NOT NULL,
        amount_ml INTEGER NOT NULL CHECK(typeof(amount_ml)='integer' AND amount_ml>0 AND amount_ml<=1000000),
        notes TEXT NOT NULL DEFAULT '' CHECK(length(notes)<=2000),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
```

### 索引

- `idx_water_profile_time`：CREATE INDEX idx_water_profile_time ON water_records(profile_id,drank_at)

## water_reminder_settings

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| profile_id | INTEGER | 0 | NULL | 1 |
| enabled | INTEGER | 1 | 0 | 0 |
| mode | TEXT | 1 | NULL | 0 |
| fixed_times_json | TEXT | 1 | '[]' | 0 |
| interval_minutes | INTEGER | 1 | NULL | 0 |
| active_start | TEXT | 1 | NULL | 0 |
| active_end | TEXT | 1 | NULL | 0 |
| pause_when_goal_met | INTEGER | 1 | 1 | 0 |
| created_at | TEXT | 1 | NULL | 0 |
| updated_at | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "profiles",
    "from": "profile_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE water_reminder_settings (
        profile_id INTEGER PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
        enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
        mode TEXT NOT NULL CHECK(mode IN ('fixed_times','interval')),
        fixed_times_json TEXT NOT NULL DEFAULT '[]',
        interval_minutes INTEGER NOT NULL CHECK(interval_minutes BETWEEN 1 AND 1440),
        active_start TEXT NOT NULL, active_end TEXT NOT NULL CHECK(active_end>active_start),
        pause_when_goal_met INTEGER NOT NULL DEFAULT 1 CHECK(pause_when_goal_met IN (0,1)),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
```

### 索引


## diet_recipe_categories

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | NULL | 0 |
| name | TEXT | 1 | NULL | 0 |
| name_key | TEXT | 1 | NULL | 0 |
| created_at | TEXT | 1 | NULL | 0 |
| updated_at | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "profiles",
    "from": "profile_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE diet_recipe_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 50), name_key TEXT NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(profile_id,name_key), UNIQUE(profile_id,id));
```

### 索引

- `sqlite_autoindex_diet_recipe_categories_2`：SQLite自动生成的主键/唯一约束索引
- `sqlite_autoindex_diet_recipe_categories_1`：SQLite自动生成的主键/唯一约束索引

## diet_recipes

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | NULL | 0 |
| category_id | INTEGER | 0 | NULL | 0 |
| name | TEXT | 1 | NULL | 0 |
| description | TEXT | 1 | '' | 0 |
| servings | REAL | 1 | NULL | 0 |
| preparation_minutes | INTEGER | 0 | NULL | 0 |
| nutrition_mode | TEXT | 1 | NULL | 0 |
| manual_calories_kcal | REAL | 0 | NULL | 0 |
| manual_protein_g | REAL | 0 | NULL | 0 |
| manual_fat_g | REAL | 0 | NULL | 0 |
| manual_carbohydrate_g | REAL | 0 | NULL | 0 |
| source_type | TEXT | 1 | NULL | 0 |
| source_note | TEXT | 1 | '' | 0 |
| source_url | TEXT | 1 | '' | 0 |
| revision | INTEGER | 1 | 1 | 0 |
| archived_at | TEXT | 0 | NULL | 0 |
| created_at | TEXT | 1 | NULL | 0 |
| updated_at | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "diet_recipe_categories",
    "from": "profile_id",
    "to": "profile_id",
    "on_update": "NO ACTION",
    "on_delete": "NO ACTION",
    "match": "NONE"
  },
  {
    "id": 0,
    "seq": 1,
    "table": "diet_recipe_categories",
    "from": "category_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "NO ACTION",
    "match": "NONE"
  },
  {
    "id": 1,
    "seq": 0,
    "table": "profiles",
    "from": "profile_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE diet_recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        category_id INTEGER, name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100), description TEXT NOT NULL DEFAULT '',
        servings REAL NOT NULL CHECK(servings>0), preparation_minutes INTEGER CHECK(preparation_minutes>=0),
        nutrition_mode TEXT NOT NULL CHECK(nutrition_mode IN ('calculated','manual')),
        manual_calories_kcal REAL CHECK(manual_calories_kcal>=0), manual_protein_g REAL CHECK(manual_protein_g>=0),
        manual_fat_g REAL CHECK(manual_fat_g>=0), manual_carbohydrate_g REAL CHECK(manual_carbohydrate_g>=0),
        source_type TEXT NOT NULL CHECK(source_type IN ('user_entered','referenced','example')),
        source_note TEXT NOT NULL DEFAULT '', source_url TEXT NOT NULL DEFAULT '',
        revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0), archived_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(profile_id,id), FOREIGN KEY(profile_id,category_id) REFERENCES diet_recipe_categories(profile_id,id));
```

### 索引

- `idx_recipe_profile_name`：CREATE INDEX idx_recipe_profile_name ON diet_recipes(profile_id,name)
- `idx_recipe_profile_active_category`：CREATE INDEX idx_recipe_profile_active_category ON diet_recipes(profile_id,archived_at,category_id)
- `sqlite_autoindex_diet_recipes_1`：SQLite自动生成的主键/唯一约束索引

## diet_recipe_ingredients

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | NULL | 0 |
| recipe_id | INTEGER | 1 | NULL | 0 |
| food_id | INTEGER | 1 | NULL | 0 |
| amount_g | REAL | 1 | NULL | 0 |
| position | INTEGER | 1 | NULL | 0 |
| food_name_snapshot | TEXT | 1 | NULL | 0 |
| calories_per_100g_snapshot | REAL | 0 | NULL | 0 |
| protein_g_per_100g_snapshot | REAL | 0 | NULL | 0 |
| fat_g_per_100g_snapshot | REAL | 0 | NULL | 0 |
| carbohydrate_g_per_100g_snapshot | REAL | 0 | NULL | 0 |
| food_updated_at_snapshot | TEXT | 1 | NULL | 0 |
| source_snapshot | TEXT | 1 | NULL | 0 |
| is_example | INTEGER | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "diet_recipes",
    "from": "profile_id",
    "to": "profile_id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  },
  {
    "id": 0,
    "seq": 1,
    "table": "diet_recipes",
    "from": "recipe_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  },
  {
    "id": 1,
    "seq": 0,
    "table": "food_items",
    "from": "food_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "NO ACTION",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE diet_recipe_ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL, recipe_id INTEGER NOT NULL,
        food_id INTEGER NOT NULL REFERENCES food_items(id), amount_g REAL NOT NULL CHECK(amount_g>0), position INTEGER NOT NULL CHECK(position>0),
        food_name_snapshot TEXT NOT NULL, calories_per_100g_snapshot REAL CHECK(calories_per_100g_snapshot>=0),
        protein_g_per_100g_snapshot REAL CHECK(protein_g_per_100g_snapshot>=0), fat_g_per_100g_snapshot REAL CHECK(fat_g_per_100g_snapshot>=0),
        carbohydrate_g_per_100g_snapshot REAL CHECK(carbohydrate_g_per_100g_snapshot>=0),
        food_updated_at_snapshot TEXT NOT NULL, source_snapshot TEXT NOT NULL, is_example INTEGER NOT NULL CHECK(is_example IN (0,1)),
        UNIQUE(recipe_id,food_id), UNIQUE(recipe_id,position),
        FOREIGN KEY(profile_id,recipe_id) REFERENCES diet_recipes(profile_id,id) ON DELETE CASCADE);
```

### 索引

- `idx_recipe_food`：CREATE INDEX idx_recipe_food ON diet_recipe_ingredients(profile_id,food_id)
- `sqlite_autoindex_diet_recipe_ingredients_2`：SQLite自动生成的主键/唯一约束索引
- `sqlite_autoindex_diet_recipe_ingredients_1`：SQLite自动生成的主键/唯一约束索引

## diet_recipe_steps

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | NULL | 0 |
| recipe_id | INTEGER | 1 | NULL | 0 |
| position | INTEGER | 1 | NULL | 0 |
| instruction | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "diet_recipes",
    "from": "profile_id",
    "to": "profile_id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  },
  {
    "id": 0,
    "seq": 1,
    "table": "diet_recipes",
    "from": "recipe_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE diet_recipe_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL, recipe_id INTEGER NOT NULL,
        position INTEGER NOT NULL CHECK(position>0), instruction TEXT NOT NULL CHECK(length(trim(instruction))>0),
        UNIQUE(recipe_id,position), FOREIGN KEY(profile_id,recipe_id) REFERENCES diet_recipes(profile_id,id) ON DELETE CASCADE);
```

### 索引

- `sqlite_autoindex_diet_recipe_steps_1`：SQLite自动生成的主键/唯一约束索引

## diet_inventory_items

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | NULL | 0 |
| food_id | INTEGER | 1 | NULL | 0 |
| quantity_g | REAL | 1 | NULL | 0 |
| notes | TEXT | 1 | '' | 0 |
| revision | INTEGER | 1 | 1 | 0 |
| created_at | TEXT | 1 | NULL | 0 |
| updated_at | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "food_items",
    "from": "food_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "NO ACTION",
    "match": "NONE"
  },
  {
    "id": 1,
    "seq": 0,
    "table": "profiles",
    "from": "profile_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE diet_inventory_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        food_id INTEGER NOT NULL REFERENCES food_items(id), quantity_g REAL NOT NULL CHECK(quantity_g>=0), notes TEXT NOT NULL DEFAULT '',
        revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0), created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(profile_id,food_id));
```

### 索引

- `sqlite_autoindex_diet_inventory_items_1`：SQLite自动生成的主键/唯一约束索引

## diet_ingredient_terms

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | NULL | 0 |
| name | TEXT | 1 | NULL | 0 |
| name_key | TEXT | 1 | NULL | 0 |
| kind | TEXT | 1 | NULL | 0 |
| archived_at | TEXT | 0 | NULL | 0 |
| created_at | TEXT | 1 | NULL | 0 |
| updated_at | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "profiles",
    "from": "profile_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE diet_ingredient_terms (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100), name_key TEXT NOT NULL,
        kind TEXT NOT NULL CHECK(kind IN ('ingredient','allergen')), archived_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(profile_id,name_key), UNIQUE(profile_id,id));
```

### 索引

- `sqlite_autoindex_diet_ingredient_terms_2`：SQLite自动生成的主键/唯一约束索引
- `sqlite_autoindex_diet_ingredient_terms_1`：SQLite自动生成的主键/唯一约束索引

## diet_ingredient_aliases

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | NULL | 0 |
| term_id | INTEGER | 1 | NULL | 0 |
| alias | TEXT | 1 | NULL | 0 |
| alias_key | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "diet_ingredient_terms",
    "from": "profile_id",
    "to": "profile_id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  },
  {
    "id": 0,
    "seq": 1,
    "table": "diet_ingredient_terms",
    "from": "term_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE diet_ingredient_aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL, term_id INTEGER NOT NULL,
        alias TEXT NOT NULL, alias_key TEXT NOT NULL, UNIQUE(profile_id,alias_key),
        FOREIGN KEY(profile_id,term_id) REFERENCES diet_ingredient_terms(profile_id,id) ON DELETE CASCADE);
```

### 索引

- `sqlite_autoindex_diet_ingredient_aliases_1`：SQLite自动生成的主键/唯一约束索引

## diet_food_composition

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| profile_id | INTEGER | 1 | NULL | 1 |
| food_id | INTEGER | 1 | NULL | 2 |
| ingredient_status | TEXT | 1 | NULL | 0 |
| allergen_status | TEXT | 1 | NULL | 0 |
| assessed_food_updated_at | TEXT | 1 | NULL | 0 |
| source_note | TEXT | 1 | '' | 0 |
| updated_at | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "food_items",
    "from": "food_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "NO ACTION",
    "match": "NONE"
  },
  {
    "id": 1,
    "seq": 0,
    "table": "profiles",
    "from": "profile_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE diet_food_composition (
        profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE, food_id INTEGER NOT NULL REFERENCES food_items(id),
        ingredient_status TEXT NOT NULL CHECK(ingredient_status IN ('unknown','partial','declared_complete')),
        allergen_status TEXT NOT NULL CHECK(allergen_status IN ('unknown','partial','declared_complete')),
        assessed_food_updated_at TEXT NOT NULL, source_note TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
        PRIMARY KEY(profile_id,food_id));
```

### 索引

- `sqlite_autoindex_diet_food_composition_1`：SQLite自动生成的主键/唯一约束索引

## diet_food_composition_terms

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| profile_id | INTEGER | 1 | NULL | 1 |
| food_id | INTEGER | 1 | NULL | 2 |
| term_id | INTEGER | 1 | NULL | 3 |
| relation | TEXT | 1 | NULL | 4 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "diet_ingredient_terms",
    "from": "profile_id",
    "to": "profile_id",
    "on_update": "NO ACTION",
    "on_delete": "NO ACTION",
    "match": "NONE"
  },
  {
    "id": 0,
    "seq": 1,
    "table": "diet_ingredient_terms",
    "from": "term_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "NO ACTION",
    "match": "NONE"
  },
  {
    "id": 1,
    "seq": 0,
    "table": "diet_food_composition",
    "from": "profile_id",
    "to": "profile_id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  },
  {
    "id": 1,
    "seq": 1,
    "table": "diet_food_composition",
    "from": "food_id",
    "to": "food_id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE diet_food_composition_terms (
        profile_id INTEGER NOT NULL, food_id INTEGER NOT NULL, term_id INTEGER NOT NULL,
        relation TEXT NOT NULL CHECK(relation IN ('contains','may_contain')),
        PRIMARY KEY(profile_id,food_id,term_id,relation),
        FOREIGN KEY(profile_id,food_id) REFERENCES diet_food_composition(profile_id,food_id) ON DELETE CASCADE,
        FOREIGN KEY(profile_id,term_id) REFERENCES diet_ingredient_terms(profile_id,id));
```

### 索引

- `idx_composition_term`：CREATE INDEX idx_composition_term ON diet_food_composition_terms(profile_id,term_id)
- `sqlite_autoindex_diet_food_composition_terms_1`：SQLite自动生成的主键/唯一约束索引

## diet_food_preferences

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| id | INTEGER | 0 | NULL | 1 |
| profile_id | INTEGER | 1 | NULL | 0 |
| food_id | INTEGER | 0 | NULL | 0 |
| term_id | INTEGER | 0 | NULL | 0 |
| rule_type | TEXT | 1 | NULL | 0 |
| notes | TEXT | 1 | '' | 0 |
| created_at | TEXT | 1 | NULL | 0 |
| updated_at | TEXT | 1 | NULL | 0 |

### 外键

```json
[
  {
    "id": 0,
    "seq": 0,
    "table": "diet_ingredient_terms",
    "from": "profile_id",
    "to": "profile_id",
    "on_update": "NO ACTION",
    "on_delete": "NO ACTION",
    "match": "NONE"
  },
  {
    "id": 0,
    "seq": 1,
    "table": "diet_ingredient_terms",
    "from": "term_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "NO ACTION",
    "match": "NONE"
  },
  {
    "id": 1,
    "seq": 0,
    "table": "food_items",
    "from": "food_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "NO ACTION",
    "match": "NONE"
  },
  {
    "id": 2,
    "seq": 0,
    "table": "profiles",
    "from": "profile_id",
    "to": "id",
    "on_update": "NO ACTION",
    "on_delete": "CASCADE",
    "match": "NONE"
  }
]
```

### DDL 与约束

```sql
CREATE TABLE diet_food_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        food_id INTEGER REFERENCES food_items(id), term_id INTEGER,
        rule_type TEXT NOT NULL CHECK(rule_type IN ('like','dislike','allergy','forbidden')),
        notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        CHECK((food_id IS NULL) != (term_id IS NULL)),
        FOREIGN KEY(profile_id,term_id) REFERENCES diet_ingredient_terms(profile_id,id),
        UNIQUE(profile_id,food_id,rule_type), UNIQUE(profile_id,term_id,rule_type));
```

### 索引

- `sqlite_autoindex_diet_food_preferences_2`：SQLite自动生成的主键/唯一约束索引
- `sqlite_autoindex_diet_food_preferences_1`：SQLite自动生成的主键/唯一约束索引

## diet_schema_migrations

| 字段 | SQLite类型 | NOT NULL标志 | 默认值 | 主键序号 |
| --- | --- | --- | --- | --- |
| version | TEXT | 0 | NULL | 1 |
| checksum | TEXT | 1 | NULL | 0 |
| applied_at | TEXT | 1 | NULL | 0 |

### 外键

```json
[]
```

### DDL 与约束

```sql
CREATE TABLE diet_schema_migrations (
            version TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL
        );
```

### 索引

- `sqlite_autoindex_diet_schema_migrations_1`：SQLite自动生成的主键/唯一约束索引
