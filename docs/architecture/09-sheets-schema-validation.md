# Sheets schema validation

## Purpose
Schema validation enforces a clear data contract for Sheets inputs and prevents silent data loss. Every row is either accepted as valid or preserved as invalid with explicit reasons, so operators can correct the data without guessing what was dropped.

## Inputs and outputs

### Input rows
Rows are dictionaries read from Sheets (column name -> cell value).

### ValidationResult
The validator returns a `ValidationResult` with:
- `valid_rows`: rows that passed validation, with coercions applied
- `invalid_rows`: rows that failed, with `row_idx`, original `row`, and `reasons`
- counts: `rows_in`, `rows_valid`, `rows_invalid`

### Marked rows
Rows can be annotated instead of dropped. Two fields are added:
- `_gw_valid`: boolean
- `_gw_reasons`: pipe-separated reason codes for invalid rows

## Schema format
The schema is defined in `rules.schema` and is the single source of truth. Each column has a spec with `type`, `required`, and `allow_blank`.

Supported `type` values in T2:
- `string`
- `number`
- `bool`
- `date_iso`

Example snippet:
```yaml
rules:
  schema:
    id:
      type: string
      required: true
      allow_blank: false
    amount:
      type: number
      required: true
      allow_blank: false
```

## Reason codes
The validator emits exact reason strings:
- `missing_required:<col>`
- `blank_not_allowed:<col>`
- `type_error:<col>:<type>`

## Golden behavior rules
- Never drop rows silently.
- Invalid rows are preserved and annotated with reasons.
- Coercion is allowed (e.g., "3.50" -> 3.5), but dates must match strict ISO `YYYY-MM-DD`.

## Operator-facing outputs
Operators see validation outcomes in both Sheets and run artifacts:
- Report tab: a metric/value KPI block including a UTC timestamp.
- Needs review tab: invalid rows with `reason` and `values_json`.
- Run artifacts: `runs/<run_id>/artifacts/report.csv` and `runs/<run_id>/artifacts/needs_review.csv`.

## Example
Schema:
```yaml
rules:
  schema:
    id:
      type: string
      required: true
      allow_blank: false
    date:
      type: date_iso
      required: true
      allow_blank: false
    amount:
      type: number
      required: true
      allow_blank: false
```

Input rows:
```json
{
  "id": "A-1",
  "date": "2026-02-01",
  "amount": "3.50"
}
{
  "id": "",
  "date": "02/01/2026",
  "amount": "abc"
}
```

Expected reasons for the invalid row:
- `missing_required:id`
- `type_error:date:date_iso`
- `type_error:amount:number`
