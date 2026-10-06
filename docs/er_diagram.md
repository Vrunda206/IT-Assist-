# ER Diagram – IT Assist

Paste the block below into https://mermaid.live (or any Markdown viewer with Mermaid support).

```mermaid
erDiagram
    DEPARTMENTS ||--o{ EMPLOYEES : "has"
    EMPLOYEES ||--o{ ASSET_ASSIGNMENTS : "receives"
    ASSETS ||--o{ ASSET_ASSIGNMENTS : "assigned in"
    ASSET_CATEGORIES ||--o{ ASSETS : "classifies"
    VENDORS |o--o{ ASSETS : "supplies"
    ASSETS ||--o{ MAINTENANCE : "serviced in"
    ASSETS ||--o{ ASSET_USAGE : "measured in"

    DEPARTMENTS {
        int department_id PK
        varchar department_name UK
        varchar location
    }
    EMPLOYEES {
        int employee_id PK
        varchar employee_name
        varchar email UK
        varchar phone
        int department_id FK
        varchar designation
        date joining_date
        varchar status
    }
    ASSET_CATEGORIES {
        int category_id PK
        varchar category_name UK
        varchar description
    }
    VENDORS {
        int vendor_id PK
        varchar vendor_name
        varchar contact_person
        varchar phone
        varchar email
    }
    ASSETS {
        int asset_id PK
        varchar asset_tag UK
        varchar asset_name
        int category_id FK
        int vendor_id FK
        varchar brand
        varchar model
        varchar serial_number UK
        date purchase_date
        decimal purchase_cost
        date warranty_expiry
        varchar status
        varchar location
        timestamp created_at
    }
    ASSET_ASSIGNMENTS {
        int assignment_id PK
        int asset_id FK
        int employee_id FK
        date assigned_date
        date returned_date
        varchar assignment_status
        varchar remarks
    }
    MAINTENANCE {
        int maintenance_id PK
        int asset_id FK
        varchar issue
        date maintenance_date
        decimal cost
        varchar status
        varchar remarks
    }
    ASSET_USAGE {
        int usage_id PK
        int asset_id FK
        date usage_date
        decimal usage_hours
        int performance_score
        decimal downtime_hours
    }
```

## Relationships (all one-to-many)
| Parent (1) | Child (many) | Foreign key | On delete |
|---|---|---|---|
| departments | employees | employees.department_id | RESTRICT |
| asset_categories | assets | assets.category_id | RESTRICT |
| vendors | assets | assets.vendor_id (optional) | SET NULL |
| employees | asset_assignments | asset_assignments.employee_id | RESTRICT |
| assets | asset_assignments | asset_assignments.asset_id | CASCADE |
| assets | maintenance | maintenance.asset_id | CASCADE |
| assets | asset_usage | asset_usage.asset_id | CASCADE |

`employees` ↔ `assets` is many-to-many over time, resolved by the junction table `asset_assignments`.
