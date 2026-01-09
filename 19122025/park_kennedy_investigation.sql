-- Investigation: Park Kennedy Feature Sync Issue
-- SFDC ID: a01Dn00000HHUanIAH

-- Step 1: Check Park Kennedy in Salesforce
SELECT
    id,
    name,
    snappt_property_id_c,
    reverse_etl_id_c,
    fraud_detection_enabled_c,
    income_verification_enabled_c,
    id_verification_enabled_c,
    bank_linking_enabled_c,
    connected_payroll_enabled_c,
    verification_of_rent_enabled_c,
    idv_only_enabled_c,
    is_deleted,
    created_date,
    last_modified_date
FROM crm.salesforce.product_property
WHERE name LIKE '%Park Kennedy%'
ORDER BY created_date DESC;

-- Step 2: Check Park Kennedy features in RDS
SELECT
    p.id as property_id,
    p.name,
    p.short_id,
    p.status,
    pf.feature_type,
    pf.enabled,
    pf.enabled_at,
    pf.updated_at
FROM rds.pg_rds_public.properties p
LEFT JOIN rds.pg_rds_public.property_features pf ON p.id = pf.property_id
WHERE p.name LIKE '%Park Kennedy%'
ORDER BY p.id, pf.feature_type;

-- Step 3: Check Park Kennedy in the feature aggregation table
SELECT
    property_id,
    property_name,
    fraud_enabled,
    fraud_enabled_at,
    iv_enabled,
    iv_enabled_at,
    idv_enabled,
    idv_enabled_at,
    bank_linking_enabled,
    bank_linking_enabled_at,
    payroll_linking_enabled,
    payroll_linking_enabled_at,
    vor_enabled,
    vor_enabled_at,
    idv_only_enabled,
    idv_only_enabled_at
FROM crm.sfdc_dbx.product_property_w_features
WHERE property_name LIKE '%Park Kennedy%';

-- Step 4: Check if Park Kennedy is in the sync table (records that need updating)
SELECT
    snappt_property_id_c,
    reverse_etl_id_c,
    name,
    fraud_detection_enabled_c,
    income_verification_enabled_c,
    id_verification_enabled_c,
    bank_linking_enabled_c,
    connected_payroll_enabled_c,
    verification_of_rent_enabled_c
FROM crm.sfdc_dbx.product_property_feature_sync
WHERE name LIKE '%Park Kennedy%';

-- Step 5: Check for duplicate property IDs
SELECT
    snappt_property_id_c,
    COUNT(*) as record_count,
    GROUP_CONCAT(id) as salesforce_ids
FROM crm.salesforce.product_property
WHERE name LIKE '%Park Kennedy%'
GROUP BY snappt_property_id_c;
