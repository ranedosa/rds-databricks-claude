-- Query 1: Find Park Kennedy in RDS Properties
SELECT
    id as property_id,
    name,
    short_id,
    status,
    sfdc_id,
    identity_verification_enabled,
    inserted_at,
    updated_at
FROM properties
WHERE name LIKE '%Park Kennedy%'
ORDER BY id;
