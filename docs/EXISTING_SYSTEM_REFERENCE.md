# Existing System Reference

This document contains PLC and database configuration extracted from the existing PeakHMI system.

> **Source:** `C:\Projects\PeakhMI\PeakHMI\portConfiguration.ntp` and `ScriptGlobals.ini`

## PLC Configuration

| Setting | Value |
|---------|-------|
| IP Address | 192.168.50.10 |
| Protocol | Ethernet/IP (Allen-Bradley Logix) |
| Slot | 0 (default) |

## Recipe UDT Structure

The recipe data is stored at `RECIPE[0]` (runtime/active recipe). Recipes 1-99 are stored recipes.

### Product Information
| PLC Tag | Description |
|---------|-------------|
| `RECIPE[0].RECIPE_NUMBER` | Recipe number (INT) |
| `RECIPE[0].PRODUCT_NAME1` | Product name / Customer |
| `RECIPE[0].PRODUCT_NAME2` | Customer note / Feed rate |

### Bulk Ingredients (9 slots)
| Name Tag | Weight Tag | Example Value |
|----------|------------|---------------|
| `RECIPE[0].B1_NAME` | `RECIPE[0].B1_WT` | BARLEY |
| `RECIPE[0].B2_NAME` | `RECIPE[0].B2_WT` | MAIZE |
| `RECIPE[0].B3_NAME` | `RECIPE[0].B3_WT` | BARLEY/MAIZE |
| `RECIPE[0].B4_NAME` | `RECIPE[0].B4_WT` | LIME |
| `RECIPE[0].B5_NAME` | `RECIPE[0].B5_WT` | BROLL |
| `RECIPE[0].B6_NAME` | `RECIPE[0].B6_WT` | SOYA |
| `RECIPE[0].B7_NAME` | `RECIPE[0].B7_WT` | COPRA |
| `RECIPE[0].B8_NAME` | `RECIPE[0].B8_WT` | HULLS |
| `RECIPE[0].B9_NAME` | `RECIPE[0].B9_WT` | DDGS |

### Minor Ingredients (18 slots)
| Name Tag | Weight Tag |
|----------|------------|
| `RECIPE[0].INGRE_NAME_1` | `RECIPE[0].INGRE_1_WT` |
| `RECIPE[0].INGRE_NAME_2` | `RECIPE[0].INGRE_2_WT` |
| ... | ... |
| `RECIPE[0].INGRE_NAME_18` | `RECIPE[0].INGRE_18_WT` |

### Special Ingredients
| Tag | Description |
|-----|-------------|
| `RECIPE[0].MOLASSES_WT` | Molasses weight |
| `RECIPE[0].RECYCLE_WT` | Recycled ingredient weight |
| `RECIPE[0].TOTAL_WT` | Total batch weight |
| `RECIPE_REAL[0,0]` | Batch ratio |

## SQL Server Configuration

| Setting | Value |
|---------|-------|
| Server | `SVR\SQLEXPRESS` |
| Database | `EXO_Live` |
| Driver | ODBC Driver 17/18 for SQL Server |
| Username | `SA` |
| Password | *(see config.yaml - do not store in docs)* |
| Login Timeout | 10 seconds |

### Target Tables

**Primary:** `dbo.X_RecipeLog` - Main recipe batch logging

**Secondary:** `dbo.X_Recipe_Check_Sheet` - Sequential check sheets

### Column Mappings (PLC → SQL)

| SQL Column | Source | Notes |
|------------|--------|-------|
| `SEQ_Number` | PLC point "Recipe Sequence Number" | Batch ID |
| `Manufacture_Date` | System timestamp | ISO 8601 format |
| `Recipe_Number` | PLC point "Receipe Number" | |
| `Product_Name` | `RECIPE[0].PRODUCT_NAME1` | |
| `Customer_Note` | `RECIPE[0].PRODUCT_NAME2` | |
| `B001_Name` | Bulk slot 1 name | |
| `B002_Name` | Bulk slot 2 name | |
| ... | ... | |
| `B009_Name` | Bulk slot 9 name | |
| `B001_Weight` | PLC point "Weight B001" | |
| ... | ... | |
| `B009_Weight` | PLC point "Weight B009" | |
| `ING001_Name` | `RECIPE[0].INGRE_NAME_1` | |
| ... | ... | |
| `ING018_Name` | `RECIPE[0].INGRE_NAME_18` | |
| `ING001_Weight` | PLC point "Weight I001" | |
| ... | ... | |
| `ING018_Weight` | PLC point "Weight I018" | |
| `MOLASSES_Weight` | PLC point "Weight IMOLASSES" | |
| `RECYCLE_Weight` | PLC point "Ingredient Recycle Weight" | |
| `TOTAL_Weight` | PLC point "Weight Total" | |
| `BATCH_RATIO` | PLC point "Batch_Ratio" | |

## Trigger Mechanism

The existing PeakHMI system uses `Batch_Enable` digital trigger:
- Scripts monitor for rising edge on trigger
- When triggered, data is read and logged via ODBC
- Trigger is reset to 0 after successful log

**PeakHMI Point Names** (need actual PLC addresses from .pdb or PLC program):
| Point Name | Purpose |
|------------|---------|
| `Batch_Enable` | Main trigger for X_RecipeLog |
| `Batch_Enable_SEQ` | Trigger for X_Recipe_Check_Sheet |
| `Recipe Sequence Number` | Batch ID / sequence counter |

## Weight Tags (Actual vs Recipe)

**Important:** The logged weights come from separate PLC tags (actual measured weights), NOT from RECIPE[0] (which contains setpoints).

**PeakHMI Weight Points** (need actual PLC addresses):
| Point Name | SQL Column |
|------------|------------|
| `Weight B001` - `Weight B009` | `B001_Weight` - `B009_Weight` |
| `Weight I001` - `Weight I018` | `ING001_Weight` - `ING018_Weight` |
| `Weight IMOLASSES` | `MOLASSES_Weight` |
| `Ingredient Recycle Weight` | `RECYCLE_Weight` |
| `Weight Total` | `TOTAL_Weight` |
| `Batch_Ratio` | `BATCH_RATIO` |

## Actual PLC Tag Addresses

**Source:** `E:\temp\Stockfood_Master_Controller_Tags.CSV`

### Key Control Tags
| Description | PLC Tag | Data Type |
|-------------|---------|-----------|
| Batch Enable (trigger) | `RECIPE_BITS[0,2].10` | BOOL |
| Recipe Sequence Number | `A_DINT[10]` | DINT |
| Recipe Sequence Number (INT) | `A_INT[0]` | INT |
| PeakHMI Log Trigger | `A_BIT[261]` | BOOL |
| Batch Ratio | `RECIPE_REAL[0,0]` | REAL |
| Weigh Bin Weight (actual) | `RECIPE_DINT[0,91]` | DINT |
| Recycle Weight | `RECIPE_DINT[0,29]` | DINT |

### Recipe UDT Structure (`RECIPE[0]`)

**Verified from Logix Designer (2026-01-29):**

| Field | Data Type | Description |
|-------|-----------|-------------|
| `RECIPE[0].RECIPE_NUMBER` | DINT | Recipe number |
| `RECIPE[0].PRODUCT_NAME1` | STRING | Product name |
| `RECIPE[0].PRODUCT_NAME2` | STRING | Customer note |
| `RECIPE[0].B1_NAME` - `B9_NAME` | STRING | Bulk ingredient names |
| `RECIPE[0].B1_WT` - `B9_WT` | DINT | Bulk ingredient weights |
| `RECIPE[0].INGRE_NAME_1` - `INGRE_NAME_18` | STRING | Minor ingredient names |
| `RECIPE[0].INGRE_1_WT` - `INGRE_18_WT` | REAL | Minor ingredient weights |
| `RECIPE[0].MOLASSES_WT` | DINT | Molasses weight |
| `RECIPE[0].RECYCLE_WT` | DINT | Recycle weight |
| `RECIPE[0].TOTAL_WT` | DINT | Total batch weight |

### Calculated/Actual Weight Tags
| Description | PLC Tag |
|-------------|---------|
| Averaged Weigh Bin Weight | `RECIPE_DINT[0,90]` |
| Weigh Bin Weight | `RECIPE_DINT[0,91]` |
| B1-B9 Setpoint Adjustments | `RECIPE_DINT[0,17]` - `RECIPE_DINT[0,28]` |
| Small Ingredients Total | `RECIPE_DINT[0,4]` |
| Bulk Ingredients Total | `RECIPE_DINT[0,5]` |

## SQLlog Handshake Tags (Added to PLC)

These tags were added for the SQLlog handshake:

| Tag | Data Type | Description |
|-----|-----------|-------------|
| `SQLlog_Trigger` | INT | 0=Idle, 1=Log Request, 2=Acknowledged, 99=Fault |
| `SQLlog_Heartbeat` | INT | Python increments every 2s |
| `SQLlog_Error_Code` | INT | Error code on fault |

See PROJECT_SCOPE.md for the 4-state handshake protocol.

## Named Bulk Ingredient Slots

From `ScriptGlobals.ini`, the default slot names:

| Slot | Name |
|------|------|
| 1 | BARLEY |
| 2 | MAIZE |
| 3 | BARLEY / MAIZE |
| 4 | LIME |
| 5 | BROLL |
| 6 | SOYA MEAL |
| 7 | COPRA MEAL |
| 8 | SOYA HULLS |
| 9 | DDGS |
| 10 | MOLASSES |
