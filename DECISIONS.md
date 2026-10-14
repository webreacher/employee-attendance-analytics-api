# Architectural & Design Decisions

### 1. Dual Collection Strategy with an Audit Trail
- **Design:** Instead of overwriting punch-in/out records without a history, any manual correction creates an entry in an immutable `audit_logs` collection before modifying `attendance`.
- **Rationale:** Compliance and payroll auditing require full visibility into when an adjustment was made, who authorized it (`modified_by`), and why (`reason`).

### 2. Time-Window Aggregations via `$setWindowFields`
- **Design:** Used MongoDB's native `$setWindowFields` with a 7-entry document window (`[-6, 0]`) rather than performing running calculations in Python memory.
- **Rationale:** Moving averages and trend analyses run much faster on the MongoDB database engine directly, keeping network transport minimal.

### 3. Precision Rounding (`ROUND_HALF_UP`)
- **Design:** Used Python's `decimal` library with `ROUND_HALF_UP` for floating-point attendance rates rather than standard floating-point approximations.
- **Rationale:** Standard IEEE 754 float types introduce rounding inaccuracies (e.g., `0.1 + 0.2 != 0.3`) which can skew payroll and time analytics reports.

### 4. Input Validation & Range Bounds
- **Design:** Strict date parsing and a maximum querying range limit of 92 days on trends.
- **Rationale:** Protects the database against unbounded historical aggregations that could degrade memory performance.