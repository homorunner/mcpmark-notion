Conduct a comprehensive security audit to identify PostgreSQL users with insufficient or dangling permissions in a business database environment.

## Your Mission:

You've been hired as a security consultant to audit the PostgreSQL database permissions for a growing e-commerce company. The company has experienced rapid growth and multiple teams have been granted database access over time. However, there's concern about permission inconsistencies and security gaps.

## Security Audit Requirements:

1. **Discover the database structure**: Identify all business tables and their purposes
2. **Catalog all database users and roles**: Use `pg_user`, `pg_roles`, and `pg_auth_members` to find all accounts
3. **Analyze current permissions**: Use `information_schema.table_privileges` to map permissions
4. **Identify security issues**:
   - **Dangling users**: Inactive accounts that should be removed
   - **Missing permissions**: Users lacking permissions required for their business role
   - **Excessive permissions**: Users with unnecessary permissions that should be revoked

## Expected Deliverables:

Your audit must produce findings in a structured format that can be verified. Create two tables to store your audit results:

**1. Summary Table:**
```sql
CREATE TABLE security_audit_results (
    audit_id SERIAL PRIMARY KEY,
    audit_type VARCHAR(50) NOT NULL, -- 'DANGLING_USERS', 'MISSING_PERMISSIONS', 'EXCESSIVE_PERMISSIONS'
    total_issues INTEGER NOT NULL,
    users_affected INTEGER NOT NULL,
    tables_affected INTEGER NOT NULL
);
```

**2. Detailed Findings Table:**
```sql
CREATE TABLE security_audit_details (
    detail_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    issue_type VARCHAR(50) NOT NULL, -- 'DANGLING_USER', 'MISSING_PERMISSION', 'EXCESSIVE_PERMISSION'
    table_name VARCHAR(50), -- NULL for dangling users
    permission_type VARCHAR(20), -- 'SELECT', 'INSERT', 'UPDATE', 'DELETE', NULL for dangling users
    expected_access BOOLEAN NOT NULL -- TRUE if user should have access, FALSE if should not
);
```

## Success Criteria:

Your audit should populate both tables with:
- **Summary data**: High-level counts of different types of security issues
- **Detailed findings**: Specific permission gaps for each user and table combination

Analyze usernames and infer their intended business roles, then determine what permissions they should have based on the available tables and typical business needs.

The verification process will check that your findings correctly identify the actual permission gaps in the system by comparing against expected results.