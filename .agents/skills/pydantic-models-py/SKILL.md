---
name: pydantic-models-py
description: Create Pydantic models following the multi-model pattern with Base, Create, Update, Response, and InDB variants. Use when defining API request/response schemas, database models, or data validation in Python applications using Pydantic v2.
license: MIT
metadata:
  author: Microsoft
  version: "1.0.0"
  source: https://github.com/microsoft/skills
  adapted_for: TradingAgentsA (MongoDB via motor, app/schemas/)
---

# Pydantic Models

> 来源：[microsoft/skills](https://github.com/microsoft/skills) 的 `pydantic-models-py`，已按本项目结构（`app/schemas/`、MongoDB）适配。

Create Pydantic models following the multi-model pattern for clean API contracts.

## Quick Start

Copy the template from [assets/template.py](assets/template.py) and replace placeholders:
- `{{ResourceName}}` → PascalCase name (e.g., `Project`)
- `{{resource_name}}` → snake_case name (e.g., `project`)

## Multi-Model Pattern

| Model | Purpose |
|-------|---------|
| `Base` | Common fields shared across models |
| `Create` | Request body for creation (required fields) |
| `Update` | Request body for updates (all optional) |
| `Response` | API response with all fields |
| `InDB` | Database document with `doc_type` |

## camelCase Aliases

```python
class MyModel(BaseModel):
    workspace_id: str = Field(..., alias="workspaceId")
    created_at: datetime = Field(..., alias="createdAt")
    
    class Config:
        populate_by_name = True  # Accept both snake_case and camelCase
```

## Optional Update Fields

```python
class MyUpdate(BaseModel):
    """All fields optional for PATCH requests."""
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
```

## Database Document

```python
class MyInDB(MyResponse):
    """MongoDB 文档模型。

    本项目用 MongoDB（motor 异步驱动），InDB 扩展 Response 加上数据库特有字段。
    可按需加 _id（ObjectId）、doc_type（类型标记，用于同一 collection 存多类型）等。
    """
    # MongoDB 的 _id 由数据库生成，序列化时转字符串
    id: str = Field(..., alias="_id", description="MongoDB ObjectId")
```

> 注：本项目 MongoDB 无需 Cosmos DB 那样的强制 `doc_type` 分区字段；
> 但若一个 collection 存多种文档类型，仍可用 `doc_type` 做类型标记。

## Integration Steps

1. Create schemas in `app/schemas/`
2. Export from `app/schemas/__init__.py`（参考现有 schema 组织方式）
3. Add corresponding TypeScript types in `frontend/src/types/`
