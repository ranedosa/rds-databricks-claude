-- DBTITLE 1,TEST TABLE: modify_address (MAIN OUTPUT) - FIXED
-- Fixed version of cell 16 with correct company_id join

CREATE OR REPLACE TABLE crm.sfdc_dbx.unity_modify_address_v2_test AS
SELECT
    ma.sfdc_id,
    ma.fde_id,
    ma.api_flag AS IsPartnerProperty,
    CASE
        WHEN yp.property_id IS NOT NULL AND p.company_id = '15' THEN 'Yardi Systems'
        WHEN yp.property_id IS NOT NULL AND p.company_id = '49' THEN 'Inhabit'
        WHEN ma.api_flag = 1 AND c.name IS NOT NULL THEN c.name
        ELSE NULL
    END AS PropertyCreatedBy,
    ma.match_method
FROM (
    SELECT *
    FROM ModifyAddress
    WHERE fde_id NOT IN (
        SELECT fde_id
        FROM SFDCPropertyFlagRecords
    )
    UNION ALL
    SELECT *
    FROM SFDCPropertyFlagRecords
) ma
INNER JOIN rds.pg_rds_public.properties p
    ON ma.fde_id = p.id
LEFT JOIN rds.pg_rds_public.yardi_properties yp
    ON ma.fde_id = yp.property_id
LEFT JOIN rds.pg_rds_public.companies c
    ON p.company_id = c.id
